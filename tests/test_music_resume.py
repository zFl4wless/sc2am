"""Exercise the durable workflow at its subprocess boundary; no real Music access."""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner
from mutagen.id3 import COMM, ID3

import main
import sc2am.apple_music as music
from sc2am.apple_music import AppleMusicManager as Manager
from sc2am.downloader import Downloader
from sc2am.history import History

LIBRARY = "AAAAAAAAAAAAAAAA"
TRACK = "BBBBBBBBBBBBBBBB"
PLAYLIST = "CCCCCCCCCCCCCCCC"


class MusicDouble:
    """Model copied library files, stable IDs, memberships and lost replies."""

    def __init__(self):
        self.library = LIBRARY
        self.playlist = PLAYLIST
        self.playlist_name = "Roadtrip"
        self.listings = 0
        self.target_error = ""
        self.track = ""
        self.marker = ""
        self.marker_matches = []
        self.member = False
        self.mutations = []
        self.calls = []
        self.failure = {}

    def run(self, command, **kwargs):
        assert kwargs == {"capture_output": True, "text": True, "timeout": 30}
        assert command[:2] == ["osascript", "-e"]
        if len(command) == 3:
            self.listings += 1
            return subprocess.CompletedProcess(command, 0, json.dumps([self.playlist_name]), "")
        path, playlist, marker, known, library, action, playlist_id = command[3:]
        self.calls.append(command[3:])
        if library and library != self.library:
            return subprocess.CompletedProcess(command, 1, "", "SC2AM_NOT_STARTED: Library changed")
        if playlist and (
            self.target_error
            or (playlist_id and playlist_id != self.playlist)
            or (not playlist_id and playlist != self.playlist_name)
        ):
            return subprocess.CompletedProcess(
                command,
                1,
                "",
                "SC2AM_NOT_STARTED: " + (self.target_error or "Target playlist is stale; rerun"),
            )
        if action == "resolve":
            assert marker == known == "", "discovery must not search for tracks"
            return subprocess.CompletedProcess(
                command, 0, f"{self.library}||{self.playlist if playlist else ''}|0", ""
            )
        # Persistent IDs take precedence; only a missing ID falls back to markers.
        if not (known and known == self.track) and len(self.marker_matches) > 1:
            return subprocess.CompletedProcess(
                command,
                1,
                "",
                "SC2AM_NOT_STARTED: Multiple library tracks match this source. "
                "Resolve duplicates in Music before retrying.",
            )
        if action != "lookup":
            self.mutations.append(action)
            with History(Path(path).parent) as history:
                rows = history.connection.execute(
                    "SELECT key FROM records WHERE key LIKE '%:pending:%'"
                ).fetchall()
                assert rows, "intent must be durable before dispatch"
            mode = self.failure.get(action)
            if mode == "before":
                return subprocess.CompletedProcess(
                    command, 1, "", "SC2AM_NOT_STARTED: Target changed"
                )
            if mode not in ("no_effect", "timeout_before", "invalid_reply", "phantom_reply"):
                if action == "import":
                    self.track, self.marker = TRACK, marker
                    assert marker in ID3(path)["COMM::eng"].text[0]
                else:
                    assert known == self.track  # Playlist stage must use a library reference.
                    self.member = True
            if mode in ("timeout_after", "timeout_before"):
                raise subprocess.TimeoutExpired(command, 30)
            if mode == "error_after":
                return subprocess.CompletedProcess(command, 1, "", "AppleEvent timed out")
            if mode == "invalid_reply":
                return subprocess.CompletedProcess(command, 0, "", "")
            if mode == "phantom_reply":
                return subprocess.CompletedProcess(command, 0, f"{LIBRARY}|{TRACK}||0", "")
            if mode == "interrupt_after":
                raise KeyboardInterrupt()
        # A copied file is only discoverable by its marker or saved reference.
        if known and known == self.track:
            track = self.track
        elif self.marker_matches:
            track = self.marker_matches[0]
        else:
            track = self.track if marker == self.marker else ""
        output = "|".join(
            [
                self.library,
                track,
                self.playlist if playlist else "",
                "1" if track and playlist and self.member else "0",
            ]
        )
        return subprocess.CompletedProcess(command, 0, output, "")


@pytest.fixture
def music_double(monkeypatch):
    double = MusicDouble()
    monkeypatch.setattr(music.subprocess, "run", double.run)
    monkeypatch.setattr(music.time, "sleep", lambda _: None)
    return double


