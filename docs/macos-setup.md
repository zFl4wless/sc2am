# macOS Setup for Apple Music Automation

SC2AM can only automate Apple Music reliably on macOS when a few local prerequisites are in place. This guide documents the checks you should do before importing tracks.

For the end-user installation commands (Python 3.10+, Homebrew FFmpeg, first
download and upgrades), follow the single workflow in the README's
[macOS installation section](../README.md#end-user-installation-on-macos). It
installs the verified GitHub release wheel. Do not repeat dependency
installation with `requirements.txt`; the wheel already declares the Python
runtime dependencies.

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

## From a Mac import to iPhone and CarPlay

SC2AM downloads and imports an MP3 into the Music library on this Mac. It does
not sync an iPhone, upload a track, or confirm cloud availability. Choose one of
the following Apple-managed paths to make the track available on the phone.

### Sync Library (Apple Music or iTunes Match)

Sync Library requires an Apple Music or iTunes Match subscription. Sign in to
the same Apple Account in Music on the Mac and Apple Music on the iPhone, and
connect both devices to the internet.

1. On the Mac, open **Music > Settings > General** and enable **Sync Library**.
2. On the iPhone, open **Settings > Apps > Music** and enable **Sync Library**.
3. In Music on the Mac, wait for the cloud library update to finish. Find the
   imported song in **Songs**; you can show the **Cloud Status** and **Cloud
   Download** columns from **View > Show View Options**.
4. When the song appears in the iPhone Music library, download it there before
   going offline. A Mac-side import or a song visible in the iPhone library
   alone does not mean its audio is stored on the iPhone.

Apple's current Music guide documents a cloud library limit of 100,000 songs
(excluding iTunes Store purchases) and a maximum size of 200 MB per file. If a
track is over that file limit or shows as ineligible, manual Finder sync may be
an option. Catalog matching is controlled by Apple: a match may be offered at
catalog quality, while other tracks are uploaded at their original quality.
This is not a guaranteed conversion or quality upgrade. See Apple's guides for
[Sync Library requirements](https://support.apple.com/en-us/118285) and
[cloud library limits](https://support.apple.com/guide/music/access-your-music-library-on-all-your-devices-musa3dd5209/mac).

### Manual Finder sync (without Sync Library)

If you do not use an Apple Music or iTunes Match subscription, sync selected
music directly from the Mac:

1. Connect the iPhone to the Mac with USB, unlock it, and approve **Trust This
   Computer** if prompted.
2. In Finder, select the iPhone in the sidebar, open **Music**, enable **Sync
   music onto [device]**, choose the whole library or selected artists, albums,
   genres, or playlists, then click **Apply** or **Sync**.
3. Keep the phone connected until Finder reports that syncing has finished.
   Once transferred, the selected tracks are stored on the phone and can play
   offline. Finder can also sync over Wi-Fi after it is enabled in the device's
   **General** settings.

Finder music sync and Sync Library are separate modes. Apple says turning Sync
Library off removes downloaded music from the iPhone; read the on-screen prompt
and make sure you can download those tracks again before changing modes. Finder
music syncing is unavailable for items currently managed by Cloud Music Library;
Apple's [syncing overview](https://support.apple.com/guide/mac-help/intro-to-syncing-your-mac-and-your-devices-mchl923c1147/mac)
explains that Finder sync for music requires turning off Cloud Music Library.
Back up important library files before switching. A device can sync with only
one Apple Music or Apple TV library at a time. If Finder offers **Erase and
Sync**, do not accept unless you intend to replace all content of that type on
the iPhone with this Mac's library. See Apple's [Finder sync
instructions](https://support.apple.com/en-us/102471).

### Play offline and in CarPlay

With Sync Library, wait until the track appears on the iPhone, then use **More >
Download** (or touch and hold the song and choose **Download**) in Music. With
Finder sync, the selected files are transferred to the phone. Test playback on
the iPhone with Wi-Fi and cellular data disabled before relying on offline use.

Set up CarPlay once with a compatible vehicle, then connect the iPhone by USB
or wirelessly as supported by the car. On the iPhone, **Settings > General >
CarPlay** shows configured vehicles. In CarPlay, open **Music** or ask Siri to
play the track. CarPlay can play music available on the iPhone. A cloud-only
track needs a network connection; a downloaded or Finder-synced track is the
choice for offline trips. CarPlay availability depends on the vehicle and
region. See Apple's guides to [set up CarPlay](https://support.apple.com/en-us/108415),
[download music for offline listening](https://support.apple.com/guide/iphone/add-music-and-listen-offline-iph0cff2d191/ios),
and [play music with CarPlay](https://support.apple.com/guide/iphone/play-music-with-carplay-iphebcc8e9e6/ios).

SC2AM asks yt-dlp for the best available audio and converts it to MP3 with a
192-kbit/s encoding target. That setting cannot restore detail absent from the
SoundCloud source; conversion may reduce quality, and the source's actual
quality can be lower than the output target. Tags and cover art do not change
the audio quality. Apple Music may match a file to its catalog, but SC2AM does
not request or guarantee a higher-quality replacement.

### When the track is on the Mac but missing on the iPhone

- Confirm both devices use the same Apple Account and Sync Library is enabled
  on both. Sync Library needs Apple Music or iTunes Match; Finder sync does not.
- Confirm both devices are online. In Music on the Mac, choose **File > Library
  > Update Cloud Library**, then leave the Mac online while the cloud status is
  **Waiting**. Sync can take time; there is no guaranteed completion time.
- In **Songs**, show **Cloud Status** and **Cloud Download**. A **Waiting** item
  has not synced yet. An exclamation mark means Music cannot find the source
  file; use **Locate** to reconnect the original MP3 instead of deleting and
  importing duplicates.
- Check that the file is below Apple's documented 200-MB limit and that the
  library has not reached 100,000 songs. If Finder sync is the chosen fallback,
  follow its library and erase warnings above.
- On the iPhone, check **Settings > Apps > Music > Sync Library**, confirm free
  storage, reopen Music, and give the library time to update. Do not toggle Sync
  Library off and on as a first fix: Apple says turning it off removes
  downloaded music from the phone. See Apple's [missing songs and cloud-status
  troubleshooting](https://support.apple.com/en-us/118287).

Successful local import confirmation from SC2AM does not verify any of these
cloud, iPhone, offline, or CarPlay steps. Test those on your own devices; the
separate release acceptance checklist tracks live device verification.

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
- [`docs/music-import-validation.md`](music-import-validation.md) (local Music import test scope)
