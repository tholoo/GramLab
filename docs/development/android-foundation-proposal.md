# Approved Android foundation prototype

Status: approved for the scoped feasibility prototype; process/guest preparation, contained APK
compilation and a [local world/bot exchange](world-bot-prototype.md) are implemented. The client
activation/bridge remain pending. Prepared 2026-09-05 for
[ticket 01](../../.scratch/android-offline-foundation/issues/01-validate-android-seam.md).
This proposes the next feasibility work within the full product objective. It does not replace
the foundation acceptance criteria or the broader compatibility backlog.

## Evidence and recommended choices

The [source investigation](android-source-feasibility.md) identifies a candidate pinned client,
toolchain, rendering/callback paths and initialization hazards. The
[host investigation](android-host-feasibility.md) confirms accessible KVM and a disposable
network namespace with local TCP and rejected external IPv4/IPv6 documentation destinations.
Neither establishes a working Android build or renderer.

| Approved choice | Selection | Tradeoff and proof required |
| --- | --- | --- |
| Client baseline | Telegram Android commit `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`, version 12.10.1, TL layer 229; separate offline application build and reviewable patch queue | Current candidate has native/build complexity; build and actual UI loop must prove applicability |
| Runtime | One dedicated x86_64 Android Emulator, AOSP API 36 image, KVM and explicit software GPU; project-scoped provisioning | Emulator 37.1.11 and API 36 default x86_64 image revision 2 are pinned in the toolchain profile; measure boot/rendering before expanding the pool |
| Bridge and provenance | Independently specified semantic JSON messages over authenticated local HTTP; Java adapter owns conversion to/from upstream TL objects | More explicit mapping work, but no upstream-generated TL types in the Python core; IPC does not itself resolve distribution licensing |
| World and recovery | One SQLite database per world with transactional state, ordered events and an update-delivery outbox; explicit world clock and seed | Serializes writes initially; transaction/replay invariants must survive interruption; not a public persistence API commitment |
| Execution isolation | Per-run network namespace containing emulator, bot and simulator; loopback only, plus mount/process isolation and endpoint allowlists | Host mechanism works in a small probe; guest routing, inherited sockets and every network-capable subsystem still need independent tests |

Source/generated schema code and patches remain within the client copyleft boundary. Only
original protocol descriptions and independently implemented domain/Bot API behavior enter the
MIT core. Do not generate Python classes from the client's TL generator. Record per-file,
submodule and asset licenses before acquisition/adaptation; distribution review remains separate.

## Scoped prototype after review

Acquire the selected source and development dependencies in a separate provisioning step. Keep
an unchanged ignored checkout and reviewable client patches. Record exact package revisions,
checksums, licenses and commands before a build; SDK downloads and Gradle resolution are allowed
only during provisioning. The run environment receives cached inputs and no external route.
No system service change is part of this proposal. If NixOS requires one, present the exact
change separately before applying it.

Build a dedicated offline app with distinct package/branding, synthetic-only app-private data,
local signing material and no account login. Retain upstream native libraries needed for text,
media and storage. Disable native networking initialization and outgoing native request paths
explicitly in the offline build, covering all initialized account slots and background paths.
Populate the synthetic self user and a bot dialog through the upstream configuration/storage and
controller boundaries identified in the source report. Unsupported client RPCs return a visible
failure with method/trace evidence; never silently fall through to native transport or invent
success to make startup appear healthy. Some upstream recovery paths retry generic errors, so
trace and support the required update-state/difference contract; terminate the scenario with a
clear capability failure for an unsupported required path rather than leaving a retry loop running.

Keep a single world authority in Python. The prototype bridge carries world/persona identity,
request correlation, ordered events and explicit error results, not arbitrary TL-serialized
objects. A per-run capability authenticates bridge and control access; a world ID alone is not
an authorization credential. Map the minimum proven startup/history/message/callback/edit
operations in Java while preserving controller update processing and actual message-cell/button
rendering. Maintain request cancellation, callback completion and expected queue/thread behavior.
Do not freeze a public SDK or bridge schema before the real loop succeeds.

