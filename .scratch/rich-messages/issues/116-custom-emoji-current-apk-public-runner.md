# Verify custom emoji through bridge v5 and the current APK

Type: task
Status: ready-for-agent
Work state: claimed
Owner: custom-emoji-runner-v5
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
