# Next-agent handoff

## Starting state

GramLab has pinned Nix/direnv environments, an acquired Android source checkout and an
experimental Linux process boundary with real-process and dedicated AOSP guest tests. Cached
Android dependencies rebuild offline under strict verification. An experimental SQLite world
drives a real local bot through HTTP; its reply now renders in the actual Telegram Android
application through synthetic startup and a Java semantic read adapter. The upstream chat renderer
is preserved. A bounded real inline-tap/callback/edit and bot/client recovery loop now has
[Android evidence](android-callbacks.md). An experimental Python scenario client exists; the
simulation-only consumer launcher now prepares selected files and retains automatic run reports.
Android modes in that launcher remain unfinished.

The bounded real bot → actual Android → inline-button tap/callback → edit → bot/client recovery
loop is the first milestone of the active goal; the wider agreed feature inventory remains open. No real accounts or DC
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

Continue the [programmable scenario workstream](../../.scratch/programmatic-scenarios/spec.md).
The [consumer runner](consumer-runner.md) now provides `gramlab run` and `python -m gramlab run`
with a TOML manifest, selected source/data files, private scenario/bot processes, named bot IDs,
timeouts and bounded redacted logs. Normal runs, assertion/bot failures, output limits and missing
runtime startup retain JSON/HTML evidence. Large HTML sections use explicit previews while JSON
retains complete state. The installed two-conversation example passes; desktop/mobile browser
inspection finds the actual conversation evidence, no layout overflow and no external resources.

Continue claimed ticket 02 by connecting actual Android observation to this consumer workflow.
Both Android modes currently fail explicitly during preparation. Preserve the existing private
emulator component, authoritative world and original renderer. The actual Android test harness
still owns its separate rendering/recovery evidence; do not claim a simulation-only runner test
proves Android support. Consumer-requested lifecycle/fault commands and broader dependency
packaging also remain open. Local runner evidence is recorded in ignored
`.cache/local-notes/consumer-runner.md`.

The final core gate passes 132 tests at 87.74% measured coverage. Full lint/format, strict typing
across 37 files, Nix/workflow checks, offline distributions and local-link/privacy checks pass.
The contained supervisor's copied source is not coverage-instrumented; its behavior is exercised
through the actual CLI. No Android source/runtime change or new guest evidence is part of this
runner milestone. All recorded run/check handles completed.

Its [world control layer](scenario-control.md) now lets a private scenario process create users,
chats and actions over authenticated local JSON while trusted orchestration retains the database
and bot lifecycle. The real private scenario → separate echo bot exchange passes with complete
semantic results and filesystem/egress observations. Wrong-world/capability, malformed input,
directory replacement, callbacks and concurrent writers are tested. Control capability redaction
is included. All 91 core tests pass at 92.07% coverage, with static and Nix/workflow checks passing.
No Android source/runtime change or new guest run was needed. Local evidence and completed
handles are in ignored `.cache/local-notes/scenario-control.md`.

The [experimental Python scenario client](scenario-sdk.md) now provides all nine world operations.
Actual loss-after-commit injection produces one mutation and an explicit uncertain outcome without
retry. Malformed responses, redirects, timeouts, server errors, configuration and proxy rejection
are tested. The private scenario and concurrent writers now use the SDK; all 100 core tests pass
at 92.46% coverage, with full static checks passing. Local evidence is in ignored
`.cache/local-notes/scenario-sdk.md`.

Ticket 01 is resolved; consumer-runner ticket 02 remains claimed for Android integration and
the remaining workflow acceptance. Selected file packaging, the simulation-only launcher,
bounded process lifecycle and automatic reports are implemented as described above.
Keep consumer Python in its own component; the approved per-run capability and local HTTP model
already authorize this direction. Do not freeze a stable public API or change the architecture
without the required consultation. The full foundation and broader product inventory remain open.

The [Bot API request encoding follow-up](bot-request-encoding.md) now accepts URL-encoded forms,
query-only POST and serialized keyboard/entity values. Textual callback Booleans follow the
inspected server argument behavior. Invalid UTF-8 and malformed nested JSON fail before mutations
or update acknowledgment; a UTF-16 poll regression previously consumed delivery incorrectly.
The independent formatting bot uses forms and retains the same complete simulation/Android
expectations. All 82 core tests pass at 91.99% coverage, and the focused actual Android
formatting/edit/restart case passes. The client/APK is unchanged. Detailed local evidence and
completed handles are in ignored `.cache/local-notes/request-encoding.md`.

