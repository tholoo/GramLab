# Reconcile the current-inline runner scenario with the default bridge version

Type: bug
Status: needs-triage
Work state: unclaimed; reproduced on the pre-architecture baseline
Blocked by: maintainer choice between an explicit test version and a product default change

`test_contained_scenario_taps_current_semantic_inline_keyboards` invokes the public CLI without
`--bridge-version`, so the run uses the preserved default bridge v3. Its third interaction targets
a custom-emoji message, whose callback correctly requires bridge v4. The scenario is rejected after
the photo and mention callbacks succeed.

The complete non-Android architecture gate reproduced this single failure after 1,581 passing tests
at 88.61% coverage. An isolated checkout of pre-branch commit `f1a5200` reproduces the same failure,
and neither this test nor the CLI default changed on the architecture branch. Decide separately
whether the test should request v4 explicitly or whether changing the product default is intended;
the latter is consequential bridge policy and was outside the behavior-preserving refactor scope.
