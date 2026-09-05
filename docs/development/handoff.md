# Next-agent handoff

## Starting state

GramLab has pinned development environments, an acquired Android source checkout and an
experimental Linux process boundary with twelve real-process tests, including a dedicated AOSP
guest's startup and local/external network behavior. There is no simulator,
offline Android build, public Python API, runtime CLI or binary fixture set. Git has a configured
`origin`; publishing to GitHub/PyPI or acquiring real Telegram accounts is not authorized by this task.
See [scaffold verification](scaffold-verification.md) for the checks already performed and their limits.

Read [AGENTS.md](../../AGENTS.md), [CONTEXT.md](../../CONTEXT.md), [TESTING.md](../../TESTING.md),
[offline safety](offline-safety.md), [architecture](../architecture/overview.md), and the
[foundation spec](../../.scratch/android-offline-foundation/spec.md).

## Agreed decisions

- Actual Telegram **Android** UI, minimally patched; not Web A, Desktop or a CSS approximation.
- Python core/SDK, independently written under MIT; client-derived components retain applicable GPL.
- Simulation-only, headless Android and interactive Android are distinct modes sharing world state.
- Offline-by-default, synthetic identities and local deterministic assets; no production/Test-DC
  connections, sessions or external fallback in normal runs.
- Fidelity is measured against pinned versions/profiles and supported surfaces. Unsupported behavior
  fails explicitly and remains visible in the compatibility matrix.
- Local Markdown issues, default triage roles, `AGENTS.md`, root glossary and root ADRs.
- Manually invoked suites; all bot functionality is in the long-term inventory, not only games.
- Reports include bugs/fixes/decisions, before/after UI where meaningful, and latency diagnosis.
- Consult the user before consequential design decisions or changing this scope.

## First action

Continue [ticket 02](../../.scratch/android-offline-foundation/issues/02-offline-world-and-safety.md).
The user approved the [foundation proposal](android-foundation-proposal.md), source/dependency
provisioning and project Nix/direnv setup. Do not ask again for those same choices.
The [source findings](android-source-feasibility.md)
and [portable host checks](android-host-feasibility.md) are preparation guidance, not a completed
Android integration. Scaffold baseline is committed as `bec0ef4`; Nix preparation is committed
as `3fc3b07`; current work is on `feat/offline-runtime-boundary`. No remote publication has occurred.
The pinned SDK has been realized and its tool versions checked in a disposable network namespace;
the source checkout and submodule pins are verified. Gradle/plugin provisioning, offline APK
compilation and actual isolated synthetic startup remain the next gates. Validate the minimal
offline adapter boundary before implementing a wide feature catalog. Read source findings as leads, not as tested integration guarantees.

The [process boundary](runtime-boundary.md) now mounts only a provisioned immutable closure and
the selected data directory. Real tests cover local traffic, parent/external denial, filesystem
and descriptor isolation, privilege restrictions, concurrent runs, failed setup and descendant
cleanup. The Android profile now includes the SDK/JDK closure, required launcher utilities and
private homes; KVM access is an explicit opt-in. A fresh AOSP guest reports API 36/x86_64 and zero
accounts, reaches a local service through `10.0.2.2`, and rejects external IPv4/IPv6 attempts with
`Network is unreachable`. Its process namespace has only loopback. The captured AOSP launcher was
inspected; this is not Telegram rendering evidence.

All twelve tests pass with 90.65% statement coverage; strict typing, lint/format, local links and
Nix checks pass. The manual CI is configured for the core tests but has not been remotely
dispatched. Next provision the pinned Gradle/plugin dependencies and implement the approved
minimal offline client patch plus synthetic world/bridge activation. Preserve actual rendering
and audit native/background networking before installing the client, even inside containment.

The first implementation milestone is a virtual identity, real local bot response, actual Android
rendering, real button tap/callback, bot edit, restart/recovery, and independently verified zero
external egress. Do not settle for pushing static screenshots into a fake chat.

Keep interfaces narrow while proving the boundary. Propose the bridge, state persistence and
runtime isolation choices with evidence before hardening them into public API. If the Android
adaptation fails, report the exact cause and alternatives to the user; do not silently switch clients.

## Runtime preparation

Use the [development environment](environment.md) and [runtime provenance](android-runtime-provenance.md).
No Waydroid or host service change is assumed. Keep host-specific observations and active process
handles in ignored `.cache/local-notes/`. Provision public source and dependencies separately;
the resulting client/scenarios must run isolated. Never use the Telegram account
provisioning folders or real credentials from another project.

## Where to record progress

Update individual [foundation tickets](../../.scratch/android-offline-foundation/spec.md), the
[compatibility matrix](../compatibility/matrix.md), and [source pins/evidence](upstream.md).
Keep synthetic run artifacts under ignored `artifacts/`; preserve durable conclusions in Markdown.
