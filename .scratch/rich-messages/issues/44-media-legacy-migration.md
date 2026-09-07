# Preserve legacy callback history during media migration

Type: bug
Status: ready-for-agent
Work state: open
Blocked by: none

Own `src/gramlab/world.py`, migration tests in `tests/test_client_sends.py`,
`tests/test_update_delivery.py`, `tests/test_media_world.py`, historical SQL fixtures only if
historical source proves a fixture defect, and this ticket. Shared docs remain coordinator-owned.

The integrated full core gate has three failures opening schema-3/4 fixtures: the schema-6
callback revision migration inserts NULL when no callback-created journal event exists.
Investigate the historical callback implementation and fixture provenance before choosing the
fix. Preserve old capabilities, answers, subscription filters, message history and concurrent
open behavior; do not fabricate historical revisions or weaken valid historical expectations.
Existing full structured regression tests are the initial red evidence. Verify captured revisions
remain correct for callbacks followed by edits, including repeated equal message bodies.

Follow TESTING.md and the parallel workflow. Reproduce focused failures before changing behavior,
run affected migration/media tests in the pinned offline guarded environment, and run scoped
Ruff/mypy. Repair unclosed World connections in owned media tests if confirmed by warnings.
Coordinator owns the combined core gate, native builds/guests and integration. Commit only owned
changes, return frozen clean tip, exact evidence and terminal process/resource status.
