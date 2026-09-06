# Establish isolated synthetic state and enforce offline execution

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: 01

Use the approved boundary/runtime from ticket 01. Define the smallest real world and lifecycle
needed for the round trip. Implement public behavior test-first; avoid speculative API stubs.

## Acceptance

- Two independent worlds can create synthetic users/chats with no shared state or credentials.
- Dedicated Android fixture state starts without authentication to any Telegram environment.
- Independent enforcement blocks external network paths from the core, bot and Android runtime.
- Tests demonstrate denied external attempts, allowed local traffic, safe artifact paths and
  scoped cleanup. Merely observing no network call is insufficient.
- IDs, media, update queues and run artifacts are isolated; seeds and clocks are controllable at
  owned boundaries. Record any Android timing limitations explicitly.

## Comments

Promote triage status only when ticket 01 resolves the runtime and boundary choices.

2026-09-05: Claimed after the user approved ticket 01's proposal. Reproducible development
provisioning is underway; next prove the independent runtime boundary and synthetic startup.
No client/bot execution is authorized without the required containment.

Preparation completed: pinned Nix core/Android shells, optional direnv Android selection, local
cache paths, formatter/checks and manually dispatched CI. Core/direnv entry, SDK package
realization, network-isolated Android tool version checks, source/submodule pins and archive
checksums passed. The SDK's duplicate legacy NDK alias was removed and rechecked. Actual world
state, OS containment runner, synthetic Android activation and the interaction loop are still
unimplemented. Keep host-specific records in ignored local notes, as requested by the user.

2026-09-06: Implemented the experimental Linux process boundary and Python packaging on
`feat/offline-runtime-boundary`. Nine real-process tests pass with 90.10% coverage; typing,
lint/format, Nix/direnv/workflow checks, configuration parsing and local links pass. Regression
tests caught symlinked data-root acceptance and premature timeout cleanup; both are fixed.
The [runtime evidence](../../../docs/development/runtime-boundary.md) records exact capabilities,
portable commands and remaining limits. No Android guest/client or real bot has started; world
state and the acceptance criteria above remain open. The manual CI now requires the runtime gate
but has not been dispatched remotely. Next extend the provisioned profile and validate dedicated
Android guest startup/egress before synthetic activation.

2026-09-06 Android follow-up: Extended the trusted Nix profile with SDK/JDK and required shell
utilities, private Android homes and explicit KVM device opt-in. Twelve combined tests pass with
90.65% coverage, including a fresh AOSP API 36/x86_64 guest reporting zero accounts, local TCP
through the emulator alias and rejected external IPv4/IPv6 attempts. The AOSP launcher screenshot
was inspected; generated state, logs, timings and screenshots remain ignored. No Telegram client,
bot or simulator has run. Core static/Nix/direnv gates pass; full application network surfaces,
world persistence, synthetic Telegram activation and the real interaction loop remain open.
Continue approved Gradle/plugin provisioning and minimal offline client/bridge/world implementation.

2026-09-06 build preparation: Added a pinned tracked-source exporter and GPL-preserving build
patch queue on `feat/android-offline-client`. Fresh exports apply cleanly, refuse overwrite, omit
upstream credential templates/ignored build data, and preserve 6,666 checked UI/resource files
byte-for-byte. Gradle 8.11.1 passed its published checksum; AGP 8.10.1 matches official module
checksum metadata. The official Google distribution CDN resolves the Maven endpoint failure.
The Kotlin build plugin, JLatexMath and Telegram Java renderer compiled. The packaged manifest
has the distinct GramLab application ID with application/backup disabled. The complete x86_64
preparation APK compiled and passed signature/ABI inspection; its hash is in the
[build evidence](../../../docs/development/android-build.md). Strict dependency metadata contains
918 checksummed artifacts and is installed by fresh source preparation. A contained rebuild
exposed Ninja's missing `/bin/sh`; a pinned Android-only shell link passed the failing regression
and all thirteen process/guest tests (90.91% coverage). The contained rebuild then completed with
cached dependencies and strict verification; binary manifest, signature and native ABI checks
passed. An intentionally wrong AGP checksum was rejected and original metadata restored. No
client runtime success is claimed; continue the approved startup/network patch, world/bridge and
real bot loop. Machine-specific build records remain ignored.

