# Next-agent handoff

## Starting state

GramLab has a scaffold, pinned development flake and an acquired Android source checkout. There
is no simulator, offline Android build, public Python API, runtime CLI, binary fixture set or
behavioral test suite. Git has a configured `origin`; publishing to GitHub/PyPI or acquiring real Telegram accounts is not authorized by this task.
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
Android integration. Scaffold baseline is committed as `bec0ef4`; current work is on
`research/android-offline-seam`. No remote publication has occurred.
The pinned SDK has been realized and its tool versions checked in a disposable network namespace;
the source checkout and submodule pins are verified. Gradle/plugin provisioning, offline APK
compilation and actual isolated synthetic startup remain the next gates. Validate the minimal
offline adapter boundary before implementing a wide feature catalog. Read source findings as leads, not as tested integration guarantees.

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
