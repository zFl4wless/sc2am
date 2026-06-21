# macOS Setup for Apple Music Automation

SC2AM can only automate Apple Music reliably on macOS when a few local prerequisites are in place. This guide documents the checks you should do before importing tracks.

## Required prerequisites

- **macOS is installed and up to date enough to run Music.app automation**
- **Music.app is installed** and can be opened manually
- **Music.app has been launched at least once** so the library is initialized
- **The current macOS user account has access to the Music library**
- **The app you use to run SC2AM** has permission to control Music through macOS Automation

## Grant Automation permission

When SC2AM opens Music.app or adds a track to a playlist, macOS may require Automation permission for the app that launched SC2AM, such as Terminal, iTerm, Visual Studio Code, or PyCharm.

1. Run SC2AM once so macOS can register the automation request.
2. Open **System Settings**.
3. Go to **Privacy & Security**.
4. Open **Automation**.
5. Allow the app you used to launch SC2AM to control **Music**.

If you previously denied the permission, enabling it again here is usually enough. In some cases, you may need to quit and relaunch the terminal or editor app before retrying.

## Verify Music.app manually

Before running SC2AM, confirm that Music.app works on its own:

1. Open **Music** manually.
2. Confirm that the app opens without permission dialogs or library errors.
3. Make sure your playlists are visible in the library.
4. If you use iCloud Music Library or Sync Library, confirm it is signed in and available.

## Common reliability checks

- Use the same macOS user account for SC2AM and for Music.app.
- Avoid running the tool from a temporary shell that cannot retain Automation prompts.
- If playlist operations fail, verify the playlist name matches exactly as shown in Music.app.
- If the app was moved, renamed, or reinstalled, re-check Automation permissions.

## Troubleshooting

### Music.app does not open

- Confirm Music.app is installed and not restricted by Screen Time or device management policies.
- Try opening Music.app manually before running SC2AM again.
- Check whether `open_music_app` is enabled in your SC2AM configuration.

### Automation prompts do not appear

- Check **System Settings > Privacy & Security > Automation**.
- Quit and reopen the app that launches SC2AM.
- If necessary, remove and re-add the permission by toggling the Music entry off and on again.

### Playlist import fails

- Verify the playlist exists in Music.app.
- Ensure the playlist name is spelled exactly the same, including spaces and punctuation.
- If you have multiple playlists with the same name, rename one of them to make the selection unambiguous.

## Related documentation

- [`README.md`](../README.md)
- [`docs/commands.md`](commands.md)
- [`docs/architecture.md`](architecture.md)

