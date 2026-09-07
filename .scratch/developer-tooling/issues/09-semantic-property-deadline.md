# Separate the persistent rich-text property from an incidental timing deadline

Type: bug
Status: ready-for-agent
Work state: resolved
Blocked by: none

The combined core gate after the input/diagnostics/tool merges passes 389 tests but the rich-text
Unicode property reports Hypothesis FlakyFailure. Its `text='0'` example takes 666.56 ms initially
and 93.27 ms on replay, crossing the default 200 ms deadline; no semantic assertion fails. The
property uses a real persistent World and fsync-capable filesystem operations, not a latency
benchmark. Retain this failure evidence rather than inferring a normalization regression or a
specific host-load cause from it.

Worker owns tests/test_rich_messages.py only for the affected property's settings/comment and
this ticket. Read TESTING.md and the diagnostic skill. Use a separate branch/worktree. Verify the
failure against the retained log, preserve every generated input/domain/assertion and explicitly
remove the incidental per-example wall-clock deadline for this semantic IO property. Do not alter
World behavior, example count, Android timeouts, runtime deadlines, concurrency or another test.
Existing bounded runner/test execution limits remain. No new test that merely inspects a decorator.

Run the focused real property and complete tests/test_rich_messages.py under the offline guard,
plus scoped Ruff/format. Record the actual retained timing failure and focused results honestly;
an unchanged semantic rerun passing is not causal proof about filesystem or host load. Coordinator
owns the combined gate, global docs and merge. No guest, APK, source acquisition or full gate is
assigned. Commit the two owned files and return a frozen clean branch with process cleanup state.

## Worker evidence

The retained combined-gate log reports the same `text='0'` example at 666.56 ms initially and
93.27 ms on replay against Hypothesis's default 200 ms deadline; it contains no semantic assertion
failure. The property now explicitly disables that incidental per-example deadline while retaining
its 25 examples, generated input domain and persistence/reopen assertions. The focused property and
all 62 tests in `tests/test_rich_messages.py` pass under the offline network guard. Scoped Ruff
check and format also pass. This rerun does not identify or claim a filesystem or host-load cause.

## Integrated acceptance

The reviewed change keeps all 25 examples, generated input rules and complete assertions. All
62 rich-message World tests pass after integration in 7.22 seconds; scoped lint/format pass.
The combined core rerun passes all 390 tests in 54.01 seconds at 80.99% coverage. The earlier
389-pass deadline failure remains retained. No Android timeout or production behavior changed.
