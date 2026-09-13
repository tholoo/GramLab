# Per-bot runtime profiles

Type: implementation
Status: ready-for-agent
Work state: resolved
Blocked by: none

Implement the contract in [the effort specification](../spec.md) through the public runner and CLI.

## Owned scope

- `src/gramlab/runner.py`
- `src/gramlab/__main__.py`
- `src/gramlab/_run.py`
- `src/gramlab/_processes.py`
- focused runner/runtime tests
- consumer-runner, environment, compatibility, changelog and handoff documentation affected by
  the new provisioning interface

## Acceptance

Use the complete acceptance list in `../spec.md`. Preserve manifest schema 1 and all current
single-profile behavior. Test through real contained processes; do not replace runtime execution
with a mock.

## Comments

- 2026-09-13: Claimed for an independent consumer integration. Red evidence must precede the
  implementation.

## Answer

Implemented trusted per-bot runtime-profile overrides without changing manifest schema 1. The CLI
accepts repeatable `--bot-profile ALIAS=PROFILE` bindings, and Python callers pass a mapping to
`runner.run`. The outer supervisor mounts the dependency union required for nested setup; each bot
component launches with only its selected profile and Python executable. Results record profile
fingerprints, while local profile documents stay private run artifacts.

Red evidence: the focused real-runner case failed because the CLI did not recognize
`--bot-profile`. After the initial implementation, the duplicate-binding case exposed profile-file
loading before duplicate validation; it failed with `FileNotFoundError` instead of the required
preflight rejection. The full non-Android gate then exposed five existing CLI adapter cases because
an empty profile mapping changed the default `runner.run` call shape. The default CLI path now omits
that optional argument entirely. A final report-level assertion then showed that the fingerprint was
present only in `result.json`; the HTML report now exposes a dedicated Bot runtime profiles section.
The focused collection also exercises two profile-isolated bots through the public Python runner.

Focused verification passes all four runtime-profile cases, all five default/explicit bridge CLI
compatibility cases, scoped Ruff format/lint and strict typing for the changed source files. The
initial full run had six failures: five exposed a default CLI call-shape regression and one existing
current-inline fixture used the default bridge v3 for an interaction requiring v4. The CLI now
omits empty optional profile mappings, and the custom-emoji fixture explicitly selects bridge v4.
The final serialized non-Android gate passes all 1,608 tests at 88.96% coverage. Android is
unaffected by component-profile selection itself.

The implementation was reconciled with the generic consumer-compatibility capability set. The
combined tree refreshed its checkout-local editable install and passed all four runtime-profile
cases, scoped Ruff lint and strict typing for the changed source files. No task process or shared
Android resource remains active.
