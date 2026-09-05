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
and all thirteen process/guest tests (90.91% coverage). Native compilation now proceeds inside
containment. No client runtime success is claimed; continue the live offline rebuild and full
client/world/bot gates. Machine-specific build records remain ignored.
