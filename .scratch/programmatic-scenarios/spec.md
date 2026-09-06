# Programmable isolated scenarios

Status: ready-for-agent
Work state: claimed

Build the Python scenario workflow on the approved per-run local HTTP capability and SQLite
world model. Keep scenario code in a private runtime component. Trusted GramLab orchestration
owns world services, bot/emulator lifecycle and artifact collection. This preserves the existing
supervisor/component distinction rather than promoting consumer Python to supervisor code.

## Acceptance

- A documented command runs an original Python scenario and real local bot in containment.
- Scenario code controls its world through an authenticated, versioned semantic interface;
  it cannot open the world database or another component's files/processes.
- Scenario, bot and client credentials have distinct purposes; another run's capability fails.
- Virtual actions, bot replies and Android observations use the existing authoritative world.
- Multiple virtual participants and independent simultaneous runs have isolated state.
- Normal exit, scenario assertion failure, bot failure and timeout preserve useful redacted
  evidence and clean up all descendant processes.
- Selected source/dependency inputs are explicit and provisioned before execution; runtime
  never installs packages or falls back to an external endpoint.
- Provide an executable consumer example, precise supported modes and honest limitations.

The first implementation step is the world control interface already anticipated by the
[approved proposal](../../docs/development/android-foundation-proposal.md). Bot lifecycle,
packaging, runner and report integration follow through the same workflow; a control endpoint
alone does not satisfy this specification. Do not freeze the experimental SDK as a stable API.

## Tickets

- [01: World control from a private scenario process](issues/01-world-control.md)
- [02: Consumer runner and artifacts](issues/02-consumer-runner.md)
- [03: Native composer acknowledgment references](issues/03-composer-references.md)
- [04: Native composer sends and durable recovery](issues/04-native-composer.md)
- [05: Android Unicode input tooling references](issues/05-input-tooling-references.md)