@pytest.fixture
def track(tmp_path):
    path = tmp_path / 'track "été".mp3'
    path.write_bytes(b"local test payload")
    return path


def pending_records(path):
    with History(path.parent) as history:
        return history.connection.execute(
            "SELECT key FROM records WHERE key LIKE '%:pending:%'"
        ).fetchall()


def test_open_then_playlist_and_repeated_processes_reuse_one_reference(track, music_double):
    assert Manager.open_file_with_music(track) == (True, "Import confirmed in Apple Music")
    assert Manager.add_to_playlist(track, "Roadtrip") == (True, "Added to playlist 'Roadtrip'")
    # New manager / database connections must reuse durable evidence.
    assert Manager().open_file_with_music(track)[0]
    assert Manager().add_to_playlist(track, "Roadtrip")[0]
    assert music_double.mutations == ["import", "playlist"]
    assert not pending_records(track)


@pytest.mark.parametrize("stage", ["import", "playlist"])
@pytest.mark.parametrize("failure", ["timeout_after", "error_after"])
def test_completed_mutation_is_reconciled_without_replay(track, music_double, stage, failure):
    music_double.failure[stage] = failure
    assert Manager.add_to_playlist(track, "Roadtrip")[0]
    assert Manager.add_to_playlist(track, "Roadtrip")[0]
    assert music_double.mutations == ["import", "playlist"]
    assert not pending_records(track)


@pytest.mark.parametrize(
    "failure", ["no_effect", "timeout_before", "invalid_reply", "phantom_reply"]
)
def test_unconfirmed_import_cannot_claim_success_or_replay(track, music_double, failure):
    music_double.failure["import"] = failure
    success, message = Manager.open_file_with_music(track)
    assert not success
    assert "not confirmed" in message
    assert pending_records(track)
    # A fresh invocation reads first but cannot blindly send the event again.
    success, message = Manager.open_file_with_music(track)
    assert not success
    assert "previous Music mutation is still unconfirmed" in message
    assert music_double.mutations == ["import"]
    # Simulate a late completion; the next invocation reconciles it.
    music_double.track = TRACK
    music_double.marker = ID3(track)["COMM::eng"].text[0]
    assert Manager.open_file_with_music(track)[0]
    assert music_double.mutations == ["import"]
    assert not pending_records(track)


def test_partial_playlist_failure_retries_only_failed_stage(track, music_double):
    music_double.failure["playlist"] = "before"
    assert not Manager.add_to_playlist(track, "Roadtrip")[0]
    assert music_double.track == TRACK
    assert not music_double.member
    assert not pending_records(track)  # Script explicitly proved no mutation started.
    music_double.failure.clear()
    assert Manager.add_to_playlist(track, "Roadtrip")[0]
    assert music_double.mutations == ["import", "playlist", "playlist"]


def test_uncertain_playlist_is_not_repeated_but_can_reconcile(track, music_double):
    music_double.failure["playlist"] = "timeout_before"
    assert not Manager.add_to_playlist(track, "Roadtrip")[0]
    assert not Manager.add_to_playlist(track, "Roadtrip")[0]
    assert music_double.mutations == ["import", "playlist"]
    music_double.member = True
    assert Manager.add_to_playlist(track, "Roadtrip")[0]
    assert not pending_records(track)


def test_interrupted_process_leaves_intent_and_next_run_reconciles(track, music_double):
    music_double.failure["import"] = "interrupt_after"
    with pytest.raises(KeyboardInterrupt):
        Manager.open_file_with_music(track)
    assert pending_records(track)
    assert Manager.open_file_with_music(track)[0]
    assert music_double.mutations == ["import"]
    assert not pending_records(track)


def test_library_switch_does_not_reuse_other_library_reference(track, music_double):
    assert Manager.open_file_with_music(track)[0]
    music_double.calls.clear()
    music_double.library = "DDDDDDDDDDDDDDDD"
    music_double.track, music_double.marker = "", ""
    assert Manager.open_file_with_music(track)[0]
    assert music_double.mutations == ["import", "import"]
    first_lookup = next(call for call in music_double.calls if call[5] == "lookup")
    assert first_lookup[3:5] == ["", music_double.library]
    with History(track.parent) as history:
        keys = [
            row[0]
            for row in history.connection.execute(
                "SELECT key FROM records WHERE key LIKE 'music:%'"
            )
        ]
    assert any(LIBRARY in key for key in keys)
    assert any(music_double.library in key for key in keys)


