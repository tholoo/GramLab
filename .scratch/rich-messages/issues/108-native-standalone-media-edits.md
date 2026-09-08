# Prove standalone media edits in the original Android document workflow

Type: task
Status: ready-for-agent
Work state: claimed
Owner: task/native-media-edit-acceptance
Blocked by: host work may proceed independently; native execution requires verified104 delivery

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
