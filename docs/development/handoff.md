# Next-agent handoff

## Starting state

GramLab has pinned Nix/direnv environments, an acquired Android source checkout and an
experimental Linux process boundary with real-process and dedicated AOSP guest tests. Cached
Android dependencies rebuild offline under strict verification. An experimental SQLite world
drives a real local bot through HTTP; its reply now renders in the actual Telegram Android
application through synthetic startup and a Java semantic read adapter. The upstream chat renderer
is preserved. A bounded real inline-tap/callback/edit and bot/client recovery loop now has
[Android evidence](android-callbacks.md). An experimental Python scenario client exists; the
consumer launcher now prepares selected files, runs simulation-only or headless Android scenarios,
and retains automatic reports with original client captures. Interactive mode remains unfinished.

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

## Parallel development preparation

The user authorized concurrent implementation on separate worker branches, with coordinator-owned
merges and conflict resolution. Follow [the agent workflow](parallel-work.md) when dispatching,
starting or integrating work. The helper places ticket-bound checkouts under the shared sibling
`GramLab-worktrees` container, verifies assigned checkout/branch identity, and coordinates costly
checks through common Git locks. All 15 real Git/lock checks pass, including hidden untracked
work and occupied-path preservation. A disposable two-worker exercise also verifies separate
commits, two coordinator merge commits, retained changes and clean worktree removal. ShellCheck,
Bash syntax and focused Python lint/format pass. This preparation does not imply implementation
workers are currently running. Keep actual paths and runtime evidence in ignored local notes.
The full product goal remains active.
For repeated command-line checks, [tools/dev](../../tools/dev) retains the selected shell through
an ignored per-worktree Nix profile. Actual default-shell execution, its registered garbage
collection root, ShellCheck, invalid-shell rejection and nonzero command exit propagation pass.
This complements direnv and keeps local store paths out of tracked files.

## First action

Rich lists are integrated on the coordinator branch: independent normalization, native patch
0012, public nested capture/input traversal, and a reusable real HTTP bot/scenario. The focused
World/HTTP suite passes 82 cases; the full core gate passes 326 tests at 80.52% coverage in 46
seconds. Full static checks, workflow validation and installed-wheel execution pass. The installed
list result also passes complete semantic verification. The twelve-patch fresh export preserves
all 6,666 original UI/resource files; one incremental offline APK build took 2 minutes 31 seconds.

Focused native evidence covers the complete list codec and 42 malformed rejections, actual
checkbox input without user mutation, live bot edits and cold restart, plus public inline
callback/RTL editing and offscreen metadata-only ambiguity rejection. Original screenshots show
real wrapping, all five ordered label styles and nested checked/unchecked items. Ordered markers
can overlap checkboxes in the pinned renderer; preserve that quirk. The final reusable fixture
places checkboxes on nested unordered items so its ordered labels remain visible. See
[rich messages](rich-messages.md), [native projection](android-rich-projection.md) and the
[list example](../../examples/rich_lists/README.md).

Two-worker Android verification is not yet accepted. The first pair completed both scenarios but
failed a host assertion requiring the callback to remain unanswered at observation. The documented
input contract permits an early answer; a retained-result replay established and verified the
assertion correction, including rejection of an incorrect answer. The corrected second pair passes
the public example, but the direct checkbox case reports an initial cold-launch timeout. Its later
semantic steps complete, and logcat reports first display after 14.459 seconds. The unchanged case
passes alone in 75 seconds. This does not establish the cause or accept concurrent scheduling.
Do not increase timeouts, count that failure as a pass, or begin a two-worker full gate yet.
Actual process handles and evidence paths stay in ignored local notes. The next check is the
serial list-inclusive combined Android gate; poll its current handle before starting another guest.
The combined gate remains pending;
list integration/example and parallel-gate tickets remain claimed.

The preceding pre-list combined Android gate passed all 34 tests without skips in 1,865 seconds.
It is historical coverage, not a list-inclusive gate. The original effects probe's settings
observations have since been reduced from 39 to 20; a focused unchanged-profile run passed in
159 seconds versus earlier 174–176 second observations. Differing load prevents a causal speedup
claim. The combined gate must also cover that optimization with the list-capable APK.

