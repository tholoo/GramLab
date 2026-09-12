# Verify original albums and the public runner

Type: task
Status: ready-for-agent
Work state: claimed
Owner: album-native-acceptance
Blocked by: 112 and 113

Sequencing note: ticket112 is resolved and ticket113's reviewed adapter, immutable normal31 APK and
source/build provenance are integrated and complete. Its remaining app-process green is deliberately
part of this ticket's first focused guest so the approved normal31 inventory remains exactly three
serial runs. Implementation and host checks may proceed now; the first guest closes that final
ticket113 gate before the public and final-regression guests run.

After the core and adapter are integrated, add the focused real-bot/scenario and public-runner
acceptance. Own `src/gramlab/runner.py`, `src/gramlab/__main__.py`, `src/gramlab/_android.py`,
`src/gramlab/_android_rich_buttons.py`, and `src/gramlab/_interactions.py` only if a fixed-version
audit proves it necessary; own new `tests/fixtures/media_group_bot.py`,
`tests/probes/media_group_round_trip.py`, `tests/probes/android_media_groups.py`,
`tests/test_media_group_round_trip.py`, `tests/test_android_media_groups.py` and
`tests/test_media_group_runner_v6.py`. Add exact integer6 throughout the public runner/CLI/Android/
rich-interaction selectors while preserving default3, explicit3–5, and bool/noninteger/7 rejection.
Carry the grouped-edit branch selected in ticket111.

Native evidence must show an initial two-photo stock collage with a caption on the first member only
and a live two-document stock list with distinct ordered filenames/captions. The second document's
first body truncates after its sibling completes; require unchanged two-member group topology, one
original radial retry, exact success counts of one and two, exact final/presentation/cache bytes, no
partials and zero cold-restart GETs. Pair screenshots/XML geometry and row-order assertions with
decoded grouped IDs/flag17, exactly one two-update live envelope and one pre-group→group-end cursor
transition. Retain World/Bot API comparisons, request ledger, result/report and provenance.

The public E2E selects bridge6 explicitly with mixed document/custom-emoji history. The contained bot
sends a two-photo group; after its original collage capture the scenario sends a native composer
trigger, the same bot receives it and sends a two-document group, and the scenario captures the live
group without sleeps. Compare complete Bot API responses/history/events/v6 changes and both original
captures. The dedicated native gate, not repeated public capture, owns restart/cache proof.

Keep zero accounts, IPv4/IPv6 denial, loopback-only transport and component filesystem isolation.
Use the single normal31 APK from ticket113 for exactly three serial runs: focused album, public v6,
then one final inventoried `pytest -m android` current-APK regression with no skips after fixes settle.
Never rebuild between them. Retire every successful guest and remove hash-verified APK copies after
extracting evidence; retain one immutable normal31 APK.

## Worker implementation evidence

- The public selector now admits only exact integer bridge versions 3, 4, 5 and 6, preserving the
  default of 3 and rejecting booleans, nonintegers and 7 before run creation. The selected version
  is retained as an explicit top-level run-input/result configuration field, passed into both the
  Android runtime and simulated `Interactions`, and used for virtual callback creation. The native
  rich-button observer also admits v6 without changing its v4/v5 behavior.
- `media_group_bot.py` makes two real multipart `sendMediaGroup` calls. The contained public
  scenario starts the bot, captures the initial two-photo group, sends the original-composer-
  compatible `documents / اسناد` trigger, and captures the two-document group without a fixed
  sleep. Its retained output compares complete Bot API responses, grouped-edit rejections, World
  history/events and bridge-v6 snapshot/changes state. Both scenario receipts equal the retained
  interactions; their exact operations/texts, accepted trigger messages, native flags and single
  original send actions are guarded, including rejection of a virtual fallback in native mode. An
  independently authored projection of each canonical photo/document history row, including its
  complete dynamic file descriptors, must equal the entire retained `sendMediaGroup` response.
- The focused Android selector is one test and one `android_guest.main` lifecycle. Its probe first
  invokes all 48 existing app-process codec/carrier cases in the same AVD, then installs normal31
  for stock UI/runtime/cache acceptance. The initial screenshot waits for both original photo
  transfers and retains a 320x640 nonblank PNG plus XML/caption evidence; the grouped carrier codec
  supplies decoded grouped IDs and flag17. No grouped-photo observer is activated because the
  existing normal31 observer intentionally rejects `getCurrentMessagesGroup() != null`.
