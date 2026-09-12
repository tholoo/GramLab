# Verify custom emoji through bridge v5 and the current APK

Type: task
Status: ready-for-agent
Work state: resolved
Owner: coordinator
Blocked by: none

Custom emoji is functionally implemented and has strong normal24 lifecycle, codec and fault
evidence. Normal30 includes later patches that overlap Bridge, Runtime, RichMessage, Media and
FileLoader, while its public document scenario proves only one static caption emoji. Add a complete
reusable public-runner workflow and rerun the existing focused surfaces on the current APK.

Own this ticket and new files:

- `tests/fixtures/custom_emoji_runner_bot.py`;
- `tests/custom_emoji_runner_scenario.py`; and
- `tests/test_runner_custom_emoji_v5.py`.

Do not change production modules, existing tests/fixtures, Android patches, shared docs, profiles,
assets or dependencies. Use the existing immutable WebP/WebM/thumbnail fixtures and explicit bridge
5. Request additional ownership before editing it.

Through `python -m gramlab run`, register both static transparent WebP and transparent VP9 WebM,
deliver an incoming ordinary custom-emoji entity, and have the same contained bot publish ordinary
and rich carriers including a custom emoji inside a rich-button label. Perform one original inline
callback that edits static carriers to animated ones. Capture initial, edited and cold-relaunched
views. Compare complete Bot API responses/updates, World histories/events, v5 snapshots/changes,
callback creation/answer, canonical alternatives distinct from catalog fallback, exact bot file
downloads and scenario output. Simulation uses the same independent semantic oracle without making
rendering claims.

Native assertions require original static/animated carriers, changing transparent frames, button
label placement, exact transfer/cache reuse, zero restart GETs, zero accounts, network/filesystem
containment, immutable APK identity and inspected screenshots/XML. The worker runs red/green
contained simulation, focused host checks, Android collection, strict mypy and Ruff only. No guest,
build or full gate.

Coordinator uses canonical normal30 for the new public case and the existing codec, lifecycle and
full fault tests. The focused shared-thumbnail test is redundant if the full fault case passes.
Retain exact results/captures/reports; retire each guest and remove hash-verified run-local APK
duplicates afterward.

## Comments

### Worker implementation

`custom-emoji-runner-v5` added only the three assigned public-runner files. The contained scenario
registers the existing transparent static WebP and transparent VP9 WebM through the public SDK,
creates an incoming ordinary static entity, and drives one real Bot API peer. That peer publishes
an ordinary static entity with an inline callback plus a rich paragraph and disabled rich-button
label whose canonical alternatives (`RICH-ALT` and `BUTTON-ALT`) deliberately differ from the
catalog fallback. One inline action answers its frozen callback and edits all three bot carriers to
the animated document. The scenario retains initial, edited and independent cold-relaunch
captures.

The independent test oracle spells the complete World history/event order, Bot API
requests/responses and update boundaries, exact bot downloads and headers, recipient-only grants,
scenario output, source fingerprints, v5 snapshot/changes/callback dependencies, and live v5 HTTP
snapshot/change/document/asset responses. Simulation makes no renderer claim. The Android-marked
case reuses the same oracle and additionally requires bridge5/APK identity, three original cold
launches and PNGs, the exact original inline target, zero accounts, and the existing guest
network/filesystem containment result.

The meaningful red baseline reached a passing contained registration/publication/callback/edit
workflow, then failed solely because only the initial and edited captures existed:

```text
tools/dev default --command unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest -p no:cacheprovider \
  tests/test_runner_custom_emoji_v5.py::test_public_runner_retains_initial_edited_and_relaunched_custom_emoji \
  -q --junitxml=artifacts/custom-emoji-runner-v5-red.xml'
1 failed: expected custom-emoji-relaunch; observed initial and edited only
```