The [HTML report follow-up](reports.md) adds an experimental original report writer and a runnable
documentation example. The actual recovery scenario emits complete semantic evidence and three
original Android screenshots after its assertions pass. Report tests cover malicious text,
credential redaction, bounded PNG validation and exclusive concurrent publication. The core gate
passes 73 tests at 91.47% coverage; the focused actual Android recovery case passes. The client
and APK are unchanged from the prior thirteen-test Android gate. Browser inspection covers desktop
and mobile layouts, loaded captures, disclosure controls and inert malicious text. This does not
complete automatic failure reporting, scenario SDK, concurrency or performance acceptance.
Local artifacts and completed handles are recorded in ignored `.cache/local-notes/reports.md`.

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

The [callback world foundation](callback-world.md) now implements inline callback keyboards,
private bot text/keyboard edits, generated queries, durable answers and authenticated client
callback commands. Request IDs deduplicate retries per persona; stale data remains deliverable.
Storage version 3 preserves prior world identity/outbox and handles concurrent migration. A real
bot killed after receiving a callback restarts, receives the same pending update, then edits,
answers and acknowledges it. The new core gate passes 34 tests at 91.47% coverage; all seven
existing Android tests still pass. New typing/workflow checks and public-tree privacy pass.
The [Android callback follow-up](android-callbacks.md) now adds keyboard/edit conversion, real
callback dispatch and ordered live message events through the original controller. The actual
button tap creates a callback; a bot killed before handling resumes the same update, edits and
answers, and the edited message survives a client cold restart. The world and Android modes use
the same semantic scenario. The fifth GPL patch changes only the two GramLab adapter classes.
Fresh preparation matches both and preserves all 6,666 checked upstream UI/resource files.

The legacy software graphics path crashed the emulator with SIGSEGV after inline input. A core
dump localized the fault to generated graphics code; exact shader symbols were unavailable.
The documented `swangle` mode (SwiftShader through ANGLE) passes the focused interaction loop
under the same approved software-GPU direction and pinned app/emulator/image/display. The guest
reports its actual graphics backend. Do not conflate earlier legacy-profile screenshots with a
pixel-equivalence baseline. The full gate also exposed an observation race: wait for both messages,
not just the cached bot reply, and decode UIAutomator XML entities when matching text.

The final eight-test Android gate passes, including the real callback case and existing network,
JNI, bridge and startup rejection tests. Python static, Nix/direnv/workflow, fresh preparation,
APK signature/manifest/ABI, local links and public-tree privacy checks pass. Machine observations,
crash diagnostics and generated UI evidence stay in ignored directories.
The separate core gate passes 34 tests at 91.47% coverage. All build/test handles have completed;
local artifact locations and completed handles are in ignored `.cache/local-notes/callback-world.md`.

The [component boundary](component-boundary.md) now separates real bot files/processes from trusted
world/guest orchestration while sharing the run's offline network. `Sandbox.supervise` explicitly
permits trusted nested setup; `component` children have private mounts/PIDs, cleared inherited
state, no effective capabilities and no further user namespaces. A fixed non-root supervisor
identity avoids retaining privileges for nested UID mapping. Pidfd cleanup covers normal exit,
exceptions, explicit kill, supervisor death and timeout; simultaneous components retain separate
state. All real bot probes use this path. The callback bot rejects visible world files and its
private launch counter survives restart. The current gate passes 42 core tests at 90.64% coverage
and all eight Android tests. Static and Nix/direnv/workflow checks pass. The APK and upstream
adapter are unchanged. All build/test handles have completed; ignored
`.cache/local-notes/component-boundary.md` records the local evidence locations.

