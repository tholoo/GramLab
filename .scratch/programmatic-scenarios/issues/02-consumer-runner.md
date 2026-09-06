# Run consumer scenarios with lifecycle and evidence

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: 01

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