The [timing command](test-timings.md) compares retained JUnit without rerunning guests and keeps
suite wall time separate from summed case durations. Continue measuring expensive observations
and use focused checks during iteration. Serializing all native cases remains a major development
cost, but concurrent execution needs actual reliability evidence before adoption.

The next rich-content work has [source findings](rich-actions-references.md) for links and rich
buttons. It is research only. Establish exact shared interfaces and original native targeting,
and prepare a concrete offline navigation proposal before consequential design decisions. No
external navigation or runtime egress is authorized. Rich actions, media, custom emoji, Mini Apps,
interactive mode and the wider product inventory remain unfinished; the full goal stays active.

During that gate, the coordinator reproduced a rich-string normalization gap through the World:
an admitted tab survives instead of becoming a space. The pinned cleaner also establishes
Unicode-marker removal/replacement and a per-string UTF-8 stopping rule. The
[reviewed normalization contract](rich-text-cleaning.md) and
[worker ticket](../../.scratch/rich-messages/issues/12-rich-text-cleaning.md) assign a correction
to `task/rich-text-cleaning` in its separate worktree. That worker owns only the validator, its
World/HTTP tests and ticket. The integration code/APK remain frozen; the current gate does not
cover this unmerged correction. Review its frozen handoff after the gate, then run affected
combined checks. Rich actions and permanent native geometry/target identity remain separate work.

## Previous rich-message checkpoint

The completed first parallel rich-message batch has a passing real-bot send/edit scenario and original
Android rendering evidence. The integrated offline APK builds in 2 minutes 15 seconds; the focused native test passes in 72 seconds, including
complete actual serializer observations, two malformed-table rejections, live RTL editing and cold
restart. All three original screenshots were inspected. See [the precise API subset](rich-messages.md)
and [native evidence and reproduction](android-rich-projection.md). The combined Android regression
gate passes all 29 tests without skips in 27 minutes on the new APK. Local handles,
fingerprints and artifact locations are retained in ignored notes.

The follow-up public scenario capture implementation now searches rich text fragments while
preserving structured history. Nine integrated capture tests pass, including the reusable
[rich example](scenario-rich-messages.md) in simulation. Its full core gate passes 272 tests at
81.44% coverage in 73 seconds with four pytest workers, compared with the preceding serial
269-test gate's 148 seconds. This is a measured development run, not a controlled benchmark;
the 29-test Android regression gate also passes. This new public example's native check passes
in 65 seconds, with equal simulation/Android world, history and events. All three original
captures and the report were inspected. The installed wheel passes the simulation example;
full static checks, workflow check, local links and tracked-tree privacy checks pass. All current
check/build/preview handles are terminal. The four bounded rich-message tickets are resolved;
the full product goal remains active.

The rich-inline and effects follow-ups above extend this checkpoint; the combined gate remains
separate from their focused evidence. Broader rich/media work is still open.

After the [reuse assessment](bot-api-reuse.md), the user chose to continue the independent simulator
and accelerate it with parallel implementation. The research remains a reference for contracts
and tooling; adopting a replacement backend is not the next step. Split useful feature breadth,
rich-message rendering and rendering-profile work along agreed interfaces before dispatching.
Prioritize useful feature breadth and rich-message rendering;
retain the recovery diagnostics for new failure evidence instead of repeating successful gates.

## Earlier composer and recovery milestones

The [native composer ticket](../../.scratch/programmatic-scenarios/issues/04-native-composer.md)
retains additional open boundaries. The historical checks below explain its current evidence.
The latest [transport diagnosis](android-transport-reliability.md) isolates two failures in an
independent codec loop: local handshakes stall with the pinned emulator's Netsim forwarding,
and Android can attempt to reuse the bridge's closed HTTP connection. Both launchers now select
built-in Virtio Wi-Fi forwarding with `-feature -WiFiPacketStream`; the bridge and controlled fault
proxies explicitly advertise `Connection: close`. The codec is its own test with eight fresh
worlds and 72 real HTTP requests, preserving the original send/recovery assertions separately.
The core header regression first fails on the missing close header after observing real EOF.
All 14 focused core tests and the full 216-test core gate pass at 81.09% coverage. All 11 focused
native checks pass, including both interruption cases, live-gap recovery, repeated codecs and
seven runtime checks with guest egress isolation. The unchanged APK includes the periodic
controller callback correction and safe exception-class traces from the preceding checkpoint.

