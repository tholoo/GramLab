# Use current semantic callback support for virtual inline interactions

Type: bug
Status: ready-for-agent
Work state: open
Blocked by: none for simulation; native regression remains separate

Own this ticket, `src/gramlab/_interactions.py`, and new
`tests/test_runner_current_inline_callbacks.py`. Do not edit World, bridge schemas, Android,
existing tests, other workers' files or shared documentation.

Coordinator inspection found virtual `Interactions.tap_inline_button` calls World.create_callback
without a version, selecting its legacy v1 compatibility guard. Current photo, explicit mention
and custom-emoji messages require v3/v4 and may therefore reject an ordinary inline button in
simulation even though the shared current World supports that message. Reproduce through the
actual public contained runner/Scenario operation before fixing it.

The internal virtual client should request the current semantic callback projection (v4). It is
not an older network client. Keep World legacy admission guards, native transport selection,
callback deduplication, inline target validation and normal keyboard behavior unchanged. Do not
add public rich-button targeting or new APIs under this ticket.

Use a compact actual local bot/scenario to send admitted messages containing a photo, an explicit
rich mention and custom emoji with ordinary reply_markup keyboards. The scenario taps the exact
row/column. Verify full callback message snapshots and payloads, exactly one callback/update per
tap, expected bot handling and retained media/identity/emoji content. Use existing original
fixture bytes and synthetic profiles; no consumer code or external traffic. Include an invalid
row/column rejection that produces no callback or event. Canonical full histories and frozen
callback content are the oracle; successful subprocess exit alone is insufficient.

Use small typed standalone fixtures rather than importing untyped legacy runner tests. Follow
AGENTS, TESTING, offline safety and parallel workflow. Retain real red/green JUnit/logs, run focused
contained checks plus scoped Ruff/format/strict typing only, and return a frozen clean branch.
No guest, build, full core gate, lockfile or shared interface changes. All processes terminal at
handoff; coordinator owns merge and combined verification.
