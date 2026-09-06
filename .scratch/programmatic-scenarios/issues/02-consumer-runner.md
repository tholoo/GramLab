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

The [capture milestone](../../../docs/development/scenario-captures.md) now connects headless
Android to the same CLI and Python API. The two-conversation example has equivalent semantic
results in both modes and original PNG/XML evidence from the actual renderer. Scenario failure
retains its capture; Android startup timeout yields a failed report. All 138 core tests pass at
84.30% measured coverage and all 16 Android tests pass. Static checks, Nix/workflow validation and
offline distributions pass. Selected API tests explicitly trace real contained supervisor lines.

This ticket remains claimed for composer input, interactive mode and the remaining
workflow acceptance. Consumer-requested lifecycle/fault operations and expanded dependency
packaging remain follow-ups. Interactive mode still fails explicitly during preparation.

The [inline-input follow-up](../../../docs/development/scenario-input.md) now exposes message/row/
column selection through the consumer SDK. Simulation creates callbacks in the shared world;
Android uses accessible message/button bounds and actual input. Both modes drive the same real
bot edit, including correct selection between repeated button labels. Renderer serialization is
shared with captures and reports retain interaction evidence. Lost responses remain uncertain,
with a real response-loss test proving one callback and no automatic retry. Four simultaneous
actors produce 64 distinct callbacks and share the per-run input limit. Composer input, scrolling,
interactive mode and the wider product inventory remain open.

Final inline-input verification: 147 core tests pass at 81.86% coverage; all 18 Android tests pass.
The ambiguous-target case retains its failure and earlier screenshots without an extra callback.
Ruff, format, 44-file typing, Nix/workflow checks, offline builds and privacy/local links pass.
Desktop/mobile report inspection verifies loaded original captures without external resources.
The APK and client-derived patches are unchanged. This ticket and the broader goal remain open.