Use a real bot process against the local Bot API HTTP endpoint. Start with polling and the exact
methods the scenario uses (identity, updates, message send, callback answer and message edit).
The compatibility profile lists that subset explicitly under the selected Bot API specification;
all other methods fail visibly. Propose Bot API 10.3 as the named specification baseline, as
documented in the source investigation, without claiming coverage beyond the explicit subset.
This ordering follows the agreed first milestone and leaves the
full webhook/API/language/media/Mini App inventory intact.

For recovery, commit world state and outgoing events atomically. Preserve stable semantic IDs,
update offsets and callback identities. Reconnect the client using an event cursor or resnapshot
when its cursor is unavailable, with a defined duplicate policy. Treat the client's SQLite data
as a renderer cache, not a second world authority. Preserve bot state separately in the owned run
directory; test bot and client restarts independently. The initial replay contract covers semantic
state and delivered updates; do not promise deterministic Android frame/animation timing.

A bridge journal cursor is not the client's Telegram update cursor. The adapter must map world
events to per-persona `pts`, `seq`, `date` and `qts`, with supported `updates.getState`,
`updates.getDifference` and history contracts. Preserve the client's database on restart and test
reconciliation against the journal; any resnapshot must establish a consistent versioned client
state rather than inject messages around the controller's gap checks.

## Required proof before broad expansion

1. Provision and build the pinned client reproducibly; record patches, submodules, native inputs,
   toolchain, resulting APK hash and complete display/runtime profile. Prove failed isolation
   prevents client/bot startup, and prove no account/login path is used.
2. Create a synthetic persona and chat; send a command to the real local bot. Assert full HTTP
   request/response/update contracts and correlate the resulting world message with the actual
   Android chat. Capture the upstream rendering and semantic IDs.
3. Inspect UI structure and screenshots, tap the actual inline callback button, and assert the bot
   receives the correct actor/chat/message/data. The bot answers the callback and edits the same
   message; verify state and Android rendering agree. Include stale/duplicate/wrong-actor cases.
4. Interrupt and restart the bot and client at meaningful delivery boundaries. Verify persisted
   state, duplicate policy and event ordering. Start a second world and prove no cross-world
   state, capability, media or update delivery leakage.
5. Repeat the supported semantic scenario in simulation-only and Android modes and compare final
   state and ordered effects. Add Persian/English mixed text, RTL/LTR and a rich-message/media/
   custom-emoji exploration case with original local assets. Unsupported behavior must remain
   explicit and visible in the report and matrix.
6. Test IPv4, IPv6, DNS, redirects, WebSockets, native transport, media, WebView and background
   services from the relevant guest/process contexts. Record allowlist rejections, namespace
   membership/routes and independent traffic evidence; demonstrate attempts are contained.
7. Preserve run ID, seed, pinned versions, traces, screenshots, restart points and limitations.
   Continue into concurrent programmable scenarios, fault scheduling, broader versioned API
   coverage, previews, latency diagnostics and HTML reports through the existing tickets.

For behavior changes, demonstrate a failing boundary test first when fixing a bug, then run
focused and applicable full checks from TESTING.md and CONTRIBUTING.md. Android evidence is a
separate gate; simulator tests cannot substitute for it.

## Remaining uncertainties

- The [runtime boundary](runtime-boundary.md) now has dedicated AOSP boot/local/external-network
  evidence. No offline Telegram build, tap, bot loop or replay has run.
- Runtime package metadata is resolved in the [provenance record](android-runtime-provenance.md).
  Emulator/image acquisition, checksum checks and dedicated guest boot passed. The Telegram
  rendering profile remains unverified.
- The source report identifies required paths but does not prove the complete startup RPC set,
  callback thread semantics, native bypass, rich-message mapping, or local font/media behavior.
- The Android image's language assets and upstream locale filtering must support the Persian
  profile without network language-pack downloads.
- A separate package and IPC boundary do not establish that any future combined distribution is
  MIT-only. No publishing or distribution is proposed here.

Approval recorded 2026-09-05: the user approved this Android proposal and authorized using
the session-provided local proxy for network problems during provisioning. The user also requested a
high-quality project `flake.nix` and `.envrc`. This authorizes the scoped client/runtime, semantic
bridge, SQLite persistence, isolation prototype and project-local source/dependency provisioning.
Normal runs still require zero external egress. Consequential changes beyond these choices,
host service changes and publication retain their existing review requirements.
