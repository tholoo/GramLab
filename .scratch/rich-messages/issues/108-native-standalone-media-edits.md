# Prove standalone media edits in the original Android document workflow

Type: task
Status: resolved
Work state: integrated and accepted on reviewed normal30 APK
Owner: coordinator
Blocked by: none

Extend the existing105 real-bot document scenario with the merged106 media operations. This is
acceptance work for required operational behavior, not a new parallel harness or a production
adapter rewrite. Keep original forced-document send/reuse/download and rejection controls.

## Ownership and interfaces

Own this ticket and only `tests/fixtures/document_bot.py`, `tests/probes/document_round_trip.py`,
`tests/test_document_round_trip.py`, `tests/probes/android_document_ui.py`, and
`tests/test_android_document_ui.py`. Reuse existing licensed photo fixtures and the original
photo observer contract without modifying shared fixtures. Request ownership for any additional
file before editing. Coordinator owns production, patches, shared docs/CI, merges and native runs.
Use the assigned branch/worktree/environment and follow the parallel workflow and TESTING.md.

Use the frozen106 real HTTP methods and current v5 dependencies. No schema, runner, classification,
parse-mode, grouped/inline/business edit or native patch changes. A source path being present does
not prove Android acceptance; report an actual native failure before proposing a production fix.

## Required combined sequence

Keep the bilingual initial forced D1 document on message2, its original exact download, static
custom-emoji caption and inline keyboard K1. Each subsequent transition is driven by an actual
callback consumed by the contained bot, with an answer and exact Bot API effect:

1. K1 sends the unchanged D1 reuse as message3, then editMessageCaption replaces message2's caption
   and keyboard with K2 while preserving D1.
2. K2 uses multipart editMessageMedia to replace message2 D1 with a new P1 photo and K3.
3. K3 uses editMessageCaption to replace the P1 caption and keyboard with K4, preserving P1.
4. K4 uses multipart editMessageMedia to replace P1 with a distinct ordinary D2 document and K5.
   New standalone document uploads keep the explicit forced-file flag.

Keep creation IDs/dates stable through edits. Capture every relevant original row/caption/keyboard
transition, tap the current named document for D2, and cold-restart the same app data. Final state
must contain message2 D2/K5 and unchanged message3 D1. Keep captures bounded and meaningful, with
an independently specified stage inventory; do not make an arbitrary image count the oracle.

## Semantic and native acceptance

Specify complete expected HTTP responses, four delivered callback updates/answers, current history,
ordered message.edited events/revisions, v5 changes/snapshot, pending updates and reopened state.
Callback dependencies must retain each actual historical message and media (K1/K2 D1; K3/K4 P1).
Verify getFile and exact bytes for D1/P1/D2, retained recipient grants after replacement/reopen,
and unchanged reused D1. Assert full expected values independently rather than copying actual output
into expected objects. Preserve earlier malformed/cross-kind/foreign-bot rejection coverage.

Native orchestration must place proxy phases immediately before each relevant action. Require
original P1 bitmap binding through the existing observer and successful asset delivery, not merely
a caption or plausible screenshot. Preserve original ordinary-photo cleanup when P1 is replaced;
retained World grants do not imply indefinite retention of the selected native image destination.
Use existing tickets49/56 and photo acceptance as the cleanup oracle. Require D1's initial tapped
GET and no redundant edit/restart GET, P1 transfer and unchanged-caption cache reuse, no premature
D2 GET before its filename tap, one successful D2 transfer and no cold-restart transfer. Verify exact
destination bytes, absence of partial publication, phase-local traces and complete semantic state.

Keep full ordered current-APK/source provenance, containment and zero-account checks, bounded
failure PNG/XML/trace/logcat/ledger retention and original images in the report. This direct harness
does not replace later public-runner acceptance. Default classification, albums and broader rich
button placements remain required separate work.

## Verification and handoff

Retain a real pre-extension host failure showing the missing edit sequence before changing the
bot/orchestration; do not manufacture a production-defect claim. Exercise the real contained bot
and HTTP/World boundary with complete expectations. For host native-orchestration controls use only
established external boundaries, and explicitly report that these do not prove rendering.
Run focused scenario/evidence tests, affected old document/photo scenario controls, scoped strict
mypy and Ruff in the pinned offline environment with fatal ResourceWarning. No guest, APK build,
full suite, new upstream export or dependency changes. Coordinator runs actual native acceptance
on the reviewed delivery APK after104 passes and will assign any evidenced adapter defect separately.
Freeze a clean commit and report exact red/green scope, provenance, terminal processes, shared-doc
impact and remaining native acceptance; do not resolve this ticket from host-only results.

## Comments

