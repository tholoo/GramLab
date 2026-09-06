# Structured rich-message API and durable world

Type: task
Status: ready-for-agent
Work state: open
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
