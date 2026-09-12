# Add public scenario flows and typed handles

Type: task
Status: resolved
Work state: resolved
Blocked by: none

Add an ergonomic, typed scenario-authoring interface for installed GramLab consumers while
preserving all twenty raw `Scenario` operations and the schema-1 control wire contract. Bind users,
configured bots and private chats to run-owned handles; let conversations own common message,
capture and input operations; let messages own inline-button selection; and let callbacks and bot
process handles own bounded observation waits.

The new interface is additive and remains experimental. It must not expose the World database,
move consumer code into trusted orchestration, retry uncertain writes, add runtime network access,
change simulation/Android fidelity, or imply that Android evidence exists for simulation-only runs.
Handles from one `Scenario` instance must be rejected by another instance before a request is sent.

## Acceptance

- Installed and runner-supplied packages export the typed interface.
- `Scenario.user`, `Scenario.bot` and `Scenario.conversation` replace routine raw-ID threading.
- Conversation history returns immutable typed message handles and owns bounded message waits.
- Inline-button action, callback-answer and bot-state waits retain existing uncertainty semantics;
  only reads are repeated automatically.
- Timeout errors identify the observation and retain the last safe observation without credentials.
- Existing raw SDK callers and exact JSON-shaped results remain unchanged.
- Real loopback control tests, a contained public-runner example, strict typing, Ruff and the
  applicable non-Android gate pass.

## Comments

The user selected recommendation 1 from the 2026-09-12 developer-excellence abstraction report
so other projects can begin consuming GramLab before internal architecture work continues.

Resolved on `task/scenario-flows`. The installed package and private runner SDK now export frozen,
run-bound `User`, `Bot`, `Conversation`, `Message`, inline-action, callback, capture and interaction
handles from `gramlab`. Conversation, callback and bot waits are bounded and repeat reads only;
timeouts retain copied safe observations. The twenty raw `Scenario` operations and their exact
JSON-shaped results remain unchanged.

Red evidence: the initial focused collection failed all nine cases because the public types and
methods did not exist. Green evidence: the flow collection passes all nine cases through the real
loopback control service; the affected client, World-control and runner collection passes; strict
mypy passes the changed package and both example directories; scoped Ruff lint/format and
`git diff --check` pass. The echo hello, two-conversation echo and inline-callback manifests pass
through the real contained CLI with run IDs `0fc666c1-7072-4568-a766-6f7e4aac08ff`,
`5589ddc8-a513-4cb7-a812-3e128102a749` and
`1e4830e2-5fde-4e3a-8efc-d21e3e98be71`; their temporary results are retained under
`/tmp/gramlab-scenario-flows.Jmas5E/` and `/tmp/gramlab-inline.GgIBtW/run/`. The offline build under
`/tmp/gramlab-flow-dist.AxudyS/` contains a wheel and sdist with `scenario_flow.py`, and the wheel
imports both `Scenario` and `Conversation` from the package root.

The full non-Android gate reached 88.70% coverage with 1,587 passing tests and four failures. One is
the documented unchanged default-bridge-v3/custom-emoji-v4 baseline. The other three exposed test
fixtures that appended raw-dictionary assertions to examples migrated to typed handles; the shared
raw fixture was restored, the inline test extension was updated to use typed IDs, and those three
exact cases pass on a focused rerun. Per user direction, the full gate was not repeated. Android was
not rerun because this additive simulation SDK layer does not change native behavior.
