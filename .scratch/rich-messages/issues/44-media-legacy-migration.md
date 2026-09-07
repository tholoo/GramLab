# Preserve legacy callback history during media migration

Type: bug
Status: ready-for-agent
Work state: resolved
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

## Worker evidence

Historical schema-3 source at `c6842005` always emitted `callback.created` when inserting a
callback and `callback.answered` when storing its answer. The schema-3/schema-4 fixtures contained
an answered callback and its queued update but omitted both required journal events. Restoring the
events lets schema 6 derive the honest captured message revision (sequence 5) without a fabricated
fallback and preserves the transactional concurrent migration.

The three full-gate regressions and all owned media World tests pass together (12 tests). The full
affected client-send, update-delivery and media-World files pass (33 tests), including exact legacy
revision assertions and `ResourceWarning` promotion after closing every test-owned World. Scoped
Ruff formatting/lint and World source mypy pass. No native, guest or full core gate was run.

Coordinator integration: all 471 non-Android tests pass in 94.50 seconds at 81.71% coverage.
Repository-wide Ruff/format and integrated source/media typing pass. No production migration
fallback was added; historical callback event provenance was independently checked.
