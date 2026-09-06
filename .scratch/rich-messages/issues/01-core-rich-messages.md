# Structured rich-message API and durable world

Type: task
Status: ready-for-agent
Work state: claimed
Owner: rich-core (task/rich-core)

Implementing the acceptance and owned files below; coordinator retains integrated acceptance.
Blocked by: none

Read ../spec.md. Own src/gramlab/rich_messages.py (new), src/gramlab/world.py,
src/gramlab/bot_api.py, dedicated tests/test_rich_messages.py and tests/test_rich_bot_api.py,
and docs/development/rich-messages.md (new). Own this ticket only among shared task records.
Coordinator owns all Android changes, client bridge/scenario integration and shared docs.

## Acceptance

- Verify exact input/output types against official Bot API 10.3 and pinned official server sources.
- Implement independently validated rich block input and send/edit through real HTTP requests.
- Preserve complete nested EN/FA text, RTL flag, table fields, details and formatting wrappers.
- Atomic invalid/unsupported rejection, ownership checks, persistence/reopen and edit events retain
  complete content. Text-only regression behavior remains intact. Rich API output is not flattened.
- Send the precise JSON contract and wrapper support to coordinator early for adapter coordination.
- Run focused meaningful core tests within the documented network guard. Record tests and gaps,
  then commit only owned files. Leave ticket claimed for coordinator's integrated acceptance.


## Worker handoff

Work state remains claimed until coordinator integration. Core implementation and dedicated
contract evidence are ready for coordinator review.

- Added independent validation of all ten assigned block types and nine formatting wrappers.
  Explicit `skip_entity_detection: true` is required; HTML/Markdown, automatic entities and the
  remaining block/wrapper inventory fail before mutation. See
  [the precise public contract](../../../docs/development/rich-messages.md).
- Durable send/edit, canonical defaults, complete HTTP output, plain/rich transitions, callback
  payloads, ownership, snapshot/difference propagation and reopening are covered. The shared
  output contains complete `rich_message`, with no flattened Bot API text fallback.
- Initial real-HTTP red run: 14 failures establish the absent API contract. The first green run
  passed the same 14 tests. Expanded dedicated rich suite passed 41 tests in 13.47 seconds; the
  subsequent 27-test world run adds canonical-output budget rejection. The 15 HTTP tests remain
  applicable. A preceding focused regression run passed 67 rich and ordinary world/API/entity
  tests in 28.69 seconds. One intermediate test used incorrect `events`/`message` result keys;
  corrected to the existing public `changes`/`data` contract, with no production fix for that typo.
- Tests ran inside the documented loopback-only outer namespace. Ruff and formatting pass on all
  five changed Python files; strict mypy passes all 19 core modules. No APK build or Android runtime
  was run by this worker. Coordinator owns combined gates and original renderer evidence.
- Coordinator-approved explicit local table profile: span at most 100, summed colspan×rowspan
  at most 10,000, no later row wider than the first by normalized column spans. Core/adapter
  workers agreed the same validation. This does not establish complete table layout conformance.
- Avoided repeated full Android/core gates; focused boundary tests finish in seconds. Worker
  environment and artifacts are isolated; no persistent process remains after checks.