def test_saved_reference_survives_edited_music_comment(track, music_double):
    assert Manager.open_file_with_music(track)[0]
    music_double.marker = "user edited comment"
    assert Manager.open_file_with_music(track)[0]
    assert music_double.mutations == ["import"]


def test_removed_membership_is_restored_without_import(track, music_double):
    assert Manager.add_to_playlist(track, "Roadtrip")[0]
    music_double.member = False
    assert Manager.add_to_playlist(track, "Roadtrip")[0]
    assert music_double.mutations == ["import", "playlist", "playlist"]


def test_deleted_library_track_is_reimported_after_live_lookup(track, music_double):
    assert Manager.open_file_with_music(track)[0]
    music_double.track, music_double.marker = "", ""
    assert Manager.open_file_with_music(track)[0]
    assert music_double.mutations == ["import", "import"]


def test_concurrent_music_work_is_rejected_before_dispatch(track, music_double):
    with History(track.parent) as history, history.music_lock():
        success, message = Manager.open_file_with_music(track)
    assert not success
    assert "Another Music import is running" in message
    assert not music_double.calls


def test_corrupt_history_stops_before_music(track, music_double):
    root = track.parent / ".sc2am"
    root.mkdir()
    (root / "history.sqlite3").write_bytes(b"corrupt database")
    assert not Manager.open_file_with_music(track)[0]
    assert not music_double.calls


def test_marker_preserves_comments_and_is_not_appended_twice(track):
    tags = ID3()
    tags.add(COMM(encoding=3, lang="eng", desc="", text=["My notes"]))
    tags.add(COMM(encoding=3, lang="deu", desc="Other", text=["Notizen"]))
    tags.save(track)
    marker = "sc2am:" + "a" * 64
    Manager._mark_file(track, marker)
    Manager._mark_file(track, marker)
    tags = ID3(track)
    assert tags["COMM::eng"].text == ["My notes\n" + marker]
    assert tags["COMM:Other:deu"].text == ["Notizen"]


@pytest.mark.parametrize("default_comment", [False, True])
@pytest.mark.parametrize("prefix", ["sc2am:", "SC2AM:", "Sc2aM:"])
@pytest.mark.parametrize("digest", ["abcdef01" * 8, "ABCDEF01" * 8, "aBcDeF01" * 8])
def test_marker_removes_foreign_and_embedded_markers_from_all_comments(
    track, default_comment, prefix, digest
):
    own = "sc2am:" + "a" * 64
    foreign = prefix + digest
    other = prefix.swapcase() + digest.swapcase()
    ordinary = "  Notizen\nsc2am:test\nſc2am:" + "a" * 64 + "\nSC2AM:" + "Ａ" * 64 + "  "
    tags = ID3()
    if default_comment:
        tags.add(COMM(encoding=3, lang="eng", desc="", text=[f"Notes ({foreign}) {own}"]))
    tags.add(COMM(encoding=3, lang="deu", desc="", text=[f"Vor{foreign}nach"]))
    tags.add(
        COMM(encoding=3, lang="eng", desc="Other", text=[f"First {other}\nLast {own.upper()}"])
    )
    tags.add(COMM(encoding=3, lang="fra", desc="Only marker", text=[foreign]))
    tags.add(COMM(encoding=3, lang="deu", desc="Notes", text=[ordinary]))
    tags.save(track, v2_version=3)

    Manager._mark_file(track, own)
    marked_bytes = track.read_bytes()
    Manager._mark_file(track, own)
    assert track.read_bytes() == marked_bytes
    comments = ID3(track)
    assert comments["COMM::eng"].text == ["Notes () \n" + own if default_comment else own]
    assert comments["COMM::deu"].text == ["Vornach"]
    assert comments["COMM:Other:eng"].text == ["First \nLast "]
    assert "COMM:Only marker:fra" not in comments  # Mutagen omits empty comments on save.
    assert comments["COMM:Notes:deu"].text == [ordinary]
    all_text = "\n".join(text for frame in comments.getall("COMM") for text in frame.text)
    assert all_text.count(own) == 1
    assert own.upper() not in all_text
    assert foreign not in all_text and other not in all_text