- The probe publishes the two distinct documents after the initial snapshot, requires exactly one
  `events_applied/messages` trace row with token 2 and records the bridge cursor transition from
  position 2 to 4. The proxy retains minimal decoded snapshot/change positions and an explicit
  publication barrier: `begin_publication` drains handler forwarding, then captures the trace
  boundary before the atomic World commit. Every preceding `TL_updates_getDifference` request must
  have an exact same-account/token response, while operations begun during the commit remain in the
  checked application slice. Position-4 snapshots remain physically blocked until the host observes
  the one token-2 `events_applied` trace. This admits legitimate repeated position-2 startup
  snapshots and even a snapshot arriving early but forwarded only after application, while proving
  an atomic `[3, 4]` response to `after=2`, no pending/prior `getDifference`, resnapshot or forwarded
  position-4 application, no `after=3` or 409, and subsequent `after=4` polling. It freezes ordered
  XML row bounds, truncates only document 2's first body after document 1 completes, and collects at
  least 20 stable observations spanning two seconds before the original mdpi radial retry.
  Host-monotonic proxy/tap timestamps prove the second D2 request begins only after the tap starts.
  Exact status/delivered byte digests bind D1 full once and D2 partial then full. Exact internal
  `./cache4/-1_-1.txt` and
  `./cache4/-1_-2.pdf`, plus full package-external `Telegram Files/first-album.txt` and
  `Telegram Files/second-album.pdf` paths, bind both final and cold inventories with no partials or
  cold document GETs. Five original PNG/XML pairs are retained; collage layout remains explicitly
  limited to manual inspection.
- The focused report helper embeds all five captures plus network/profile/APK/source digest and
  verified-provenance evidence. The native selector now requires `GRAMLAB_ANDROID_APK_PROVENANCE`
  and calls the existing complete toolchain/series verifier before entering the guest, while
  retaining raw result/stdout/stderr and the verified values. The follow-up affected host selection
  passes 78/78 with no failures or skips under the documented isolated network guard; its JUnit is
  `artifacts/album-native-host-04.xml`. Ruff check/format and strict mypy pass the changed harness.
  No Android guest or APK build ran in this worker.

## Remaining coordinator gates

Run `test_actual_album_codec_ui_retry_and_cold_cache_share_one_guest` first with the immutable
normal31 APK and codec probe APK, then inspect all five original captures and retained XML. This is
normal31 guest one and closes ticket113's pending green codec gate. Run the separate public-v6
Android selector second, then the complete inventoried current-APK Android regression third. Do not
rebuild normal31 between them; keep this ticket claimed until those native results pass.

## Coordinator focused-run correction

The first combined native attempt at merge commit `9b037d4` completed its one-guest codec/UI
lifecycle and retained all five UI captures, but the host oracle correctly failed four legacy-v5
codec cases. The immutable normal31 code requested `/v5/snapshot`; the newly combined fixture had
hard-coded its queued snapshot response to `/v6/snapshot` and returned HTTP 404. The remaining v6
codec rejection results and the complete UI probe were retained at
`artifacts/album-normal31-focused-01-work/`; JUnit is
`artifacts/album-normal31-focused-01.xml`. This is a harness failure, not an accepted Android gate.

The coordinator widened only the test fixture's queued-snapshot route to exact v5/v6 and added a
host test which performs an authenticated v5 request through the real fixture server. That focused
host selection passes 22/22; Ruff format/check and strict mypy pass both changed harness files. The
APK, codec probe and Android source were not changed or rebuilt. A fresh combined focused gate and
manual five-capture inspection remain required before ticket113 or this ticket can resolve.

The corrected second attempt served v5 correctly, completed the full guest/UI lifecycle, and then
exposed a separate authored-oracle error: `photo(..., None)` deliberately means omission, so the
case named `group-id-null` contained no `media_group_id` and normal31 correctly accepted it as two
standalone photos. Evidence is retained at `artifacts/album-normal31-focused-02-work/` with JUnit
`artifacts/album-normal31-focused-02.xml`; it is not an accepted gate. The case now injects literal
JSON null into both messages, and the host inventory asserts the fields cannot silently become
omissions again. Its three focused host checks and the same two-file Ruff/mypy scope pass. This was
again test-only; normal31 and its probe remain byte-identical. A fresh combined focused run remains
required.
