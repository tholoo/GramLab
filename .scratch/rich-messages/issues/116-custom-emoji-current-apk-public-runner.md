# Verify custom emoji through bridge v5 and the current APK

Type: task
Status: ready-for-agent
Work state: open
Owner: unassigned
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
