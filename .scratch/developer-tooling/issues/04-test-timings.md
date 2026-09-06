# Compare retained test timings

Type: task
Status: ready-for-agent
Work state: open
Blocked by: none

## Ownership

Worker owns tools/test-timings (new), docs/development/test-timings.md (new), this ticket and
tests/test_test_timings.py (new, only if meaningful focused behavioral coverage is needed).
Coordinator owns shared documentation, integration and combined checks. No runtime, Nix, APK or
production-code changes are assigned.

## Contract

Provide a small standard-library command that reads a saved pytest JUnit XML report, optionally
compares it with an earlier report, and emits structured JSON with the slowest individual cases.
Include per-case identity, outcome and duration; distinguish added/removed cases from matched
duration changes. A positive configurable limit bounds the displayed case lists. Reject malformed,
missing, negative/nonfinite durations and duplicate case identities explicitly rather than
silently merging them. Include failures/skips honestly. Never start pytest or modify the inputs.

JUnit per-case time can include setup/teardown. Report suite-provided timing separately from the
sum of case durations; under parallel execution those values are not interchangeable. Comparisons
with changed workload/profile/load are observations, not controlled benchmark or speedup claims.
Preserve recorded suite attributes without inventing missing wall-clock data or success counts.
Handle both testsuite and testsuites roots, without double-counting wrappers. Document exactly
which producer/schema is supported and reject ambiguous unsupported shapes.

Use real retained pytest JUnit reports for acceptance, plus bounded synthetic malformed input
when needed for rejection checks. Verify matching/added/removed cases and positive/negative
deltas against an independently specified small example. Keep all actual report paths and local
machine information in ignored artifacts/notes. Check syntax/lint/format/type behavior appropriate
to the chosen implementation; do not run the core suite, an Android guest or a build. No new
dependency is needed. Return a frozen committed branch and exact commands/evidence to the
coordinator, who owns review, merges and documentation links.