def test_new_import_cleans_comments_and_refreshes_verified_history(track, music_double):
    foreign = "sc2am:" + "b" * 64
    tags = ID3()
    tags.add(COMM(encoding=3, lang="eng", desc="", text=[f"Notes ({foreign})"]))
    tags.add(COMM(encoding=3, lang="deu", desc="Other", text=[f"Notizen {foreign}"]))
    tags.save(track)
    with History(track.parent) as history:
        history.remember_download("https://soundcloud.com/fixture/track", "soundcloud:123", track)
    assert Manager.open_file_with_music(track)[0]
    comments = ID3(track)
    assert comments["COMM::eng"].text == ["Notes ()\n" + music_double.marker]
    assert comments["COMM:Other:deu"].text == ["Notizen "]
    with History(track.parent) as history:
        assert history.cached_file("soundcloud:123") == track.resolve()
    assert Manager.open_file_with_music(track)[0]
    assert music_double.mutations == ["import"]


@pytest.mark.parametrize("playlist", ["", "Roadtrip"])
@pytest.mark.parametrize("collision", ["different", "ambiguous"])
def test_saved_id_precedes_conflicting_markers(track, music_double, playlist, collision):
    assert Manager._import(track, playlist).success
    if collision == "ambiguous":
        music_double.marker_matches = [TRACK, "DDDDDDDDDDDDDDDD"]
    else:
        music_double.marker = "user edited comment"
        music_double.marker_matches = ["DDDDDDDDDDDDDDDD"]
    music_double.calls.clear()
    mutations = music_double.mutations[:]
    assert Manager._import(track, playlist).success
    discovery, lookup = music_double.calls
    assert discovery[2:4] == ["", ""] and discovery[5] == "resolve"
    assert lookup[3:6] == [TRACK, LIBRARY, "lookup"]
    assert lookup[6] == (PLAYLIST if playlist else "")
    assert music_double.mutations == mutations


@pytest.mark.parametrize("known", ["", "DDDDDDDDDDDDDDDD"])
def test_ambiguous_markers_without_live_saved_id_stop_before_mutation(track, music_double, known):
    with History(track.parent) as history:
        source = history.file_source(track)
        if known:
            history.put(f"music:{LIBRARY}:{source}", known)
    music_double.marker_matches = [TRACK, "EEEEEEEEEEEEEEEE"]
    original = track.read_bytes()
    for _ in range(2):
        success, message = Manager.open_file_with_music(track)
        assert not success
        assert "Multiple library tracks match this source" in message
        assert "Resolve duplicates in Music before retrying" in message
    assert not music_double.mutations
    assert not pending_records(track)
    assert track.read_bytes() == original
    assert all(call[3] == known for call in music_double.calls if call[5] == "lookup")


def test_library_switch_between_discovery_and_lookup_stops_before_mutation(
    track, music_double, monkeypatch
):
    run = music_double.run

    def switch_library(command, **kwargs):
        result = run(command, **kwargs)
        if command[8] == "resolve":
            music_double.library = "DDDDDDDDDDDDDDDD"
        return result

    monkeypatch.setattr(music.subprocess, "run", switch_library)
    success, message = Manager.open_file_with_music(track)
    assert not success and "Library changed" in message
    assert not music_double.mutations
    assert not pending_records(track)


def test_existing_music_track_is_reused_without_retroactive_comment_cleanup(track, music_double):
    tags = ID3()
    tags.add(COMM(encoding=3, lang="eng", desc="", text=["Notes sc2am:" + "b" * 64]))
    tags.save(track)
    original = track.read_bytes()
    music_double.marker_matches = [TRACK]
    assert Manager.open_file_with_music(track)[0]
    assert track.read_bytes() == original
    assert not music_double.mutations
    assert not pending_records(track)


@pytest.mark.parametrize(
    "output",
    ["", "opened", "|||0", f"{LIBRARY}|42||0", f"{LIBRARY}|||1", f"{LIBRARY}|{TRACK}||true"],
)
def test_malformed_confirmation_is_not_success(track, monkeypatch, output):
    monkeypatch.setattr(
        Manager, "_run_osascript", Mock(return_value=(True, Mock(stdout=output), ""))
    )
    success, message = Manager.open_file_with_music(track)
    assert not success
    assert "valid library/track confirmation" in message


