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

The output preserves the root and suite attributes. Each suite's recorded `time` is also exposed as
`time_seconds`, while `case_duration_sum_seconds` is calculated from testcase values. Those values
are deliberately separate: testcase times can include setup and teardown, and under parallel pytest
runs their sum is not elapsed suite time. Comparisons made across different test selections,
profiles or machine load are observations; they do not establish a controlled speedup.

Malformed XML, unreadable files, missing/malformed/negative/nonfinite testcase durations and
unsupported shapes produce an error on standard error and exit status 2. Passing and failing cases,
errors and skips all remain in the timing lists; the child marker determines the reported outcome.
