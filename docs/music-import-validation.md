# Confirmed Music imports: validation and recovery

## Evidence status for issue #80

Automated tests exercise subprocess failures, copied-file identity, repeated
runs, interrupted processes, library changes, partial playlist failure, cache
integrity, and CLI retry with a retained download. They simulate Music responses;
they do not establish Music's actual import behavior.

On 2026-10-07 the production script and the two read-only acceptance scripts
compiled successfully against the installed macOS Music scripting dictionary.
Compilation does not execute imports or prove runtime behavior. **Live validation
is pending**: no isolated test library was available, and the user requested that
this gate remain open in the PR. No personal Music library was modified. Keep the
PR in draft until the following evidence is recorded; do not mark #80 complete in
roadmap #94 before review and merge. Work on dependent #86 remains out of scope.

## Isolated setup (manual, required before running the helper)

Use a disposable macOS user account without an Apple Account signed into Music.
Do not use a personal or cloud-synced library. In that account, quit Music and hold
Option while reopening it, then create a new library named `SC2AM Import Test` in
a temporary test folder. Apple documents the library chooser in
[Use multiple libraries in Music](https://support.apple.com/guide/music/mus7663a920a/mac).
Keep its media folder inside the test area. Confirm visually that the library is
empty and Sync Library is disabled. Create a regular playlist named
`SC2AM, "Test" été`. Enable copying imported files into the Music media folder.

Read the isolated library's identifier only after checking this setup:

```bash
osascript -e 'tell application "Music" to get persistent ID of library playlist 1'
```

Record that ID independently. A library ID alone does **not** prove isolation;
the helper cannot distinguish personal libraries from test libraries. It requires
an explicit isolation acknowledgement and pins every import query/mutation to
the supplied ID so a library switch stops the test.

From the repository with its development environment active, run the following,
substituting the recorded ID. The directory must not already exist:

```bash
PYTHONPATH=. python scripts/validate_music_imports.py \
  --library-id 'REPLACE_WITH_TEST_LIBRARY_ID' \
  --playlist 'SC2AM, "Test" été' \
  --directory "$PWD/music-test-copy-on" \
  --confirm-isolated-library --expect-copied
```

The helper generates three one-second sine-wave MP3s locally using FFmpeg. It
imports them, tests normal repeats, discards real completed mutation responses to
simulate a lost reply, and simulates a playlist failure before dispatch followed
by retry. It then independently requires exactly one library track per source
marker and exactly one playlist entry, and records persistent IDs, imported file
locations and mutation counts in `evidence.json`. Losing a reply exercises the
same reconciliation path as a timeout; it is not a real hung-Music test. The helper
leaves its files and tracks available for inspection and does not clean up Music.

Repeat in a new directory with Music's copying preference disabled and without
`--expect-copied`. Inspect the reported locations; the copy-off result should
reference its source fixtures. Preserve both evidence files outside the checkout
or attach sanitized copies to the PR. They contain local paths.

## Additional manual acceptance checks

- [ ] Record commit SHA, macOS/Music versions, isolation setup, Automation
      permission state, library ID, copy preference, date and tester.
- [ ] Run the helper in both copy modes. Require three PASS lines per run and
      inspect Music for one track/playlist entry per generated source.
- [ ] Quit and reopen Music and rerun imports for the same fixtures using
      `AppleMusicManager.add_to_playlist(Path(...), playlist_name)` from Python.
      Verify the persistent IDs and counts do not change.
- [ ] Remove one fixture from the playlist only; rerun that import and verify one
      restored membership and no additional library track.
- [ ] Temporarily revoke Automation permission in the disposable account. Run an
      import, observe an actionable warning, restore permission, and retry.
      Confirm no duplication. Permission failure during a read sends no mutation.
- [ ] With a permitted public SoundCloud track, run `sc2am download URL --playlist
      'SC2AM, "Test" été'` using a download directory inside the test area. Run the
      same command again without network access and verify `Reused verified
      download`, unchanged track ID, and no additional playlist entry. Repeat
      through `batch` with the same URL twice.
- [ ] Inspect the CLI's current download-based summary and warning exit policy;
      stage-specific counters/strict exits belong to #86, not this change.
- [ ] Record any real Music timeout separately. Do not claim that simulated lost
      replies prove behavior under an actual hung application.

Keep the live gate unchecked until these observations are available. Cloud sync,
iPhone and CarPlay are separate acceptance work and are not implied by a local
track reference. After review and merge of #80, update its checkbox in roadmap
#94; do not start dependent work before that point.

## Recover an unresolved mutation

First rerun the same command with the same download directory. SC2AM rechecks
Music without replaying a pending mutation. If the track or playlist entry has
appeared, its reference is recorded and the pending intent is cleared.

If the warning remains, inspect the active library and requested playlist in
Music. A pending intent can mean the event ran but its result was lost. Never
remove the whole `.sc2am` directory to force retry: this discards the duplicate
barrier and confirmed references. Keep the original MP3 and journal together.

Only if you have established that the requested change did **not** occur:

1. Stop all SC2AM processes and quit Music normally to settle outstanding events.
   Resolve any duplicate or ambiguous tracks first. Back up the journal while
   no SC2AM process is running.
2. Inspect pending records in the affected download directory (read-only):

   ```bash
   sqlite3 -readonly '/path/to/downloads/.sc2am/history.sqlite3' \
     "SELECT key, value FROM records WHERE key LIKE '%:pending:%';"
   ```

3. Clear only the exact inspected pending key, after confirming its source,
   library, stage and playlist. The following prompts rather than clearing every
   record. Replace only the download directory path:

   ```python
   from pathlib import Path
   from sc2am.history import History

   with History(Path('/path/to/downloads')) as history, history.music_lock():
       key = input('Exact pending key inspected above: ')
       assert key.startswith('music:') and ':pending:' in key
       record = history.get(key)
       assert record is not None
       print(key, record)
       assert input('Music is closed and this change did not occur; type CLEAR: ') == 'CLEAR'
       history.delete(key)
   ```

4. Reopen the same library and rerun the original command. Its retained, verified
   MP3 is reused. Do not clear a confirmed `music:` reference or a different
   pending stage. If Music's comment marker or history was manually removed,
   first reconcile the actual existing track; automatic duplicate avoidance may
   no longer have enough evidence.

A changed cached MP3 is also rejected. Restore the recorded file from a trusted
backup or investigate the change before editing history. Restoring history is
preferable to resetting it, especially after an interrupted import.