Red JUnit SHA-256 is
`bdf0d0bc33e9a01b1cb11d14325055d316264c00fb24a184c669b80635c26204`.
After adding the third capture, the complete host oracle including live v5 HTTP passes. A final
focused regression passes all four selected cases in 8.094 seconds:

```text
tools/dev default --command unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest -p no:cacheprovider \
  tests/test_runner_custom_emoji_v5.py tests/test_runner_custom_emoji_registration.py \
  tests/test_runner_custom_emoji_captures.py tests/test_custom_emoji_round_trip.py \
  -m "not android" -q --junitxml=artifacts/custom-emoji-runner-v5-final.xml'
4 passed
```

The final JUnit SHA-256 is
`5fe5c3f4d2db061a2d6fd01ea4583cb7baaff43551b93db180d336bfe35c659a`.
The new public-runner `result.json` SHA-256 is
`9a12755b2651f9c2a82742f549ac59a3e6c7d0c8885a6b720e5bd9ce92c33654` under the ignored
`artifacts/custom-emoji-runner-v5-final-work/` tree. Scoped strict mypy reports no issues in
the three implementation files; Ruff check and format-check pass; the Android selection collects
exactly one case without executing a guest; `git diff --check` passes.

No Android guest or APK build ran on the worker branch. The Android case is collected for the
coordinator's serialized normal30 gate. Changing transparent frames, original transfer/cache reuse
and zero restart GETs remain the existing lifecycle/fault suite's responsibility and are not
inferred from these three ordinary runner screenshots.

### Coordinator native red and harness correction

The first normal30 run stopped at the new public case after107.224 seconds and retained
`artifacts/custom-emoji-normal30-native-01.xml`. The original UI had already rendered `Incoming`,
`Ordinary` and `Rich / غنی RICH-ALT`; UIAutomator represented the disabled rich-button row as its
documented generic `Buttons` text rather than exposing the drawn `Badge / نشان BUTTON-ALT` label as
an accessibility node. The scenario had incorrectly required the exact button label as a shared
capture-readiness substring, so Android timed out before taking its first screenshot.

The correction keeps the exact rich-button alternative in the independent semantic oracle and
uses only `Incoming`, `Ordinary` and `Rich` as cross-mode capture readiness. The Android assertion
separately requires its observed `Buttons` marker; the existing pixel-level lifecycle gate remains
responsible for proving static/animated glyphs in the distinct button region. The focused public
host case then passes under the pinned offline profile at
`artifacts/custom-emoji-runner-v5-fix-host-04.xml`; strict mypy, Ruff and format-check also pass.
No production module, Android source/patch, content or fidelity contract changed.

### Coordinator launch-lifecycle diagnosis

The second normal30 attempt reached and retained the initial original-client capture, then failed
before the inline callback because the immediate `am force-stop`/`am start -W` sequence did not
establish a fresh activity launch. The prior application process was still alive while its message
load continued. The generic launch error was therefore not relaxed: `_open_chat` now polls the
package PID after force-stop and proceeds only after `pidof` proves the process absent. Unexpected
status and a process surviving the five-second bound remain fail-closed. A focused host regression
first failed because no PID check occurred at all in
`artifacts/android-launch-stop-red-01.xml`, then the launch tests passed **3/3** in
`artifacts/android-launch-stop-green-02.xml`.

The subsequent combined host gate exposed a separate scheduling race in this ticket's fixture:
the bot had printed its complete final transcript but the scenario could finish before the
supervisor observed the bot process exit, contradicting the strict clean-exit assertion. The
scenario now performs a bounded public `bot_status` handshake and requires generation 1 to have
exited with code zero. That case passed five consecutive contained runs at
`artifacts/custom-emoji-exit-handshake-host-{1..5}.xml`. The full affected host selection then
passed **152/152** at `artifacts/current-acceptance-host-after-launch-fix-02.xml`; strict mypy and
Ruff check/format pass for all changed files. The retained native attempt is
`artifacts/custom-emoji-normal30-native-02.xml`; it is diagnostic evidence, not a native pass.

