# Next-agent handoff

## Starting state

GramLab has pinned Nix/direnv environments, an acquired Android source checkout and an
experimental Linux process boundary with real-process and dedicated AOSP guest tests. Cached
Android dependencies rebuild offline under strict verification. An experimental SQLite world
drives a real local bot through HTTP; its reply now renders in the actual Telegram Android
application through synthetic startup and a Java semantic read adapter. The upstream chat renderer
is preserved. There is no public simulator SDK/CLI or complete interaction loop yet.

The active goal remains the real bot → actual Android → real inline-button tap/callback → edit →
bot/client recovery loop, followed by the wider agreed feature inventory. No real accounts or DC
connections are permitted. Git has a configured `origin`; remote publication is not authorized.
Host-specific settings, proxy addresses, process handles and generated artifacts stay ignored.

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
as `3fc3b07`; the process/guest milestones are `7950caa` and `faa6f92`; build preparation is
`6b7dc67`. Current work is on
`feat/android-offline-client`. No remote publication has occurred.
The pinned SDK has been realized and its tool versions checked in a disposable network namespace;
the source checkout and submodule pins are verified. Gradle/plugin provisioning and preparation
APK compilation, contained rebuilding and initial real rendering passed. Continue the approved
adapter rather than introducing a second renderer or a generated upstream schema in Python.

Read [synthetic application evidence](android-application.md). Patch four binds the world/persona
before normal startup, seeds the existing controller/dialog cache, replaces Java read dispatch
and removes cloud startup components. Native guards and independent network containment remain
mandatory. The real bot's mixed Persian/English reply and the ordinary message composer are
visible in the unchanged ChatActivity. The final seven-test Android gate passes, including three cold launches, exact message
visibility, missing/wrong-world startup rejection and zero Android accounts. Python static,
Nix/direnv/workflow, local-link and privacy checks pass. Fresh preparation reproduces all six
startup inputs and preserves the 6,666 checked UI/resource files. All build/test handles have
completed; detailed local artifacts remain in ignored `.cache/local-notes/application-startup.md`.

Next implement client writes/live updates and the inline callback/edit loop through the same
world. Unknown RPCs must keep explicit failures. Do not assign the world event cursor to Telegram
`pts`, invent empty successful responses to silence startup queries, or edit the renderer to
compensate for incomplete state. Current support excludes read-state/presence semantics, broader
pagination, callback/edit, media and Mini Apps. Component data mounts/quotas and complete license
and source reconstruction audits remain open. The trusted bot fixture shares the supervisor's
run data mount; do not describe it as separately filesystem-isolated.

## Earlier milestone history

The following records describe successive preparation artifacts. References to a disabled app or
unimplemented startup apply to those earlier milestones; current startup is documented above.

The [process boundary](runtime-boundary.md) now mounts only a provisioned immutable closure and
the selected data directory. Real tests cover local traffic, parent/external denial, filesystem
and descriptor isolation, privilege restrictions, concurrent runs, failed setup and descendant
cleanup. The Android profile now includes the SDK/JDK closure, required launcher utilities and
private homes; KVM access is an explicit opt-in. A fresh AOSP guest reports API 36/x86_64 and zero
accounts, reaches a local service through `10.0.2.2`, and rejects external IPv4/IPv6 attempts with
`Network is unreachable`. Its process namespace has only loopback. The captured AOSP launcher was
inspected; this is not Telegram rendering evidence.

The previous runtime/guest gate passed thirteen tests with 90.91% runtime-only statement coverage.
The expanded core/world/Bot API/client bridge gate passes 27 tests with 90.72% coverage. Android
tests have a separate gate. Strict typing, lint/format, local links and Nix checks
pass. The manual CI is configured for the core tests but has not been remotely
dispatched. [Android build preparation](android-build.md) now exports pinned tracked source,
sanitizes credential fields and applies a reviewed build patch for a disabled-by-default GramLab
APK. Gradle's checksum and AGP's published module checksum match; the Java renderer and complete
x86_64 native library compiled. APK signature, ABI and disabled manifest checks passed. The
committed dependency record contains 918 checksummed artifacts; fresh preparation installs it.
The clean contained rebuild exposed Ninja's `/bin/sh` requirement; the pinned Android-only shell
link passed its regression and the full guest/process suite. The contained rebuild completed;
its APK signature, binary manifest and x86_64 libraries were inspected. A deliberately incorrect
AGP checksum was rejected by strict offline verification and the metadata was restored afterward.
No build or emulator remains running. Ignored `.cache/local-notes/android-build.md` records local
artifact locations and completed handles; never assume an old observation timeout stopped a build.

The [world/bot prototype](world-bot-prototype.md) now persists users/private chats, explicit time,
messages, ordered events and per-bot update delivery. A separate bot process receives mixed
Persian/English text through actual HTTP, replies into the same world and acknowledges delivery.
Tests cover database reopening, rejected changes, concurrent writers, token/world/chat scope,
malformed requests and explicit unsupported operations. Capabilities are generated independently
of the stored seed and only their hashes persist. The seed is metadata, not a random-scenario engine.

The [client read boundary](client-bridge.md) now provides a versioned atomic persona snapshot and
filtered event cursor over authenticated HTTP. Database migration preserves existing worlds and
pending bot delivery; concurrent snapshot reads stay consistent with message writes. Use this
boundary rather than the legacy separate snapshot/history/event reads. Next implement the approved
client network/startup patch and authenticated Java semantic translation. The trusted
bot fixture also shares its run data mount; separate component filesystem access and quotas remain
open. The current preparation manifest explicitly disables the application;
do not enable/install it as a shortcut to synthetic startup. Preserve actual rendering and audit
native/background networking before installing the client, even inside containment.

The [native transport guard](android-native-guard.md) is now the second GPL patch. A real JNI
request was accepted in the failing baseline probe; the guarded APK rejects both request and
initialization entry points while preserving native buffer operations. Five Android runtime tests
pass, including a fresh guest with local reachability and external IPv4/IPv6 denial. The probe uses
`app_process`, without package installation or `ApplicationLoader` startup. Native abort backstops
are compiled but not directly invoked by the test. Fresh preparation reproduces the changed
inputs and preserves 6,666 checked UI/resource files. JNI declarations/registration remain intact.
Next replace Java transport dispatch and direct clock/state/proxy/DNS operations, remove cloud
startup/push/account-sync paths, and configure synthetic identity before enabling the application.
Preserve `native_setJava(false)` for memory/delegates; it does not start the transport worker.
All current build and guest handles completed; local paths and detailed startup leads are ignored.

The third GPL patch adds the [Java semantic snapshot adapter](android-semantic-bridge.md).
A real bot reply now crosses authenticated local HTTP into the guest and round-trips through the
pinned TL dialog/history serializer with correct identity, direction, order and mixed-language text.
Wrong world/persona, another world's capability, external endpoints and local redirects fail with
explicit errors. Six Android tests pass; the 27-test core gate is unchanged. Fresh preparation
matches the adapter, preserves dependency metadata and retains the checked upstream UI/resources.
The probe uses upstream's AppTests serialization mode without lifecycle startup. `GramLabBridge`
is not yet connected to `ConnectionsManager` or `ApplicationLoader`; the application remains
disabled. Continue with synthetic startup and live request/update dispatch rather than treating
the TL projection as renderer evidence. Local build/probe paths are in ignored
`.cache/local-notes/semantic-bridge.md`.

The full first implementation milestone is a virtual identity, real local bot response, actual Android
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
