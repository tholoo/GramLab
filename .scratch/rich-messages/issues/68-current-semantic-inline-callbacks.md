# Use current semantic callback support for virtual inline interactions

Type: bug
Status: ready-for-agent
Work state: resolved
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

## Worker evidence

The contained public scenario failed at its first photo-message tap with no callback event while
the virtual client selected the legacy callback contract. Passing `version=4` at that single
internal call makes photo, explicit rich-mention and custom-emoji keyboard taps succeed. The real
contained bot receives and answers each callback; complete frozen World messages, histories and
callback events are checked, and an invalid row leaves events unchanged.

The focused contained test passes under the checkout's offline pinned shell. Ruff formatting and
lint plus strict mypy pass for both owned source files. Red and green JUnit/log evidence is retained
under `artifacts/current-semantic-inline-callbacks/`. An initial attempt inherited an obsolete
runtime profile without Pillow; the retained semantic red and all accepted evidence use the
checkout-selected profile.

## Coordinator integration

Frozen tip `1e5f541e5228ed4977c6dbb5d6458549c46dfe28` is integrated. The actual public
photo/mention/custom-emoji callback regression and ordinary rich keyboard control pass two tests
in 3.23 seconds, with three Android cases explicitly deselected. Scoped Ruff/format and strict
typing pass. Combined core verification follows; this changes the internal virtual callback
projection only and does not establish any new native input behavior.

## Answer

Combined integration passes all 647 non-Android tests at 82.90% coverage in 86.79 seconds.
The contained public regression and required scoped checks pass; this ticket is resolved.
Original native rendering and input acceptance remain separate.