The latest [recovery fixtures](live-gap-recovery.md) add distinct-minute ordering and a
1,000-message backlog spanning two native difference pages. The same-second and timed fixtures
pass together; the paged fixture then passes independently in about 70 seconds. Its first page
contains positions 2–1001, followed by 1002–1004 from cursor 1001. Polling stays held at the initial
cursor throughout recovery. Another actual send succeeds, and the real bot replies once to all
three user messages. The final world and native database match all 1,007 IDs and timestamps,
seq/pts 1007 and no pending correlation. Original screenshots verify the visible chronological
suffix; complete structured evidence verifies the off-screen backlog. The APK and core are
unchanged. Full strict typing and lint/format pass; preceding core/package/Nix checks apply.
The expanded Android gate passes all 28 tests in about 21 minutes. Both interruption cases, all
three live-gap fixtures, native codec/formatting/runtime checks and consumer scenarios pass.
All current run/check handles are terminal. This is a passing integration checkpoint, not proof
that the earlier intermittent startup/send failures can no longer occur.

The preceding full 26-test gate stopped with three passed and one failed test: the composer
activity launch returned `Status: timeout`, and UIAutomator created no hierarchy file. It failed
before input. Eight subsequent minimal fresh-start trials pass, including five with a validated
method-stack diagnostic showing the main thread idle after a successful capture. These passes
do not identify or fix the intermittent startup cause. The earlier preference-sync stall, missed
commit and generic 503 also remain unexplained. Keep the ignored diagnostic and retained failure
evidence for another occurrence rather than adding speculative startup changes or input retries.

The earlier [live-gap correction](live-gap-recovery.md) restores the original periodic
`ConnectionsManager.onUpdate` independently of HTTP polling. Fresh ten-patch preparation at that
checkpoint matches the five Java inputs and preserves all 6,666 original UI/resource files.
Current fixture changes do not alter those inputs. Broader composer transformations, further
partial-write boundaries and concurrent native recovery remain open. The full goal and ticket
remain active.

The previous [acknowledgment-before-storage proof](ack-storage-recovery.md) passes an actual Android
interruption with the original storage thread held at ID-remap entry. The retained pending row,
receipt/frame correlation and split intermediate cursors recover once, followed by one real bot
reply. Its external debugger helper also passes a real JVM contract. No APK or production code
changed. The expanded Android gate passes all 24 tests, including both interruption cases and the
JVM helper. Strict typing across 48 core/probe files and three separate two-file examples, full
lint/format, Nix/workflow checks, local links in 81 Markdown files and public-tree privacy checks
pass. Core code is unchanged;
the previous 215-test core gate remains applicable. At that checkpoint all handles were terminal,
and the six-capture
report retains original UI evidence; browser layout review remains unverified.