The emulator now runs in a separate component with its own AVD, Android home/cache and logs.
The actual QEMU process's root cannot see world/bot files and has a distinct PID namespace while
retaining the run network. KVM requires explicit outer and component opt-in; missing outer access
fails setup without running the child. The real callback case repeats filesystem observations
after world and bot state exist. All ten Android tests pass, as do 42 core tests at 90.64% coverage,
static checks and Nix/direnv/workflow validation. Edit/restart screenshots were inspected. The
APK and source patches are unchanged. All handles completed; local evidence is recorded in ignored
`.cache/local-notes/emulator-component.md`. See the
[emulator follow-up](component-boundary.md#emulator-filesystem-follow-up).

The [Bot API long-poll lifecycle](bot-long-polling.md) now accepts bounded integer timeouts, sees
later world writes and interrupts a previous same-bot poll with HTTP 409. Invalid requests cannot
acknowledge or displace valid polls; bots/worlds remain independent. Server shutdown wakes pending
polls, closes incomplete request input and joins handlers. Disconnected consumers can retry the
same pending update across server restart. The private echo fixture now uses long polling, and a
separate real-bot probe establishes a wait before the virtual user supplies its message.
All 51 core tests pass at 91.04% coverage, and all ten Android tests pass. Static/Nix/workflow and
local-link/privacy checks pass; the inspected restart screenshot retains the edited reply. No APK
or source-patch changes were needed. All handles are terminal; ignored
`.cache/local-notes/long-polling.md` records detailed local evidence. Poll ownership is per server;
filters, negative offsets, expiry, webhook coordination and production flood timing remain open.

The [formatting follow-up](formatted-text.md) adds nine explicit non-link entity types at the
Bot API/world boundary, with UTF-16 validation, canonical lists and atomic formatting-only edits.
The sixth GPL patch translates those entities through the shared snapshot/history/event adapter.
A real private bot edits only formatting; the actual Android chat shows emphasis, spoilers, code
and quote blocks, retained after cold restart. Simulation-only and Android modes verify the same
complete final semantic state. The pinned TL serializer preserves all nine types, code language
and the expandable quote flag. Long-quote expansion gestures remain unverified.

All 65 core tests pass at 91.56% coverage and all twelve Android tests pass. Fresh six-patch export
matches both Java inputs and strict dependency metadata, preserving 6,666 upstream UI/resource
files. The contained offline build, APK signature/manifest/ABI, static/Nix/workflow and
local-link/privacy gates pass. Final formatting and callback restart screens were inspected.
Public documentation now describes GramLab independently of private consumer projects.
All build/test handles are terminal; ignored `.cache/local-notes/formatting.md` records local
artifact paths and diagnostics. Links, parse modes, media/custom emoji and the RichMessage block
API remain open. Keep the full goal active; this is a formatting milestone, not full acceptance.

The [older-history recovery follow-up](android-history-recovery.md) now fixes an observed stale
cache: a real bot edits an older reply and sends a newer one while Android is stopped. Startup
reconciles all snapshot histories through upstream storage, retaining the database. Two cold
restarts show corrected text/entities, removed keyboard and all four messages exactly once.
The same scenario has identical complete bot/world results without Android. The seventh GPL
patch changes only the adapter runtime class; the existing storage queue barrier precedes events.

All 66 core tests pass at 91.56% coverage and all thirteen Android tests pass. Fresh seven-patch
export reproduces Java inputs and strict metadata, preserving 6,666 upstream UI/resource files.
Contained build, APK signature/manifest/ABI, static/Nix/workflow and local-link/privacy checks pass.
The final repeated-restart screenshot was inspected. All handles are terminal; ignored
`.cache/local-notes/cache-recovery.md` records diagnostics and `.cache/local-notes/client-write-leads.md`
holds source leads for the remaining composer/correlation work. Public scenarios/SDK and reports
still need implementation; the working real loop currently lives in internal probes and fixtures.

Continue ticket 02's resource quotas, per-component control-port restrictions and media isolation,
client text writes, deletion/multi-dialog recovery and durable replica/command recovery. The current cursor is in
memory and is never assigned to Telegram `pts`. Live participant changes, broader read-state and
presence semantics, pagination, media and Mini Apps remain unsupported. The first bounded loop
is evidence toward ticket 03, whose selected rich/media/emoji case remains open. Full source and
license reconstruction audits and the wider versioned compatibility/scenario/report inventory
remain active. Unknown operations must retain explicit failures; no remote publication.

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
