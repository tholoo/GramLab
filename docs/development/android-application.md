# Synthetic Android application startup

The fourth [GPL patch](../../clients/android/patches/README.md) connects the authenticated
[semantic adapter](android-semantic-bridge.md) to the actual Telegram application. A real local
bot's Persian/English reply renders in the unchanged upstream `ChatActivity`, with both incoming
and outgoing bubbles. This is the first rendered conversation, not the complete interaction loop.

## Startup and transport

The supervisor installs the distinct GramLab debug package into a fresh, contained AOSP guest.
It writes `files/gramlab/config.json` through `run-as` stdin with the bridge endpoint, generated
client capability, world ID and persona ID. The configuration is never an activity argument or
log entry. This is a trusted test supervisor interface, not a public runtime CLI.

`ApplicationLoader` fetches and validates the initial snapshot before normal client startup.
An atomically written private binding records the world/persona. Subsequent launches must match
both before the client cache is read. Missing configuration and a valid configuration belonging
to another world are rejected with static diagnostic reasons; exception causes and capabilities
are omitted. Account zero receives the synthetic TL identity without phone login or a native
transport session. Existing controller and storage APIs populate the initial peer/dialog cache.

The Java `ConnectionsManager` seam dispatches the currently supported reads on a worker and
delivers completion on the existing stage queue. Request IDs and GUID binding/cancellation are
retained; unsupported RPCs return an explicit `501 GRAMLAB_UNSUPPORTED_<class>` error. The read
subset is `messages.getDialogs`, private `messages.getHistory`, `users.getUsers` and
`users.getFullUser`, with bounded query shapes. It is not a complete implementation of those
methods. No request falls back to native Telegram transport. Client clock queries use world time;
the guest system clock, UI animation scheduling and wall-clock deadlines remain separate.

Push initialization, account-sync registration, billing, proxy rotation, DNS fallback and cloud
challenge callbacks are disabled at startup/transport seams. The final manifest exposes only the
existing launch activity, with no providers, services, receivers or aliases. Its four permissions
are Internet, network-state access, wake lock and vibration. Backup is disabled. Cleartext is
allowed only for the numeric local bridge addresses; the bridge itself restricts endpoint and
port, disables proxies and redirects, and authenticates every snapshot.

The [JNI guard](android-native-guard.md) and independent [process boundary](runtime-boundary.md)
remain mandatory. Android's network-security XML does not provide general egress isolation.
Media, WebViews and other direct Java networking surfaces still need feature-specific audits and
tests before those features are supported.

## Behavioral evidence

The [application probe](../../tests/probes/android_application.py) starts a separate real bot
process against local HTTP, then opens the actual launch activity with the bot's peer ID. It
observes accessibility text and captures the real screen. No message view or image is injected
into the client. The scenario uses the pinned API 36 x86_64 AOSP guest, a 320×640 viewport at
160 dpi, upstream default theme/fonts and English client UI with Persian/English message text.
Capture waits for the message's accessibility node; animation timing is not normalized.

The disabled baseline could not launch its activity. The first enabled build rendered both
messages but incorrectly retained “Start Bot”: the initial cached history was empty when
`ChatActivity` inspected it. Populating Telegram's normal dialog cache before opening the chat
fixes the regression without changing the renderer. The reviewed screenshot shows the normal
message composer and both bubbles.

The lifecycle regression also exercises force-stop/relaunch, missing configuration, a different
world with valid credentials and the same numeric persona ID, and restoration of the original
configuration. It checks one visible bot reply, unchanged authoritative history, zero Android
accounts after launch, and explicit rejection traces. Test evidence and guest data remain in
ignored artifacts. Diagnostic text is checked for capabilities before writing; the private guest
data retains its configuration for restart and must be treated as sensitive run data.

Run after a [contained build](android-build.md), using a fresh artifact directory:

```sh
nix develop .#android
export GRAMLAB_ANDROID_PROBE_APK=.cache/android-build/offline/source/TMessagesProj_GramLab/build/outputs/apk/debug/TMessagesProj_GramLab-debug.apk
unshare --user --map-root-user --net bash -eu <<'BASH'
ip link set lo up
test ! -e artifacts/android-application-01
.venv/bin/pytest tests/test_android_application.py --basetemp=artifacts/android-application-01
BASH
```

Run the complete Android gate with `pytest -m android` under the same containment and a fresh
artifact directory. Keep builds and guest tests sequential to avoid competing for resources.
Missing KVM/profile/APK is unavailable coverage. This probe uses its dedicated emulator serial
only; it never attaches to a personal device.

## Remaining scope

Client writes, live update delivery, Telegram `pts` reconciliation, inline-button tap/callback,
bot edits and interrupted mutation recovery remain unimplemented. The world journal cursor is
not used as `pts`. Read receipts, presence, bot commands and broader dialogs/history pagination
are not modeled. Unsupported startup queries remain visible as errors, including sticker/config
queries. Request cancellation races and sustained-load behavior still need focused evidence.

The tested restart is force-stop/relaunch with persistent data, not arbitrary power-loss or
in-flight write recovery. Full source/dependency/license and distribution readiness remain open.
The first end-to-end milestone stays active until the real tap/edit/recovery loop is proven.

## Verification record

On 2026-09-06 the final Android gate passed all seven tests (27 core tests excluded). The
application case checks three cold launches with both messages, no duplicate reply, the ordinary
composer, zero Android accounts and both startup rejection reasons. The first rejection baseline
failed while writing a trace into a missing directory; that diagnostic failure is fixed. Android
may keep a failed process for its crash dialog, so the assertion checks the fatal startup error
and final rejection trace rather than assuming immediate PID removal. The probe then force-stops
its dedicated package. A concurrent build/guest attempt hit the boot deadline; final guest tests
ran after compilation completed.

The latest core gate passed 27 tests with 90.72% statement coverage; core behavior is unchanged by
this patch. Python lint/format and strict typing, Nix/direnv/workflow checks, local links and
public-tree privacy checks pass. A fresh four-patch export matches all six startup inputs and
strict dependency metadata, preserving 6,666 checked upstream UI/resource files byte-for-byte.
The contained offline build completed, v1/v2 signatures verify, and the binary manifest and
x86_64 libraries were inspected. The observed local APK has SHA-256
`a123bc68f9fea6c4b27aa2c9d9a9bbe9a0a07316d95597789e047f81a2a63df4`.
This identifies test evidence, not a reproducible release artifact or distribution approval.
