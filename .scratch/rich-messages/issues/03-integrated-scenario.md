# Real bot and native rich-message integration

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: 01 and 02 for passing integration

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
