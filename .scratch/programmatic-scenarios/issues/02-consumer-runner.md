# Run consumer scenarios with lifecycle and evidence

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: none (01 resolved)

Package selected scenario/bot inputs into fresh private run directories, expose the Python SDK
inside a restricted scenario process and run real bots through private components. Use the
existing trusted provisioning profile and explicit timeouts; never execute consumer Python in
the supervisor or on the host as part of discovery.

## Acceptance

- Working documented entry point and framework-independent consumer example.
- Explicit source/dependency inputs and separate scenario, bot and world writable state.
- Bounded lifecycle, concurrent independent runs, failure/timeout cleanup and redacted reports.
- Equivalent semantic scenarios in simulation-only and Android modes with actual renderer
  evidence; unsupported modes fail explicitly until connected.
- No ambient project credentials, proxy settings, host paths or generated artifacts in the repo.

## Progress

2026-09-06: The [consumer runner](../../../docs/development/consumer-runner.md) now executes a
TOML manifest through `gramlab run` or `python -m gramlab run`. Selected files are read as data
before private runtime setup; consumer Python stays outside trusted orchestration. Manifest bot
identities are available through `Scenario.bots()`. A framework-independent two-conversation
example runs through the installed console command and produces local HTML/JSON evidence.

Actual CLI tests cover complete private scenario/bot results, concurrent isolated runs, nested
entries/data, source/output rejection, ambient environment clearing, named bot capability scope,
scenario/bot failure, detached-descendant timeout cleanup, log bounds, runtime unavailability and
large semantic evidence. Input labels that become ambiguous after redaction fail before execution.
The report is inspected at desktop/mobile widths with no external resources. Dependencies remain
explicit selected files or the trusted provisioned closure; there is no runtime package installer.

This ticket remains claimed. Connect the actual Android renderer to this command and demonstrate
equivalent semantic scenarios plus original screenshots. Both Android modes currently fail
explicitly; existing dedicated Android test evidence does not establish consumer-runner support.
Consumer-requested lifecycle/fault operations and expanded dependency packaging remain follow-ups.

The final core gate passes 132 tests at 87.74% measured coverage. Static checks, Nix/workflow
validation, offline distributions and public-tree privacy/local links pass. Contained supervisor
source is uninstrumented by coverage; its behavior is checked through actual CLI execution.