2026-09-06 world/bot follow-up: Implemented independently owned SQLite users/private chats,
explicit world time and seed metadata, transactional message/event/update delivery and per-bot
acknowledgment. A separate bot process with no GramLab imports exchanges mixed Persian/English
text over local HTTP inside the runtime boundary, persists its reply and confirms its update.
Tests cover reopen persistence, malformed/unauthorized transitions, concurrent writers, separate
bot queues, generated token scope and unsupported API behavior. The
[prototype record](../../../docs/development/world-bot-prototype.md) lists exact capabilities and
limits. No Android client activation/render/tap has occurred. Atomic client snapshots, distinct
component data mounts, callback/edit semantics and abrupt process recovery remain open; keep the
full foundation acceptance active.

Final core gate: 22 passed, four unchanged Android tests excluded, 89.79% statement coverage.
Strict typing (including the independent bot and orchestration), lint/format, Nix/workflow, local
links and public-tree privacy pass. The retained synthetic transcript contains full API responses
and world history without capabilities. The invalid-poll regression proved that option validation
must precede acknowledgment; it now preserves pending delivery. No remote workflow was dispatched.

2026-09-06 client read boundary: Added atomic persona snapshots with a persistent world identity,
filtered event cursors and separate generated client capabilities over actual HTTP. The prior
database format migrates without losing messages or pending bot updates. Five new tests cover
complete snapshot contents, migration/reopen, hidden-event cursor advancement, concurrent writes,
wrong-persona/world/bot authorization, malformed requests and service reopening. The
[protocol record](../../../docs/development/client-bridge.md) defines cursor gaps, resnapshot rules
and current limits. The expanded core gate passes 27 tests with 90.72% statement coverage.
Native guard work and Java integration continue separately; no Android rendering or complete
foundation acceptance is claimed. Machine-specific observations remain ignored.

2026-09-06 native guard follow-up: The second GPL patch enables native transport rejection in the
GramLab build while preserving JNI bindings and renderer/storage memory operations. The corrected
baseline probe reached the real native request boundary and failed with a normal return; after
the patch, JNI request/init reject and the buffer round trip succeeds. All five Android runtime
tests pass in isolation, including local/external network checks. The APK is not installed and
the application remains disabled; the probe uses `app_process` without account or application
startup. Both native guard builds completed offline with strict dependency checks. Fresh source
export applies the queue, matches edited build inputs and preserves all 6,666 checked UI/resource
files. Signature/ABI/disabled-manifest, Python static, Nix/workflow, links and privacy checks pass.
The [guard evidence](../../../docs/development/android-native-guard.md) states the direct-native
and remaining background/Java/startup limitations. Continue synthetic identity and Java bridge
integration; the full foundation acceptance remains open. No remote publication occurred.

2026-09-06 Java snapshot follow-up: The third GPL patch adds local authenticated snapshot transport
and client-side TL identity/dialog/history conversion. The missing implementation failed first;
the real bot/world/guest round trip now passes with correct Persian/English text, message direction,
dialog peers and history order after pinned TL serialization. Wrong-world/persona credentials,
another world's capability, external endpoint configuration and redirects fail explicitly.
All six Android tests pass, including the previous JNI/network/guest checks; the 27 core tests are
unchanged. Fresh three-patch preparation matches the adapter and preserves 6,666 UI/resource files
and strict dependency metadata. Static/Nix/workflow, local links and privacy pass. See the
[adapter evidence](../../../docs/development/android-semantic-bridge.md) for test-context and
protocol limits. No package installation, lifecycle activation or rendering occurred. Next connect
Java RPC/update dispatch and synthetic startup; keep the real tap/edit/recovery acceptance open.

2026-09-06 synthetic application follow-up: The fourth GPL patch binds the world/persona before
startup, installs the synthetic identity, replaces Java read dispatch and removes cloud startup
components. A real local bot's Persian/English reply now renders in the unchanged Telegram chat.
The disabled baseline failed to launch; an initial cache mismatch left an incorrect Start Bot bar,
which is fixed through normal Telegram storage APIs without editing the renderer. Missing
configuration and a valid other-world configuration fail before client startup with static,
credential-free diagnostics. Three cold launches (initial, restart, restored original world) show
both messages exactly once and zero Android accounts. The authoritative history remains unchanged.
All seven Android tests pass, including existing JNI and local/external guest networking checks.
The 27-test core gate remains at 90.72% coverage. Fresh four-patch preparation matches edited
inputs, preserves all 6,666 UI/resource files and dependency metadata; signature/manifest/ABI,
static/Nix/workflow, local-link and public-tree privacy checks pass. See the
[application evidence](../../../docs/development/android-application.md) for failure corrections,
profile, commands and limitations. Logs, credentials, APKs and host observations remain ignored.
The full acceptance remains active: client writes/live updates, real callback/edit, broader
recovery, component data mounts/quotas and media isolation are still open. No remote publication.