Retain diagnostics for the intermittent startup failure, then continue remaining composer
transformations and additional recovery boundaries. The initial pre-storage
baseline attempt failed in the separate codec process and is not a valid red result at the new
boundary. Its crash trace identifies a local bridge connection timeout; Android's Binder error
occurred while reporting that crash. The earlier intermittent failures are not claimed fixed.
The older milestone records below are historical.
The [independent version 2 send boundary](client-sends.md) now has durable request receipts,
persona message positions and atomic version 4→5 migration. Seven initial failures establish
the missing contract; 53 focused tests and the full 186-test core gate pass, with 82.55% coverage.
The [native composer focused case](android-composer.md) now passes actual multilingual sends,
equal-text distinct sends, stale-draft rejection, cold restart and a committed send whose response
is withheld before client shutdown. The retained negative pending message reconciles once and a
real bot replies once. Compact acknowledgment and difference serialization checks also pass.
Fresh patch preparation preserves all 6,666 upstream UI/resource files. The full Android gate
passes 20 tests; it predates the [composer-text fixtures/probe](composer-text-references.md), which
then passes seven source-derived input cases in a separate actual Android test. The subsequent
[scenario composer](scenario-composer.md) adds explicit Start Bot and bounded typed input, an
independent text model matching those seven fixtures, and a passing shared simulation/Android
example with three original captures. Its core gate passes 215 tests at 80.99% coverage. The new
broader Android gate finishes with 21 passed and one failure in the older native interrupted-send
case: the intended send did not reach its controlled post-commit boundary. The new consumer case
passes again. Test-only missed-boundary diagnostics were added; a focused rerun passes unchanged,
so the failure remains intermittent and unresolved. The next trial fails earlier, before input:
activity startup times out and the retained ANR dump shows the main thread in a preference-file
sync. Do not conflate that distinct startup failure with the missed send. The final bounded trial
passes after toolchain preparation, again without a production change. These two focused passes
do not resolve either intermittent failure. Keep the targeted diagnostics for the next occurrence;
continue the unimplemented composer/recovery contracts without claiming a fully passing gate.
All current diagnostic, provisioning and preview handles are terminal. Both development profiles
are retained; the Android profile's closure includes the actual restored SDK executables.
The installed wheel's
offline composer example, strict typing, lint/format, Nix parsing, direnv syntax and local links
pass. The declared Nix checks, including Actionlint, now pass; all platform outputs also evaluate.
Only the host platform's checks were built. The
consumer report serves all three PNGs over local HTTP, but configured browser navigation still
returns `ERR_FAILED`; browser layout review remains unverified and the preview server is stopped.
Broader text transformations and further interruption boundaries
remain open. A screenshot
review traced the post-restart Seen checkmark to the original bot-history UI rule; it is separate
from unchanged database read state and is not a simulated read receipt. Preserve that renderer
behavior. The generated report's local HTTP check passes but browser navigation failed, so its
browser layout review is unverified. Ignored notes retain active handles and original evidence.

Continue the [programmable scenario workstream](../../.scratch/programmatic-scenarios/spec.md).
The [consumer runner](consumer-runner.md) now provides `gramlab run` and `python -m gramlab run`
with a TOML manifest, selected source/data files, private scenario/bot processes, named bot IDs,
timeouts and bounded redacted logs. Normal runs, assertion/bot failures, output limits and missing
runtime startup retain JSON/HTML evidence. Large HTML sections use explicit previews while JSON
retains complete state. The installed two-conversation example passes; desktop/mobile browser
inspection finds the actual conversation evidence, no layout overflow and no external resources.

The [scenario capture milestone](scenario-captures.md) connects the actual Android renderer to
that workflow. `Scenario.capture_chat` retains complete semantic history in both supported modes;
headless mode additionally verifies visible text and exports original PNG/UIAutomator evidence.
The same two-conversation example passes in both modes. Android assertion failure retains its
capture, and startup timeout produces a failed report. Guest startup belongs to the persistent
supervisor thread so repeated captures remain available.

The [inline-input follow-up](scenario-input.md) adds `Scenario.tap_inline_button` with message and
row/column targeting. Simulation creates the selected world callback; headless mode taps the actual
accessible button and verifies the callback from the client. The repeated-label example produces
identical final world/history state in both modes and original before/after PNGs. Captures and
input share one renderer lock. No automatic tap retries or synthetic Android fallback are used.
Response-loss tests verify a single committed callback; four concurrent virtual actors produce
64 distinct callbacks and share the explicit per-run input limit.

The final inline-input gate passes 147 core tests at 81.86% measured coverage and all 18 Android
tests. The Android collection predates one added core-only test; its deselection count is 146.
Ambiguous native targeting fails the run even if caught, without another callback, and retains
earlier screenshots. Full lint/format, strict typing across 44 files in two example-compatible
invocations, Nix/workflow checks, offline distributions and public-tree privacy/local links pass.
Desktop/mobile report review confirms loaded original captures and no external resources or
horizontal overflow. The approved APK fingerprint is unchanged. All run/check handles are terminal;
ignored `.cache/local-notes/inline-input.md` records local evidence and the stopped preview server.

