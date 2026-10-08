# First-track user pilot

Preparation for [#89](https://github.com/zFl4wless/sc2am/issues/89): can **3–5
consenting Mac users with Apple Music and SoundCloud** get their first permitted
track playing on an iPhone using the public instructions, and do they return?
**Pilot status: NOT TESTED.** This package contains no participant results and
does not complete #89. The [release device record](../demo/device-acceptance-2026-10-08.md)
is separate evidence, not a target-user trial.

## Organizer preparation

- Once recruitment is separately authorized, include 3–5 volunteers who use a
  Mac, Music.app, an iPhone and SoundCloud. Prefer a mix of Terminal experience
  and record prior SC2AM use. Do not silently exclude unsuccessful attempts.
- Confirm informed consent for the trial and separately for anonymized findings
  or follow-up. Participation is voluntary; participants may stop at any time.
- Give each participant a neutral ID (`P01`–`P05`) and a private copy of the
  [trial record](trial-template.md) and [task card](#participant-task-card).
  Keep contact information outside records.
  Collect only relevant versions, setup state, observations and consented notes;
  exclude Apple Account identifiers, personal playlist/library contents and
  unredacted logs. Publish a sanitized summary only with separate authorization.
- Agree on a roughly 30–45-minute active session and a later check if Apple sync
  is still waiting. This is a session budget, not an expected sync duration.
  Agree how notes will be retained/deleted and whether manual feedback at 7 and
  14 days is welcome. Do not schedule automations.

This preparation authorizes no recruitment, messages or data collection.

## Participant task card

Use the public guides first. Record anything confusing before asking for help;
help is allowed and must be recorded. You do not need to share your screen or
account, or supply library screenshots.

1. **Start the clock when you first open the [README](../../README.md)** for this
   attempt, before installation or setup. Record the timestamp and timezone.
   Follow its [v2.1.0 installation](../../README.md#end-user-installation-on-macos)
   and the [Mac/iPhone setup guide](../macos-setup.md). Use the published wheel,
   not a contributor install. Run `sc2am doctor`; note its result and any fixes.
   It does not verify Automation permission or device sync.
2. Choose one single SoundCloud track you have permission to download and that
   is not already imported by SC2AM. Choose an existing, uniquely named regular
   Music playlist you are comfortable adding it to. If none is suitable, create
   a regular test playlist and record this extra step. Stop if the track's
   permission is unclear. Record a sanitized source ID and approximate duration.
3. Activate the installation's virtual environment. Replace **both** example
   values with your track URL and playlist name, then run:

   ```bash
   sc2am download "https://soundcloud.com/artist/track" --playlist "My Playlist" --strict-import
   ```

   Record command start, the MP3 download result, and the local import and
   playlist results separately. Check the intended track in Music on the Mac
   and the selected playlist. A saved MP3 or exit code alone does not establish
   import or phone success. Read any Automation prompt before granting access.
   For uncertain imports, follow [recovery](../music-import-validation.md)
   rather than deleting the journal or repeatedly importing by hand.
4. Follow your existing Apple-managed route in the setup guide. For Sync Library,
   record the Mac cloud status exactly (`Waiting`, `Uploaded`, `Matched`, etc.)
   and when first observed. For an already configured Finder route, record when
   Finder reports transfer complete. Then find the track in Music on the iPhone;
   record when first seen, independently of the Mac status. SC2AM does not
   automate these steps. A catalog match is Apple's decision, not SC2AM's import.
5. Start the track from the beginning on the iPhone and confirm **audible playback
   with advancing elapsed time for at least 10 seconds**. Record that timestamp:
   it ends the primary first-playable-track measurement. Note network state;
   online playback does not prove an offline copy is stored.
6. For Sync Library, download the track on the iPhone and wait for download
   completion; record it separately from the SoundCloud-to-Mac download. Finder
   transfer supplies the phone copy through its own route. With Wi-Fi and cellular
   data disabled, start fresh and listen for at least 10 seconds. Record the
   result and restore your previous connectivity. This is a separate offline
   check. CarPlay is optional and outside the required first-track task; if
   checked, do so parked and record it separately.

Use your current, chosen sync route. Do not switch Sync Library modes just for
the pilot, enable sync for an unrelated test library, change unrelated Automation
settings or accept **Erase and Sync**. If no safe configured route is available,
stop at the Mac result and record the setup blocker. Participants perform their
own chosen actions; organizers do not access accounts or control libraries/devices.

If blocked or still waiting at the session end, record the last stage and elapsed
time. Agree on a later observation, for example the next day; there is no promised
cloud completion time. Missing observations remain `NOT TESTED` or `WAITING`.

## Timing and help rules

Use wall-clock timestamps in one timezone. Total time is first confirmed iPhone
playback minus first README opening, **including installation, help, retries,
waiting and breaks**. Record breaks so active time can be reported separately;
never silently subtract them. If playback is not reached, report “not reached
after …”, not zero or a successful duration. Unknown timestamps are `UNKNOWN`.
Polling gives time to first observation, not exact service completion time.

Let the participant try the guides without coaching. For every intervention,
record when, the blocker, what help was given and whether it resolved the problem.
Distinguish participant-reported observations from direct organizer observations.
The required fields and stage timestamps are in the blank trial record.

## Follow-up and launch gate

With prior consent, request manual feedback around **day 7 and day 14** after the
trial: did they use SC2AM again for another permitted track, was it playable on
the phone, what help was needed, and why did they return or stop? “Would use” is
intention; count only reported actual reuse. No response remains `NOT TESTED`.

Use the [findings template](findings-template.md) after the trials. Create a focused
follow-up issue for each reproducible blocker: affected stage, anonymized IDs,
version/setup, sanitized reproduction, expected/actual result and validation needed.
Link related reports; do not publish raw records or contact details.

Before broader outreach (#93), review 3–5 documented attempts, including failures,
help and reuse outcomes. Fix and recheck SC2AM or guide failures that prevent
installation, correct local import or completion of the documented phone route;
any file/library safety issue blocks launch. Classify Apple/service/setup waiting
separately and supply understandable guidance rather than claiming a SC2AM fix.
Retest an affected journey after its fix, preferably with a fresh participant.
Unresolved required-stage blockers keep the broader launch gate open. Record the
owner's decision, remaining limitations and follow-up issues; do not infer a pass
from stars, CI, the animated demo or the earlier device report. #89 stays open
until actual trials, findings and required fixes satisfy its criteria. #90/#91
remain later exploration, and this package does not authorize outreach.

## Optional invitation draft — not sent

> Would you like to try SC2AM's first-track instructions on your Mac and iPhone?
> We are looking for 3–5 volunteers who use Apple Music and SoundCloud. Allow about
> 30–45 minutes of active testing; Apple's sync may need a later check. Use only a
> track you have permission to download. You can stop at any point, and no account
> details or screen sharing are needed. With your consent, we would record
> anonymized setup, time, blockers and help, and ask about actual reuse after
> roughly 7 and 14 days. We will agree on note retention before you start.
