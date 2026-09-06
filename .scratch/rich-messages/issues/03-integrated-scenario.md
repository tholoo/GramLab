# Real bot and native rich-message integration

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: none

Coordinator owns tests/fixtures/rich-scene.json, tests/fixtures/rich_bot.py,
tests/probes/rich_round_trip.py, tests/probes/android_rich_messages.py,
tests/test_rich_round_trip.py, tests/test_android_rich_messages.py, combined checks and shared docs.

## Acceptance

- Run one real isolated bot send/edit scenario in simulation and Android modes, asserting complete
  API replies and durable history. Native codec observations inspect actual serialized content.
- Render bilingual heading, formatted paragraph, table and nested quotation; edit to RTL and
  cold-launch the original chat. Preserve native screenshots, full structured evidence and report.
- Record native install/launch/capture/codec timings to expose avoidable development costs.
- Integrate reviewed worker commits, validate focused contracts and applicable combined gates.

## Progress

The fixture/probes and assertions are prepared. Focused Ruff lint/format and strict typing pass.
The real contained bot first fails because sendRichMessage returns HTTP 404, establishing the
missing behavior before implementation. The first diagnostic obscured this with a JSON EOF;
updated failure reporting identifies the rejected method and HTTP status without credentials.
These are red integration tests; no rich behavior or screenshot success is claimed yet.

## Coordinator integration checkpoint

Reviewed core and native changes pass the integrated real-bot contract. The full core gate passes
269 tests at 82.06% coverage. The new offline APK builds successfully; the focused native test
passes with complete codec catalog, explicit invalid-table rejection and visually inspected
send/edit/cold-restart captures. Shared documentation records the precise supported boundary.
The combined Android gate is still running; keep this ticket open until its required checks pass.

## Accepted integration

The integrated APK passes the full 29-test Android gate with no skipped tests in 1,630.71 seconds.
This includes the rich send/live-edit/restart and complete codec cases, existing plain formatting,
callbacks, composer input and controlled recovery boundaries. Core, static and package checks
recorded above pass. This closes this bounded ticket; broader rich surfaces and the full GramLab
feature inventory remain open. Generic public rich capture acceptance is tracked separately in 04.