The [bot lifecycle follow-up](scenario-lifecycle.md) adds generation-checked `bot_status`,
`stop_bot` and `start_bot`. Requests go through the persistent supervisor thread; replacements
keep their bot identity/capability and private files while receiving a fresh process namespace.
Per-generation process logs and accepted lifecycle actions remain in reports. An explicit stop
completes descendant cleanup; stale and concurrent requests cannot stop a replacement generation.
A real bot resumes the same callback after receipt and before acknowledgment, with equivalent
world/history/lifecycle results and original actual Android captures. Restarts share the run's
aggregate log budget. No APK or client-derived source changes were required.

The final lifecycle gate passes 151 core tests at 81.88% measured coverage and all 19 Android
tests. Full lint/format, strict typing across 47 files in three independent example-compatible
invocations, Nix/workflow checks, offline distributions and privacy/local links pass. Desktop/mobile
report inspection confirms original captures, lifecycle evidence and no external resources or
horizontal overflow. All handles are terminal, including the stopped report-preview server.
Ignored `.cache/local-notes/lifecycle.md` records the local artifacts and verification commands.

The [update-delivery milestone](update-delivery.md) adds persistent Bot API 10.3 subscriptions
and negative recovery offsets. Filters apply to future enqueueing, retain existing pending rows
and leave client history/events intact. Malformed filter values retain the selection while
ordinary acknowledgment proceeds. Storage version 4 preserves identities, capabilities, callbacks
and outboxes across concurrent migration. Negative offsets trim once before waiting; sparse-queue
and later-subscription tests protect against losing arrivals or overwriting a newer selection.
The pinned source review records remaining integer, conflict and distant-positive-offset differences.

The extended recovery example keeps a filtered user message visible in actual Android, delivers
the native callback without consuming an ID for that message, and resumes it after bot replacement.
The final gate passes 179 core tests at 82.16% measured coverage and all 19 Android tests. Android
collection predates two additional core-only tests and reports 177 deselected. Full static typing,
lint/format, Nix/workflow checks, offline distributions and privacy/local links pass. Both original
captures were inspected; desktop/mobile report review confirms loaded images and no overflow or
external resources. An initial guest-startup disk-space failure was resolved by deleting only
disposable images from completed runs, with their evidence verified unchanged. All handles are
terminal, including the stopped preview server. Local commands/artifacts and cleanup audit stay
in ignored `.cache/local-notes/update-delivery.md` and its referenced ledger. The APK is unchanged.

The parallel [composer reference review](android-composer-references.md) is committed and its
[research ticket](../../.scratch/programmatic-scenarios/issues/03-composer-references.md) resolved.
It identifies the pinned compact acknowledgment path, durable random-ID correlation, event/ack
ordering and pts obligations. Use it for the next native composer implementation; it does not
establish that text sends, pending-send recovery or new sequence translation already work.

Continue claimed ticket 02 with composer input, scrolling, interactive mode and the remaining
workflow acceptance. Client lifecycle controls, broader fault schedules and dependency packaging
also remain open. Preserve the private emulator component, authoritative world and original
renderer. Local capture evidence is recorded in ignored `.cache/local-notes/scenario-captures.md`.

The earlier capture milestone passed 138 core tests at 84.30% measured coverage and all 16 Android tests.
Full lint/format, strict typing across 41 files, Nix/workflow checks and offline distributions pass.
An explicit test-only tracing fixture measures real contained supervisor execution for selected
Python API tests; CLI and guest behavior checks do not imply additional line coverage. The APK
and upstream source patches are unchanged. All run/check handles completed.

Earlier control and SDK milestones established the following foundations; their test counts
below are historical.

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

Ticket 01 is resolved; consumer-runner ticket 02 remains claimed for composer input, interactive mode and
the remaining workflow acceptance. Selected file packaging, simulation/headless execution,
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
expiry, webhook coordination and production flood timing remain open. The later
[delivery follow-up](update-delivery.md) implements filters and negative offsets and records
source-identified conflict and positive-offset differences.

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