@pytest.mark.parametrize("kind", ["download", "batch"])
def test_cli_retry_uses_cached_audio_and_only_retries_playlist(
    tmp_path, monkeypatch, music_double, kind
):
    track = tmp_path / "track.mp3"
    url = "https://soundcloud.com/artist/track"
    info = Mock(return_value=(True, {"id": "123", "title": "Track"}, "OK"))
    monkeypatch.setattr(Downloader, "_check_dependencies", lambda _: None)
    monkeypatch.setattr(Downloader, "get_track_info", info)
    real_run = music_double.run
    downloads = []

    def run(command, **kwargs):
        if command[0] == "yt-dlp":
            downloads.append(command)
            track.write_bytes(b"audio payload")
            return Mock(returncode=0, stdout=json.dumps(str(track)), stderr="")
        return real_run(command, **kwargs)

    monkeypatch.setattr(music.subprocess, "run", run)
    cfg = type(
        "Config",
        (),
        {
            "download_dir": tmp_path,
            "open_music_app": True,
            "default_playlist": "Roadtrip",
            "continue_on_error": False,
        },
    )()
    monkeypatch.setattr(main, "_track_context", lambda *args: {"config": cfg, "logger": Mock()})
    from sc2am.metadata import MetadataWriter

    monkeypatch.setattr(MetadataWriter, "write_to_file", Mock(return_value=(False, "no tags")))
    batch = tmp_path / "urls.txt"
    batch.write_text(url + "\n")
    args = [kind, str(batch) if kind == "batch" else url]
    music_double.failure["playlist"] = "before"
    first = CliRunner().invoke(main.cli, args)
    assert first.exit_code == 0
    assert "WARNING:" in first.output
    music_double.failure.clear()
    second = CliRunner().invoke(main.cli, args)
    assert second.exit_code == 0, second.output
    assert "Reused verified download" in second.output
    assert "WARNING:" not in second.output
    assert "1 succeeded, 0 failed" in second.output
    assert len(downloads) == 1
    info.assert_called_once()
    assert music_double.mutations == ["import", "playlist", "playlist"]


def test_damaged_pending_record_cannot_allow_replay(track, music_double):
    music_double.failure["import"] = "no_effect"
    assert not Manager.open_file_with_music(track)[0]
    key = pending_records(track)[0][0]
    with History(track.parent) as history:
        history.put(key, {})
    success, message = Manager.open_file_with_music(track)
    assert not success
    assert "Invalid pending Music record" in message
    assert music_double.mutations == ["import"]


def test_music_scope_uses_library_source_not_reserved_playlist_id():
    from sc2am.music_script import MUSIC_SCRIPT

    # Music 1.7 returned 0000000000000005 for the library playlist, but a
    # distinct persistent ID for its containing source during live acceptance.
    assert "set libraryID to persistent ID of container of libraryPlaylist" in MUSIC_SCRIPT
    assert "set libraryID to persistent ID of libraryPlaylist\n" not in MUSIC_SCRIPT


@pytest.mark.parametrize("failure", ["before", "timeout_before", "no_effect"])
def test_playlist_result_preserves_confirmed_import_evidence(track, music_double, failure):
    music_double.failure["playlist"] = failure
    result = Manager.add_to_playlist_result(track, "Roadtrip")
    assert not result.success
    assert result.imported
    assert music_double.mutations == ["import", "playlist"]


@pytest.mark.parametrize("strict", [False, True])
def test_cli_playlist_only_partial_import_is_counted(track, monkeypatch, music_double, strict):
    downloader = Mock()
    downloader.download.return_value = (True, track, "Downloaded")
    monkeypatch.setattr(main, "_create_downloader", Mock(return_value=downloader))
    music_double.failure["playlist"] = "before"
    flags = ["--strict-import"] if strict else []
    result = CliRunner().invoke(
        main.cli,
        [
            "download",
            "https://soundcloud.com/artist/track",
            "--no-open",
            "--playlist",
            "Roadtrip",
            *flags,
        ],
    )
    assert result.exit_code == (1 if strict else 0), result.output
    assert "Downloads: 1 succeeded, 0 failed" in result.output
    assert "Imports: 1 confirmed, 0 failed/unconfirmed" in result.output
    assert "Playlists: 0 confirmed, 1 failed/unconfirmed" in result.output
    assert "Partial success" in result.output
    assert music_double.mutations == ["import", "playlist"]


@pytest.mark.parametrize("change", ["library", "replacement", "deleted", "nonwritable"])
def test_pinned_target_rejects_stale_destination_before_mutation(track, music_double, change):
    target, error = Manager.resolve_playlist(" roadtrip ")
    assert not error
    assert target.name == "Roadtrip"
    assert (target.library_id, target.playlist_id) == (LIBRARY, PLAYLIST)
    if change == "library":
        music_double.library = "DDDDDDDDDDDDDDDD"
    elif change == "replacement":
        music_double.playlist = "EEEEEEEEEEEEEEEE"
    else:
        music_double.target_error = "Target unavailable; choose a regular user playlist and rerun"
    result = Manager.add_to_resolved_playlist_result(track, target)
    assert not result.success and not result.imported
    assert "SC2AM_NOT_STARTED:" in result.message
    assert not music_double.mutations
    assert not pending_records(track)
    assert music_double.listings == 1