- Retrospective pre-extension host red retained at `/tmp/gramlab-108-red/host-red.xml` against
  base `69fb7348bc20da4a1564c8b0e39534ff55e3ddfd`: the independently added four-operation scene
  inventory failed with `KeyError: 'edit_sequence'`. This is missing acceptance coverage, not a
  production defect claim.
- The contained real-bot/HTTP/World scenario and focused host controls pass after extension. Native
  rendering remains unexecuted and this ticket remains claimed pending coordinator review and the
  actual reviewed-APK run after ticket104 succeeds.
- The reviewed legacy delta was transplanted without its old ancestry as clean-history commit
  `0709c7c` on base `545828bef33312043f3959a17e51715b10622761`. Review found and the clean
  worker corrected three host/native-acceptance gaps: callback taps now use the keyboard rendered
  by the preceding transition (K1 through K4, with K5 render-only); the existing schema-2 original
  photo observer binds P1 asset3 to message2 in the current process before and after its caption
  edit; and D1/P1/D2 saved presentation copies require exact bytes with source-correct trace keys
  (`-1_-1.pdf`, `3_1.jpg`, `-1_-2.pdf`) and tap-relative request timing. The ordinary-document
  temporary is created beside its selected presentation destination and atomically renamed, so the
  native key is not a promised second coexisting file. No production, schema, shared fixture or
  native patch changed.
- Corrective red: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider
  tests/test_android_document_ui.py::test_document_callback_taps_follow_the_current_keyboard`
  failed one case because the flawed orchestration exposed no independently specified callback-tap
  schedule. The same command passes after the schedule is explicit and consumed by both scenario
  and Android orchestration.
- Final focused host command: `tools/dev default --command unshare --user --map-root-user --net
  bash -eu -c 'ip link set lo up; PYTHONDONTWRITEBYTECODE=1
  PYTHONWARNINGS=error::ResourceWarning .venv/bin/pytest -p no:cacheprovider
  tests/test_document_round_trip.py tests/test_android_document_ui.py
  tests/test_media_round_trip.py -m "not android"'`: 6 passed and one Android case deselected in
  6.97 seconds; the final unchanged-scope rerun passed the same counts in 7.86 seconds. A preceding
  run outside the checkout-local Nix shell produced two environment
  failures because its inherited component Python lacked Pillow; four host cases passed and one
  Android case was deselected. The identical pinned-shell rerun above is the valid evidence.
- Scoped strict mypy over the five owned Python files passes. Ruff lint and format-check over the
  same files pass, as does `git diff --check`. The checkout-local editable import resolves here.
  No guest, APK build, full suite or networked runtime was run. No task process remains. Actual
  original-renderer acceptance, primary-image inspection and ticket resolution remain blocked on
  verified104 delivery and belong to the coordinator under `android-gate`.
- Coordinator integration after delivery104: the same six non-Android scenarios pass in the
  combined public-v5 tree under the pinned offline shell and loopback-only namespace; the one
  Android case is deselected as intended. JUnit is retained as
  `artifacts/native-media-edit-acceptance-integrated-host-01.xml`. Scoped strict mypy, Ruff and
  `git diff --check` pass. This checkpoint integrates the clean-history migration but does not
  claim original rendering, taps, download/cache/restart behavior or ticket resolution; those
  require the next serialized Android run.
- Coordinator native10 passes the complete original-renderer workflow in118.862 seconds on the
  unchanged normal30 APK
  `a964bbaccaaf59719d966a72ecd85de4288d146887e3f7ff7d50be7281df726b`. Eight original captures
  show the D1→P1→D2 captions/keyboards, unchanged reused D1 and cold-restarted final conversation.
  The finalized ledger contains178 successful loopback requests and zero errors, with exactly one
  D1 GET in `initial`, one P1 GET in `photo`, one D2 GET in `document_final`, and no document GET in
  caption-edit or restart phases. Both schema-2 P1 observations bind asset3 to message2 in PID2489;
  presentation files and SHA-256 values match D1/P1/D2 bytes, P1 is cleaned after replacement,
  partials are absent, accounts are zero, and containment/provenance assertions pass. Evidence and
  the self-contained report remain under `artifacts/native-media-edit-android-10/`.
- Native failures01/03–09 were acceptance-harness defects, not production adapter defects: raw XML
  entity matching missed the custom emoji; stock document auto-download raced the tap oracle; the
  row center opened Telegram's context menu instead of its radial control; globally disabling media
  also suppressed P1; client polling crossed bridge shutdown; and migrated cache-name/coexistence
  expectations contradicted the pinned codec/publication path. Focused host regressions cover each
  corrected seam. No production patch or APK byte changed.
