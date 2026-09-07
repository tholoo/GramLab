# Preserve custom-emoji alternatives in public semantic captures

Type: bug
Status: ready-for-agent
Work state: open
Blocked by: none for contained simulation; native capture remains separate

Own this ticket, `src/gramlab/_captures.py` and new
`tests/test_runner_custom_emoji_captures.py`. No other production, native, existing test, fixture,
lockfile or shared-doc changes. Use the approved custom-emoji implementation contract.

Coordinator inspection found `_rich_text` recursively reads `value["text"]` for every non-button
rich leaf, but canonical custom emoji have `alternative_text`. A public capture of an otherwise
admitted rich message containing a custom emoji can therefore raise KeyError. Reproduce through
the actual contained public runner/Scenario capture boundary before correcting the narrow traversal.
Do not infer catalog fallback equality or add a second parser/renderer.

A capture's semantic text must retain canonical custom-emoji alternative text, including different
and empty alternatives, within supported rich text and nested button-label arrays. Ordinary message
entities retain their covered text. Preserve surrounding text order and the full canonical captured
history; emoji-free existing behavior must remain intact. A requested absent substring must still
fail explicitly. Semantic captures do not establish native pixels or animation.

Use original registered static fixture bytes, a tiny real contained scenario/bot if the runner
requires one, and independent expected full capture/history values. Prefer a small typed standalone
fixture over importing untyped legacy runner test helpers. Validate both successful custom-emoji
capture and a realistic absent-text rejection. Keep input provenance exact and scenario/fixture
paths portable; no consumer application references or machine data in Git.

Follow AGENTS, TESTING, offline safety and parallel workflow. Record actual red then focused green
JUnit/logs under unique ignored paths. Run focused contained tests, scoped Ruff/format/strict typing
only. No guest, build or full core gate. Return a frozen clean commit with all processes terminal.