2026-09-06 callback world follow-up: Added validated inline callback keyboards, atomic private bot
text/keyboard edits, durable callback queries/answers and authenticated client callback commands.
One client request ID deduplicates concurrent/reopened retries; distinct taps remain distinct.
Stale data reaches the bot, while wrong actors/worlds, malformed UTF-8 byte limits and invalid
mutations are rejected. Storage version 3 migrates prior formats while retaining identity and
pending updates; concurrent openers and retries are tested. A separate real bot is SIGKILLed after
callback receipt and before mutation, then restarts, receives the same update, edits the original
message, answers and acknowledges. The exact history and HTTP results are checked. All 34 core
tests pass with 91.47% statement coverage; all seven existing Android tests pass unchanged.
Static/Nix/workflow, links and public-tree privacy checks pass. See the
[callback record](../../../docs/development/callback-world.md) for supported fields and deliberate
limits. Actual Android keyboard/callback/live-edit translation, partial-mutation recovery,
component filesystem boundaries and wider compatibility remain open. Keep the full goal active.

2026-09-06 actual Android callback follow-up: the fifth GPL patch translates inline keyboards,
callback requests/answers and ordered live message edits through the existing controller. A real
tap creates the query, a bot killed after receipt replays it on restart, and the visible edited
message survives a client cold restart. The shared simulation-only scenario has the same exact
history and answer. Native emulator crashes were traced to generated graphics code; the documented
SwiftShader-through-ANGLE software mode passes under the pinned app/emulator/image/display and
independent isolation. The guest reports its actual graphics backend. Observation fixes wait for
both messages and decode UIAutomator XML without relaxing assertions.

All eight Android tests pass, including existing network/JNI/bridge/startup rejection checks.
All 34 core tests pass at 91.47% coverage. Fresh preparation matches both adapter inputs and strict
dependency metadata, preserving 6,666 upstream UI/resource files. Static/Nix/workflow, signature,
manifest/ABI, local links and public-tree privacy checks pass. Screenshots and machine-specific
diagnostics remain ignored. See the [callback evidence](../../../docs/development/android-callbacks.md).
This ticket remains active: component mounts/quotas, media isolation, older cache/replica recovery
and the wider compatibility/license acceptance are unfinished. No remote publication.

2026-09-06 component isolation follow-up: added explicit trusted run supervision and restricted
components sharing only the run network. Bot data/PID/mount namespaces are separate from the world
and client artifacts; environment/descriptors are cleared, capabilities dropped and further user
namespaces disabled. Nested setup initially failed at UID-0 mapping; the supervisor now uses a
fixed non-root namespace identity without retaining privileges. Pidfd-based cleanup is tested for
normal exit, exception, kill, supervisor death and timeout, including detached descendants. Two
simultaneously live components preserve independent state. The pinned closure includes bubblewrap
for nested setup; no host configuration was changed.

All actual bot probes now launch through private components. The callback fixture rejects access
to world files and persists its own launch counter through SIGKILL/restart. The real Android
tap/edit/restart case remains green. All 42 core tests pass at 90.64% coverage, and all eight
Android tests pass. Static/Nix/workflow checks pass; upstream code and APK are unchanged. See
[the component contract](../../../docs/development/component-boundary.md). Resource quotas,
emulator host mount separation, media/network surfaces and broader recovery remain open. No
remote publication; machine-specific observations and generated state remain ignored.

2026-09-06 emulator component follow-up: moved AVD creation and the pinned QEMU host process into
a private component; the trusted world/ADB supervisor retains orchestration. A real QEMU-root
regression first exposed readable world/bot sentinels and a shared PID namespace. The separated
runtime retains its AVD while world/bot paths disappear, its PID namespace differs and its local
network remains shared. KVM now has an explicit component option requiring outer opt-in as well;
default children cannot open it, and requesting an absent outer device fails without execution.

All ten Android tests pass, including nested KVM rejection/access and the actual tap/edit/restart
case with world/bot files hidden from QEMU. Edit and restart screenshots were inspected. All 42
core tests pass at 90.64% coverage; static, Nix, workflow, local links and public-tree privacy
checks pass. No Android source/APK rebuild or host configuration change was needed. See
[the emulator boundary evidence](../../../docs/development/component-boundary.md#emulator-filesystem-follow-up).
Resource quotas, same-run control-port restrictions, media safety and wider recovery/API coverage
remain unfinished. Keep this ticket and the full goal active; no remote publication.
