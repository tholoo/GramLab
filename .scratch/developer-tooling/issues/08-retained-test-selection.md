# Plan the remaining tests from a retained partial gate

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: none

The rich-button Android gate stopped after 19 passing cases because an older catalog expectation
was stale. The coordinator independently collected all 41 node IDs and selected the failed plus
21 unexecuted cases on the same APK. Automate the bookkeeping that avoided repeating the first
19 cases. This is a read-only test plan, never permission to reuse results from changed inputs.

Worker owns tools/test-timings, tests/test_test_timings.py, docs/development/test-timings.md and
this ticket in a separate branch/worktree. Extend the existing validated JUnit parser rather than
introducing another parser or executing pytest. Preserve the existing CLI and timing output.
Add optional `--collected-nodeids PATH`, reading a JSON array of pytest node-ID strings. With that
option, append a `selection` object containing the original ordered collection, retained passing
node IDs and ordered remaining node IDs. Failed, errored, skipped and absent cases all remain.
Counts must cover the complete lists, independent of the existing display limit. Empty or duplicate
collections, malformed entries, ambiguous normalized identities and JUnit cases absent from the
collection must reject explicitly with status 2. A report containing zero cases retains no passes.

Support ordinary pytest Python module functions, test classes and parameterized names, including
parameter text containing dots, brackets or `::`. Map only the module/class portion to JUnit's
classname; preserve parameter text literally. Do not guess through unrecognized node-ID shapes
or sanitized identity mismatches. Detect collisions before using a pass to omit any test. Existing
JUnit shape, duplicate, DTD and outcome validation remains mandatory.

Use independent CLI behavioral tests for a partial gate, failures/errors/skips, missing cases,
class/parameter identities, input order, invalid/ambiguous identities, zero observations, malformed
JSON and unchanged old invocation behavior. Exercise actual subprocess exit/JSON boundaries,
without launching Android. Document a small explicit JSON example and emphasize that the caller
must verify unchanged source, fixtures, profile and APK before retaining passes; this command does
not establish cross-run equivalence or mark a gate complete. A partial report cannot prove absence
of earlier failures or supply results from a second report.

Run focused developer-tool tests, Ruff/format and the existing strict typing scope in the pinned
offline shell. Preserve worker-local environments and caches. Coordinator owns shared CI/static
lists, global handoff, acceptance against the real retained gate and integration. No guest, build,
network, profile, timeout or automatic retry changes are assigned. Commit only owned files and
return a frozen clean branch with exact evidence and remaining limits.

## Worker evidence

`--collected-nodeids` now validates a nonempty JSON array and maps supported pytest module/function
and single test-class node IDs to the already validated JUnit identities. Parameter text,
including dots, brackets and `::`, is retained literally. Duplicate collections, unsupported node
shapes, normalized identity collisions and report cases absent from the collection reject before a
selection is emitted. The selection preserves the original order, retains only observed passing
cases and leaves failures, errors, skips and absent cases in the complete remaining list. Its counts
and lists are independent of the display limit. Without the option, the existing output shape and
timing behavior remain unchanged.

All 27 focused real CLI tests pass. They include class and parameter identities, a partial report,
all nonpassing outcomes, absent and zero observed cases, input ordering, duplicate/empty/malformed
collections, ambiguous normalized identities, sanitized mismatches and the existing XML/DTD
rejections. Scoped Ruff lint/format and strict mypy for the command pass. No guest, build, full gate,
pytest execution inside the tool, network access or profile change was used. Coordinator acceptance
against the retained 41-node collection and 19-pass/22-remaining partition is still pending.

## Coordinator acceptance

The reviewed tool is merged and its 27 real CLI checks plus scoped Ruff/format/mypy pass in the
integration checkout. The actual retained Android collection and partial JUnit reproduce exactly
41 collected, 19 retained passing and 22 ordered remaining node IDs, identical to the independently
constructed coordinator selection. The stopped gate's failure remains explicit; the command does
not infer input compatibility or combine later results. No guest or automatic retry is performed.
