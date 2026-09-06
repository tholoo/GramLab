# Android runtime provisioning provenance

The user approved the scoped Android prototype on 2026-09-05. These are portable package inputs,
not host inventory, a working APK or proof of an isolated scenario. Versions are declared in
[toolchain.json](../../clients/android/toolchain.json); nixpkgs is pinned by the project flake lock.

## Primary metadata

The [official emulator archive](https://developer.android.com/studio/emulator_archive) identifies
Emulator **37.1.11 Stable**, dated July 30, 2026, with Linux archive
`emulator-linux_x64-15917651.zip` (334378080 bytes) and published SHA-256
`95771e0ae431897b2a4bd2d97fa095f29a8b0624a7b216baf529f9306161c266`.

Google's [system-image metadata](https://redirector.gvt1.com/edgedl/android/repository/sys-img/android/sys-img2-3.xml)
identifies `system-images;android-36;default;x86_64`, revision **2**, extension **17**, base extension,
stable channel, minimum emulator **35.4.9**, and `android-sdk-license`. The archive is
`x86_64-36_r02.zip` (844217077 bytes), with published SHA-1
`829c076e8ff448a336097ae25a355b495ba36e2c`. The XML does not publish an image SHA-256;
the acquired archive's computed SHA-256 is
`e1b9d9fb665001ef27b16e57d8762a2d54aec6bff617e17506edb8676667b9da`. This is an observed binary
hash, not an independently published one. The acquired emulator archive matched the published
SHA-256 above; both archive sizes matched the metadata.

| Component | Pinned version | Archive |
| --- | --- | --- |
| SDK platform | API 36, revision 2 | `platform-36_r02.zip` |
| Build tools | 36.0.0 | `build-tools_r36_linux.zip` |
| Command-line tools | 22.0 | `commandlinetools-linux-15859902_latest.zip` |
| NDK | 27.2.12479018 | `android-ndk-r27c-linux.zip` |
| CMake | 3.22.1 | `cmake-3.22.1-linux.zip` |

These toolchain entries were corroborated against Google's
[SDK metadata](https://redirector.gvt1.com/edgedl/android/repository/repository2-3.xml).
The command-line tools filename contains `latest`, but its build number and checksum are pinned;
the flake does not resolve a floating latest version. Platform-tools **37.0.1** is selected from
the pinned nixpkgs metadata as a separate package.

Direct `dl.google.com` metadata requests returned HTTP 404 during research. The official emulator
archive links to `redirector.gvt1.com/edgedl/android/repository/`; that CDN also served valid SDK
and system-image XML. The flake uses this explicit official base URL, retaining the immutable
archive names and checksums. No machine-specific proxy is embedded in the repository.

Observed metadata-document SHA-256 values (not binary checksums):

| Document | SHA-256 |
| --- | --- |
| SDK XML | `fc2503ca74b0b098fa1668619ff195c0dd118b722e1680bc7c822be4b3f2276a` |
| System-image XML | `ab70efed53b5c289035fb6b3b552b22ad6e04eeab2d58e0e6edcc9ce3640bfad` |
| Pinned nixpkgs Android `repo.json` | `b07bbadf6ce89f5efc1cd9eb7c4fde0d0d4ce411cb6bd367b430d99d687578d1` |

## Reproducibility boundaries

The pinned [nixpkgs Android recipes](https://github.com/NixOS/nixpkgs/tree/9387b3fcc0c23c86661636da63faabad4235a0a6/pkgs/development/mobile/androidenv)
patch ELF loaders/library search paths for Nix and assemble SDK package metadata. Those recipes
are provisioning inputs; they do not alter Telegram's chat renderer or certify guest behavior.
The package selection was evaluated without constructing a VM. Actual package realization and
runtime smoke results must be recorded separately.

Keep public version/hash/build conclusions here and host/proxy/device observations in ignored
`.cache/local-notes/` or run artifacts. Display, fonts, WebView, language resources and animation
policy still need a tested fidelity profile before any UI compatibility claim.

## Provisioning verification

The source checkout and ten top-level submodules match the approved commits. The
[source lock](../../clients/android/upstream-lock.json) records root license/notice hashes and
13 x86_64 native archive inputs used by upstream CMake. These are pinned upstream prebuilts;
rebuilding each from source and completing the dependency/asset license audit remain outstanding.
In particular, the upstream tde2e README gives an unpinned TDLib clone command, so that instruction
alone does not establish the source revision corresponding to its checked-in archives.

The Android SDK package was realized through the flake. Isolated tool-version smoke checks
confirmed JDK 17, emulator 37.1.11, command-line tools 22.0, CMake 3.22.1 and the packaged `aapt2`.
The default shell and actual direnv entry confirmed Python 3.13.15, uv 0.12.5 and project-local
cache/environment paths. Nix formatting, direnv and workflow lint checks passed, along with all declared platform
evaluations; locked Python provisioning and Ruff lint/format passed. These initial checks did
not start an emulator. The subsequent guest validation is recorded below. CI has only been
validated locally, not dispatched.

Gradle remains the upstream wrapper version 8.11.1. Its
[published distribution checksum](https://services.gradle.org/distributions/gradle-8.11.1-bin.zip.sha256)
is recorded in the profile; Gradle/plugin dependency provisioning and offline APK compilation are
subsequent build gates, not covered by the SDK tool smoke checks.

## Dedicated guest validation

On 2026-09-06 the [process-boundary suite](runtime-boundary.md) passed twelve combined tests,
including the actual emulator, explicit KVM access and a newly created AOSP guest. The guest
reported API 36/x86_64, build fingerprint
`Android/sdk_phone64_x86_64/emu64x:16/BE2A.250530.026.D1/13818094:userdebug/test-keys`,
and zero accounts. Local TCP through the emulator's guest alias succeeded; external IPv4/IPv6
documentation-address attempts were rejected as unreachable. Its containing network namespace
had only loopback. A captured screenshot was inspected and showed the AOSP launcher.

This used the pinned image with KVM, SwiftShader and private run data; see the boundary record
for commands, preparation display/memory settings and diagnostic limitations. Generated AVDs,
logs, timing observations and screenshots remain ignored. No Telegram client, local bot,
semantic bridge or world implementation has been executed or verified by this guest preparation.


The subsequent [transport correction](android-transport-reliability.md) selects the same pinned
emulator's built-in Virtio Wi-Fi forwarding with `-feature -WiFiPacketStream`. The toolchain records
`wifiPacketStream: false`; both launchers apply the flag. Emulator/image versions and containment
remain unchanged. All seven runtime checks pass with that selection, including actual guest local
reachability and external IPv4/IPv6 rejection. Four additional focused composer/codec checks pass;
the full Android gate remains incomplete because of an activity-startup timeout before input.