The third normal30 run completed the complete native workflow with `result.json` outcome `passed`
in80.319 seconds: all three captures, the exact original inline callback, edits and cold relaunches
were retained. Pytest then found an oracle-only redaction mismatch. The scenario's JSON transcript
correctly retained UIAutomator's non-secret target attribute `password="false"`, while final evidence
correctly applied the generic key redactor and stored `[REDACTED]`. The oracle now models and checks
both representations explicitly. It passes against the retained native result and its host case,
and strict mypy/Ruff pass. `artifacts/custom-emoji-normal30-native-03.xml` remains a failed JUnit;
a fresh passing JUnit is still required before accepting the native case.

### Current-APK public acceptance and focused regression

The fresh public rerun passes **1/1** on the unchanged reviewed normal30 APK in81.195 seconds at
`artifacts/custom-emoji-normal30-native-04.xml` (SHA-256
`cd33a62671e1b72e852a49cef9fb1d4c2d46cb050527bf5da0ce8cec0e4a31be`). The runner itself passed
in79.945 seconds. Its receipt proves bridge5, API36, the exact immutable APK identity, zero Android
accounts, guest network/filesystem containment and clean bot/client process completion. Manual
inspection of all three original-client PNGs confirms the static blue authored glyph in the
incoming, ordinary, rich and disabled-button carriers, the changed animated glyph in each bot
carrier after the real callback, and the edited state after a cold relaunch. This closes the new
public case; it does not replace the existing transparent-animation timing, codec or fault gates.

The existing normal30 codec gate also passes. Two lifecycle attempts retain every authored
quarter-frame state in lockstep across all three bot carriers and pass the spatial detector, while
the incoming static control remains unchanged. The first attempt misses the exact global one-second
phase feasibility interval by80 milliseconds across roughly6.8 seconds; a single controlled rerun
under recorded host pressure has capture gaps large enough to skip as many as three quarter-frames.
They remain honest failures at `artifacts/custom-emoji-normal30-regression-{01,02}.xml`; the existing
timing/fidelity criterion has not been weakened. The previously accepted normal24 evidence still
satisfies that same exact phase oracle. A normal30 lifecycle pass or an explicit fidelity decision
is therefore still required.

The full fault probe completed every native fault/recovery phase and passed its semantic transfer,
terminal-error, zero-asset, idle-count and shared-thumbnail observations, but its first failed/idle
pixel pair differed. Their UI XML was identical and the later mixed and partial pairs were
pixel-identical. Retained startup diagnostics show the known intermittent AOSP UWB initialization
failure started a full `dumpstate` system report; its system screenshot toast covered only that
first fault capture. This is platform-report interference, not evidence of a product or fault-
recovery regression. The combined artifact is
`artifacts/custom-emoji-normal30-codec-fault-01.xml`; the fault case remains unaccepted until a
clean exact-pixel rerun passes.

The fault probe now uses a shared bounded barrier after APK installation: it polls only the
dedicated guest's `dumpstate` PID, requires a continuous one-second report-free interval before
capturing, fails closed on unexpected status or a 60-second bound, and records whether a report was
observed plus elapsed/quiet timing. It does not disable UWB, alter the emulator profile, retry the
test or relax the exact-pixel oracle. The focused test first failed at collection because the
helper did not exist (`artifacts/system-report-barrier-red-01.xml`), then passed **8/8** at
`artifacts/system-report-barrier-green-01.xml`; scoped Ruff, format and strict mypy checks pass.

