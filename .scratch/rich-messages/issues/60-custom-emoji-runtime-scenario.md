# Provision emoji decoding and expose trusted scenario registration

Type: feature
Status: ready-for-agent
Work state: claimed
Blocked by: ticket 59 for complete scenario registration acceptance

Coordinator owns Nix runtime/development provisioning, `runtime.py`, runner/CLI, `_android.py`,
`_run.py`, `_control.py`, `scenario.py`, new runtime-selection/scenario tests and shared docs.
Follow the [implementation contract](../../../docs/development/custom-emoji-implementation-contract.md).
Supply pinned decoder paths solely from trusted provisioning; preserve ordinary component startup
costs. Add explicit trusted bridge-version launch choice, default 3 with version 4 opt-in recorded
with APK/profile evidence. Scenario registration carries bounded media bytes over its dedicated
authenticated route and preserves idempotency/uncertain outcomes. Complete real contained scenario
registration and native version selection after integrating core and adapter dependencies.

## Runtime evidence

The initial nine public/runtime checks failed before implementation and pass after it. Actual
FFmpeg/ffprobe run inside the contained supervisor and decode the original VP9 stream metadata;
an ordinary contained process has neither the codec environment variable nor access to its
executable. Invalid bridge versions reject before staging a run. Scoped Ruff/format and strict
mypy pass; host-system offline flake checks pass. Other platform builds and native v4 remain unproven.

The first four-worker affected regression passed 48 cases but failed an existing one-second
descendant-timeout check before its scenario heartbeat started; a serial control passed. Measured
old/new closure startup then exposed unnecessary mounting of 294 rather than 57 store paths in
ordinary components: mean serial startup 41.5→229.2 ms, concurrent 71.4→446.9 ms in that comparison.
Move codecs into optional trusted supervisor-only profile paths/environment, preserving backward
compatibility for earlier profiles. A fresh identical comparison after the fix measured serial
55.5/54.9 ms and concurrent 125.1/126.3 ms for before/after profiles, both with 57 ordinary paths.
These local samples establish removal of added mount overhead, not a general performance claim.
All 49 affected runner/runtime checks then pass in 12.89 seconds with four workers; the final
enhanced nine-case selection passes in 1.26 seconds. Original failed evidence is preserved.

Scenario boundary red currently has two expected failures (missing registration method and missing
route) and two existing wrong-operation rejections. SDK/control implementation and complete
registration acceptance remain in progress with ticket 59. Do not claim a working catalog from
decoder provisioning or ordinary runner tests.
