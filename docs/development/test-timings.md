# Retained pytest timing comparison

`tools/test-timings` reads an existing pytest JUnit XML report and writes JSON to standard output.
It never invokes pytest or changes either input. Compare a current report with an earlier one using:

```sh
tools/test-timings artifacts/current.xml --baseline artifacts/earlier.xml --limit 10
```

The command reports each case's `classname::name` identity, outcome, duration and original testcase
attributes. `current.slowest` is ordered by individual case duration. A comparison reports matched
duration deltas as `current - baseline`, plus separate added and removed lists. `--limit` must be a
positive integer and bounds each emitted case list; the associated counts always describe the full
input.

The supported input is pytest's JUnit XML in the default xUnit2 shape: either one `testsuite` root,
or a `testsuites` root containing direct `testsuite` children, with direct `testcase` children.
Every testcase must have nonempty `classname` and `name` attributes and a finite, nonnegative
`time`. A suite `time` is optional, but is subject to the same numeric validation when present.
Duplicate `classname::name` identities, nested suite wrappers, XML namespaces, DTDs, entity
declarations, unknown structural children and multiple outcome markers on one case are rejected.
Pytest's `properties`, `system-out` and `system-err` metadata children are accepted without being
interpreted.

To plan the unexecuted portion of a stopped gate, provide the exact original collection as a JSON
array in pytest order:

```json
[
  "tests/test_android_example.py::test_first",
  "tests/test_android_example.py::TestGroup::test_case[value::one]",
  "tests/test_android_example.py::test_last"
]
```

```sh
tools/test-timings artifacts/stopped.xml \
  --collected-nodeids artifacts/collected-nodeids.json
```

The optional `selection` output preserves that complete collection and reports retained passing
node IDs plus the ordered remaining node IDs. Failed, errored, skipped and absent cases remain;
only observed passes are retained. Selection lists and counts are complete and are not reduced by
`--limit`. Supported node IDs are ordinary Python module functions and test-class methods, with
parameter text preserved literally, including dots, brackets and `::` inside the parameter suffix.
Empty or duplicate collections, unsupported node shapes, normalization collisions and JUnit cases
absent from the collection fail explicitly.

The output preserves the root and suite attributes. Each suite's recorded `time` is also exposed as
`time_seconds`, while `case_duration_sum_seconds` is calculated from testcase values. Those values
are deliberately separate: testcase times can include setup and teardown, and under parallel pytest
runs their sum is not elapsed suite time. Comparisons made across different test selections,
profiles or machine load are observations; they do not establish a controlled speedup.

Before retaining any pass, independently verify that source, fixtures, collection, runtime profile
and, for Android, the APK are unchanged. This command reads one partial report; it cannot establish
cross-run equivalence, prove that an earlier unrecorded failure did not occur, supply results from a
later report or mark the combined gate complete.

Malformed XML, unreadable files, missing/malformed/negative/nonfinite testcase durations and
unsupported shapes produce an error on standard error and exit status 2. Passing and failing cases,
errors and skips all remain in the timing lists; the child marker determines the reported outcome.
