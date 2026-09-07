# Preserve custom-emoji alternatives in public semantic captures

Type: bug
Status: ready-for-agent
Work state: claimed
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

## Worker handoff

Task `custom-emoji-semantic-captures`, branch `task/custom-emoji-semantic-captures`, assigned base
`9db491958127ac45a02f595830bb91d5ce7f3818`. Only this ticket, `_captures.py` and the new focused
test change. The semantic text traversal now returns a canonical custom emoji's
`alternative_text`; catalog fallback, parsing, API schemas and native rendering remain unchanged.

The standalone contained fixture registers the original static WebP and thumbnail through the
public Scenario SDK, sends an ordinary entity-bearing request to a real local HTTP bot, and has
that bot publish canonical rich content. It covers surrounding paragraph text, an alternative
different from the catalog fallback, an empty alternative inside a nested button-label array and
a second nonempty button-label alternative. Its independent literals compare the complete
canonical history and retained capture. A second public capture request proves the absent catalog
fallback still rejects without adding evidence.

The intended red is retained at `artifacts/ticket67/red-target.xml`: **1 failed in 1.357 seconds**
after the complete message reached World, because custom-emoji traversal terminated the control
connection. Final loopback-only verification is retained at `artifacts/ticket67/focused.xml`:
**8 passed in 9.844 seconds**, covering the new public scenario plus the existing ordinary and
rich-action semantic capture suites. Reproduce with:

```sh
tools/dev default --offline --command unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest tests/test_runner_custom_emoji_captures.py \
  tests/test_runner_capture.py tests/test_runner_rich_action_captures.py -q'
```

Scoped Ruff check, Ruff format check and strict mypy pass for the assigned production and test
files. No guest, build, native test or full gate ran. Semantic captures do not prove custom-emoji
pixels, animation or catalog-fallback rendering; those remain outside this ticket.

## Coordinator integration

Frozen worker tip `68d258bb36412e45725d7bb664a6ddfd312f8dca` is integrated. The actual
public capture regression plus existing capture/rich-action controls pass all eight tests in
9.34 seconds, with scoped Ruff/format and strict typing passing. The original contained red
reached an admitted canonical message and failed in the control traversal. Combined core
verification follows the concurrent public-callback fix; native fidelity remains separate.
