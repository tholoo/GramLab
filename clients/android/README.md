# Android client integration

Target: a pinned, minimally patched build of [Telegram Android](https://github.com/DrKLO/Telegram),
with real upstream UI/controllers and a dedicated local simulation bridge.

An offline real-bot/original-Android loop now runs through the public consumer runner. The reviewed
30-patch normal30 build has passed an explicit bridge-v5 workflow containing a forced ordinary
document, original inline-button input, callback handling, stable-file reuse and repeated original
client launches. Earlier focused gates cover text, formatting, rich messages/buttons, photos and
custom emoji on their recorded APK checkpoints. This is not completion of the operational
milestone: albums, rich-detection native codec acceptance and the complete current-APK regression
remain open. Read the [compatibility matrix](../../docs/compatibility/matrix.md)
before generalizing from a focused result.

Patch 0031 is source-complete but not yet represented by that retained normal30 APK. It projects
the approved detector's metadata-free mention, hashtag, cashtag, bot-command and bank-card nodes
through their original `TL_iv` constructors and extends the strict serializer probe. A collected
Android case covers the five projections; compilation and guest execution remain coordinator-owned.

The approved source and its pinned submodules live in ignored `upstream/`. The
[patch queue](patches/README.md) and [preparation script](prepare.py) export only pinned tracked
files to a new dedicated build tree, sanitize upstream credential templates, install strict
dependency verification metadata and apply all 31 patches in `series` order. Preparation itself
does not fetch dependencies, build an APK or run a client. See the current source, build and local
artifact boundaries in the [Android build record](../../docs/development/android-build.md).
See [source provenance](upstream-lock.json), the
[toolchain profile](toolchain.json), and [development setup](../../docs/development/environment.md).
This directory's original notes are MIT; acquired/adapted Android code and
patches must carry their applicable upstream terms. See [licensing](../../docs/development/licensing.md).

Run the checked-in [echo example](../../examples/README.md) with its `android.toml` manifest,
`--bridge-version 5` and `--android-apk` pointing to a locally reviewed compatible APK. The
repository intentionally contains no APK release, download URL or portable local APK path. The
runner requires a fresh dedicated AOSP guest, synthetic identities, zero Android accounts and the
documented independent network containment; it never attaches to a personal device or downloads
runtime inputs. Simulation mode uses the same scenario and semantic state without claiming Android
rendering. `interactive-android` remains unsupported.

Do not acquire or update upstream source without approval. When an approved checkout is present,
its root and ten submodules must match `upstream-lock.json`; never silently track master, reuse real
sessions or ship upstream release keys. Keep ordered, reviewable adaptations in `patches/` and
re-export from the pinned base rather than editing the acquired checkout.

Use distinctly unofficial GramLab branding without changing the in-chat rendering contract.
The supported evidence profile is the pinned API-36 x86_64 emulator described by the build/runtime
records. Waydroid is not a supported or tested runtime; evaluate it separately if useful on a host.