The fresh focused fault rerun passes **1/1** in281.715 seconds at
`artifacts/custom-emoji-normal30-fault-03.xml` (SHA-256
`30b5d3d0e3d96a2dabbf37e4f3ebcc2a11f31566ac629272d5c2d93cc1088f40`). This boot observed no
platform report and established the required quiet interval in1,257.695 milliseconds. All three
failed/idle carrier crops have zero changed pixels and identical UI XML. Each recovery renders the
exact authored blue glyph count; the shared-thumbnail case issues one paired document request and
one held asset request, retains the glyph after the first carrier is removed, and completes the
exact cached asset. Original screenshots were manually inspected and contain no system toast. The
copied APK SHA-256 exactly matches normal30, API36 and zero-account/network/filesystem containment
checks pass. The earlier combined fault failure remains useful diagnostic evidence but is superseded
for acceptance by this clean exact-pixel run. A setup-only `fault-02` invocation selected an internal
serialized profile instead of the schema-wrapped runtime manifest and failed before guest launch;
it is retained as `artifacts/custom-emoji-normal30-fault-02-setup-red.xml` and makes no product or
native claim.

After acceptance review, the coordinator removed48 superseded guest-disk files and9 run-local APK
copies whose SHA-256 matched the retained canonical normal30 APK, reclaiming9,478,701,056 allocated
bytes. The cleanup revalidated the canonical APK plus371 retained JUnit/JSON/log/XML/PNG evidence
files after deletion. The latest normal30 lifecycle-failure guest disk was retained temporarily for
the timing diagnosis below; all other reports and captures remained independently inspectable.

### Normal30 lifecycle timing diagnosis

The clean first lifecycle attempt is not a spatial or carrier-consistency failure. All24 captures
match authored quarter-frames exactly in the ordinary, rich and rich-button regions, and the three
carriers produce the same state sequence. Capture intervals span about7.43 seconds. The unchanged
fixed one-second-phase oracle has a latest lower bound of `10,000,001` nanoseconds at frame22 and an
earliest upper bound of `-70,000,000` nanoseconds at frame0, so the complete24-frame intersection
misses by80 milliseconds. Every carrier nevertheless has an exact22-frame passing window beginning
at frame2; that window covers about6.84 seconds and more than six authored cycles. The pressure rerun
has longer240–420 millisecond acquisitions, skips up to three quarter-frames across its complete
10.18-second span, and still retains a19-frame passing window beginning at frame1. It is useful
capture-pressure evidence, not a substitute pass.

Removing the fixed80-millisecond post-capture pacing would save less than two seconds and does not
account for the clean run's full-horizon phase drift. Repeated blind native reruns are therefore
paused. The accepted normal24 run remains the proof that the current strict full24-frame oracle is
achievable on that checkpoint. Normal30 lifecycle acceptance now needs either a clean full-horizon
pass or explicit approval to replace that criterion with a bounded contiguous-window contract.
No cadence, renderer, spatial check, state-order check or fidelity criterion has been changed.

After extracting those interval constraints, the coordinator retired the final six AVD image files
from the pressure rerun and reclaimed951,885,824 allocated bytes. The cleanup revalidated234
remaining files, including both failed JUnits, every raw/PNG frame, result, guest observation and
log, before and after deletion. No normal30 custom-emoji or residual-rich guest disk remains; the
ignored receipt is `.cache/local-notes/guest-retirement-custom-emoji-normal30-final-01.json`.

### Approved bounded timing criterion

On 2026-09-12 the user approved the recommended bounded contiguous-window rule. Every one of the24
captures must still match an authored frame; the complete sequence must still preserve forward
quarter-frame order, observe all four states and remain synchronized across ordinary, rich and
rich-button carriers. The one-second phase feasibility test may succeed on any contiguous window of
at least20 captures spanning at least5 seconds instead of requiring one phase to fit the entire
recording. Ticket120 owns the independent oracle change and replay; no pixel, spatial, state-order,
carrier-consistency, transfer, cache, restart or fault criterion is relaxed.

The integrated bounded oracle passes its32-case visual suite and the retained clean normal30 replay.
All three carriers match across all24 authored frames and select captures2–23, spanning6.84 seconds.
Together with the existing public, codec and clean fault passes, this resolves ticket116.