def test_resolved_target_reuses_ids_and_reconciles_pending_membership(track, music_double):
    target, _ = Manager.resolve_playlist("Roadtrip")
    music_double.failure["playlist"] = "timeout_before"
    result = Manager.add_to_resolved_playlist_result(track, target)
    assert not result.success and result.imported
    assert pending_records(track)
    assert not Manager.add_to_resolved_playlist_result(track, target).success
    music_double.member = True
    assert Manager.add_to_resolved_playlist_result(track, target).success
    assert music_double.mutations == ["import", "playlist"]
    assert not pending_records(track)
    assert music_double.listings == 1
    assert len([call for call in music_double.calls if call[5] == "resolve"]) == 4
    assert all(call[4] == LIBRARY and call[6] == PLAYLIST for call in music_double.calls[1:])


@pytest.mark.parametrize("names", [[], ["Roadtrip", "ROADTRIP"]])
def test_resolve_rejects_unavailable_or_ambiguous_names(monkeypatch, names):
    monkeypatch.setattr(Manager, "get_playlists", lambda: (True, names, ""))
    state = Mock()
    monkeypatch.setattr(Manager, "_music_state", state)
    target, error = Manager.resolve_playlist("Roadtrip")
    assert target is None and error
    state.assert_not_called()


@pytest.mark.parametrize("problem", ["deleted", "Smart", "Genius", "folder", "system"])
def test_resolve_checks_target_before_any_track_work(monkeypatch, problem):
    monkeypatch.setattr(Manager, "get_playlists", lambda: (True, ["Roadtrip"], ""))
    run = Mock(return_value=(False, None, f"SC2AM_NOT_STARTED: {problem}; choose a user playlist"))
    monkeypatch.setattr(Manager, "_run_osascript", run)
    target, error = Manager.resolve_playlist("Roadtrip")
    assert target is None
    assert problem in error and "rerun" in error
    assert run.call_args.kwargs["read_only"] is True
    assert run.call_args.args[2][5] == "resolve"


def test_script_uses_pinned_id_and_resolves_without_touching_tracks():
    from sc2am.music_script import MUSIC_SCRIPT

    assert "every playlist whose persistent ID is expectedPlaylistID" in MUSIC_SCRIPT
    assert MUSIC_SCRIPT.index('if actionName is "resolve"') < MUSIC_SCRIPT.index(
        "set matchingTracks"
    )
    assert MUSIC_SCRIPT.index("if smart of destinationPlaylist") < MUSIC_SCRIPT.index(
        'if actionName is "resolve"'
    )
    assert (
        MUSIC_SCRIPT.index('if actionName is "resolve"')
        < MUSIC_SCRIPT.index('if knownTrackID is not ""')
        < MUSIC_SCRIPT.index("whose comment contains sourceMarker")
    )
    assert (
        "if (count of matchingTracks) is 0 then\n"
        "            set matchingTracks to every file track of libraryPlaylist whose comment contains sourceMarker"
    ) in MUSIC_SCRIPT


@pytest.mark.parametrize(
    "output", [f"{LIBRARY}|{TRACK}|{PLAYLIST}|0", f"{LIBRARY}||{PLAYLIST}|1", f"{LIBRARY}|||0"]
)
def test_resolve_rejects_malformed_confirmation(monkeypatch, output):
    monkeypatch.setattr(Manager, "get_playlists", lambda: (True, ["Roadtrip"], ""))
    monkeypatch.setattr(
        Manager, "_run_osascript", Mock(return_value=(True, Mock(stdout=output), ""))
    )
    target, error = Manager.resolve_playlist("Roadtrip")
    assert target is None
    assert "valid library/track confirmation" in error


def test_same_id_remains_selected_after_name_changes(track, music_double, monkeypatch):
    target, _ = Manager.resolve_playlist("Roadtrip")
    music_double.playlist_name = "Renamed"
    # A later name listing would redirect selection to another object or fail.
    listing = Mock(side_effect=AssertionError("Names must not be resolved again"))
    monkeypatch.setattr(Manager, "get_playlists", listing)
    assert Manager.add_to_resolved_playlist_result(track, target).success
    assert Manager.add_to_resolved_playlist_result(track, target).success
    listing.assert_not_called()
    assert music_double.mutations == ["import", "playlist"]
    assert all(call[6] == PLAYLIST for call in music_double.calls[1:])
