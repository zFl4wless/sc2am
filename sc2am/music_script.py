"""Fixed Music automation; all user data travels in argv, never in script source."""

MUSIC_SCRIPT = """
on run argv
    set trackPath to item 1 of argv
    set targetPlaylist to item 2 of argv
    set sourceMarker to item 3 of argv
    set knownTrackID to item 4 of argv
    set expectedLibraryID to item 5 of argv
    set actionName to item 6 of argv
    set expectedPlaylistID to item 7 of argv
    tell application "Music"
        set libraryPlaylist to library playlist 1
        set libraryID to persistent ID of libraryPlaylist
        if expectedLibraryID is not "" and libraryID is not expectedLibraryID then
            error "SC2AM_NOT_STARTED: The active Music library changed. Run the command again."
        end if
        set playlistID to ""
        if targetPlaylist is not "" then
            set matchingPlaylists to every playlist whose name is targetPlaylist
            if (count of matchingPlaylists) is 0 then
                error "SC2AM_NOT_STARTED: The playlist no longer exists. Please check the playlist name."
            end if
            if (count of matchingPlaylists) is greater than 1 then
                error "SC2AM_NOT_STARTED: Multiple playlists have this name. Please rename one or choose a unique playlist name."
            end if
            set destinationPlaylist to item 1 of matchingPlaylists
            if class of destinationPlaylist is not user playlist then
                error "SC2AM_NOT_STARTED: Choose a regular user playlist that can receive tracks."
            end if
            if smart of destinationPlaylist or genius of destinationPlaylist or special kind of destinationPlaylist is not none then
                error "SC2AM_NOT_STARTED: Choose a regular user playlist; Smart, Genius, folder and system playlists cannot receive tracks."
            end if
            set playlistID to persistent ID of destinationPlaylist
            if expectedPlaylistID is not "" and playlistID is not expectedPlaylistID then
                error "SC2AM_NOT_STARTED: The target playlist changed. Run the command again."
            end if
        end if
        set matchingTracks to {}
        if knownTrackID is not "" then
            set matchingTracks to every file track of libraryPlaylist whose persistent ID is knownTrackID
        end if
        if (count of matchingTracks) is 0 then
            set matchingTracks to every file track of libraryPlaylist whose comment contains sourceMarker
        end if
        if (count of matchingTracks) is 0 then
            set sourceFile to (POSIX file trackPath) as alias
            set matchingTracks to every file track of libraryPlaylist whose location is sourceFile
        end if
        if (count of matchingTracks) is greater than 1 then
            error "SC2AM_NOT_STARTED: Multiple library tracks match this source. Resolve duplicates in Music before retrying."
        end if
        if (count of matchingTracks) is 0 and actionName is "import" then
            set importedTracks to add (POSIX file trackPath) to libraryPlaylist
            if class of importedTracks is list then
                if (count of importedTracks) is not 1 then error "Import returned no unique track reference."
                set importedTrack to item 1 of importedTracks
            else
                set importedTrack to importedTracks
            end if
            set importedID to persistent ID of importedTrack
            set matchingTracks to every file track of libraryPlaylist whose persistent ID is importedID
        end if
        set trackID to ""
        set membership to "0"
        if (count of matchingTracks) is 1 then
            set libraryTrack to item 1 of matchingTracks
            set trackID to persistent ID of libraryTrack
            if targetPlaylist is not "" then
                set memberTracks to every track of destinationPlaylist whose persistent ID is trackID
                if (count of memberTracks) is 0 and actionName is "playlist" then
                    duplicate libraryTrack to destinationPlaylist
                    set memberTracks to every track of destinationPlaylist whose persistent ID is trackID
                end if
                if (count of memberTracks) is greater than 0 then set membership to "1"
            end if
        end if
        return libraryID & "|" & trackID & "|" & playlistID & "|" & membership
    end tell
end run
"""
