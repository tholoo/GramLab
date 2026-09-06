# Recover older Android history after downtime

The seventh [GPL patch](../../clients/android/patches/README.md) refreshes every message supplied
by the authoritative startup snapshot through the pinned client's existing history-storage API.
This addresses stale older messages after a bot edits them while Android is stopped. The existing
dialog startup path refreshed only the newest message. The client database remains a cache of the
world; startup retains it and applies the snapshot before opening the chat.

## Reconciliation boundary

The [semantic snapshot](client-bridge.md#snapshot-and-cursor-contract) already contains the complete
private-chat history and a consistent world journal position. Java translates it into newest-first
per-peer histories. After the existing `putDialogs` call, `GramLabRuntime.installPersona` submits
each history to upstream `MessagesStorage.putMessages`, using `LOAD_AROUND_MESSAGE`, zero offset,
default chat mode and no new-dialog creation. This uses the same storage path and hole handling
as loaded history. The existing storage-queue barrier waits before starting live event polling.

The patch changes only the adapter runtime class. It does not modify `MessagesStorage`, message
cells, fonts or resources, and does not delete or replace the application database. World/persona
binding checks still run before installing the persona or touching its cache. Events after the
snapshot cursor remain eligible for the existing event worker; journal positions are never used
as Telegram `pts`/`seq` values.

This is repeatable startup resnapshotting, not a durable client command log or an atomic transaction
covering all dialogs and their cursor. Upstream storage performs its own per-history transactions.
A later cold start reapplies a fresh snapshot. Storage-error recovery, deletion/tombstone handling,
participant removal, partial bot mutations and interruption at every replica write remain open.
Snapshots remain unpaginated, with the adapter's existing 8 MiB transport bound. This change does
not establish large-history performance or new media support.

## Real regression scenario

The independently written [bot fixture](../../tests/fixtures/recovery_bot.py) communicates only
through the local Bot API HTTP boundary. The
[shared scenario](../../tests/probes/recovery_round_trip.py) uses seed 7 and explicit world time:

1. A virtual user sends `Check recovery`. The bot sends `سلام — original` with an inline button,
   followed by `Previously newest`. The actual chat displays all three messages and the button.
2. The dedicated client is force-stopped. The bot edits its older reply to `سلام — corrected 😀`,
   adds bold formatting, removes the inline keyboard and sends `Sent while away` as a newer reply.
3. The client cold-starts against its existing data. The chat must show the corrected older text,
   formatting and keyboard removal together with both newer replies, each exactly once.
4. A second cold restart repeats those assertions. Bot responses, exact final world history and
   the acknowledged empty update queue must match the simulation-only scenario.

The six-patch baseline fails step 3: the newly sent message appears, but the older text and inline
button remain stale. The persisted world already contains the corrected message, proving the
mismatch is in Android recovery. Both the initial and failed restart screenshots were inspected.
The test retains its real HTTP exchange before attempting recovery so a UI failure does not lose
the corresponding bot evidence. Expected semantic outputs are authored independently of the
adapter and compared as complete structures.

The seven-patch client passes the focused recovery case across both cold restarts. Screenshots
show the corrected bold text, absent keyboard and all four messages without duplication. An initial
assertion looked only at accessibility descriptions; the inspected client exposes message strings
through UIAutomator's `text` attribute. The assertion now counts each node once across both fields,
retaining the exact-once requirement. The independent simulation-only case has the same complete
semantic outputs. All 66 core tests pass at 91.56% statement coverage; strict typing and lint/format
pass. Fresh seven-patch preparation reproduces the Java inputs and strict dependency metadata and
preserves all 6,666 checked upstream UI/resource files byte-for-byte. The contained offline build,
APK v1/v2 signatures, restricted manifest and x86_64 native library checks pass.
The full Android gate passes all thirteen tests, including existing network/native rejection,
wrong-world startup, callbacks and formatting, and the new recovery scenario. The final repeated
restart screenshot was inspected. Nix/direnv/workflow, local-link and public-tree privacy checks
pass. This remains local model and actual renderer evidence; no external conformance is claimed.

The fidelity profile remains Telegram Android 12.10.1 at
`62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`, TL layer 229, Emulator 37.1.11, AOSP API 36 default
x86_64 revision 2, `swangle`, 320×640 at 160 dpi, default client theme/fonts and English client
locale with mixed Persian/English message content. See the [callback profile](android-callbacks.md)
and [component boundary](component-boundary.md). The guest has synthetic app state and zero Android
accounts. World time is explicit; guest clocks and animation timing remain nondeterministic.

## Reproduction

Prepare/build the full patch queue using [the contained build procedure](android-build.md), then
set `GRAMLAB_ANDROID_PROBE_APK` to the resulting local APK. Run in the independent outer guard:

```sh
nix develop .#android --command unshare --user --map-root-user --net bash -eu -c '
  ip link set lo up
  test ! -e artifacts/android-history-recovery
  .venv/bin/pytest tests/test_android_recovery.py --basetemp=artifacts/android-history-recovery
'
```

The test retains `before.png`, `recovered.png`, `repeated.png`, UI XML, guarded adapter/logcat
diagnostics and the synthetic bot/world transcript under its ignored directory. Use `-m android`
for the full guest/client gate and the separate core/coverage/static checks from
[CONTRIBUTING.md](../../CONTRIBUTING.md). Run the simulation-only case with `tests/test_recovery.py`
in the same outer guard and the core development shell. Local paths, process handles and artifact
hashes belong in ignored local notes. No host service change, external runtime traffic, real
account or remote publication is involved.
