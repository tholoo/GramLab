# Android semantic snapshot adapter

Status: a real local bot reply reaches the Android-side adapter over authenticated HTTP and is
converted into the pinned client's TL dialog/history objects. The fourth patch now connects this
adapter to [synthetic application startup and rendering](android-application.md). The evidence
below describes the earlier standalone translation probe.

The third [GPL patch](../../clients/android/patches/README.md) adds `GramLabBridge` to the shared
client module. All TL conversion stays inside that boundary. Python continues to expose the
independently owned [semantic read protocol](client-bridge.md), with no upstream schema dependency.

## Transport and projection

The trusted supervisor supplies an endpoint, generated client capability, expected world ID and
persona ID. The adapter accepts explicit HTTP ports on the emulator host alias or numeric loopback
only. It disables proxy discovery, redirects and HTTP caching, applies connect/read timeouts, and
caps a snapshot response at 8 MiB. Other HTTP statuses fail explicitly without interpreting them
as state. A larger world requires pagination work; responses are never silently truncated.

The response must match wire schema 1 and the configured world/persona. Unknown fields, unsupported
chat types, duplicate identities/messages, missing participants and invalid integer ranges fail.
Message IDs and timestamps must fit the client's positive/nonnegative signed 32-bit fields;
world IDs, participant IDs and journal cursors retain their separate meanings.

| Semantic value | Client projection |
| --- | --- |
| Persona and its bots | `TL_user`, with self/bot flags, names, optional username/language and empty local photo/status |
| Private conversation | `TL_dialog` whose peer is the bot; a separate map retains the internal world conversation ID |
| Outgoing persona message | Sender is the persona, recipient is the bot, `out=true` |
| Incoming bot message | Sender is the bot, recipient is the persona, `out=false` |
| History | `TL_messages_messages`, newest message first, with the two participant objects |
| Dialog list | `TL_messages_dialogs`, containing each dialog's latest message and visible users |

Synthetic access hashes are zero; no phone, account session or production credential is imported.
The journal cursor is carried separately and is not assigned to Telegram `pts`. The current
snapshot does not implement read-state transitions, update reconciliation or client writes.
The fourth patch adds a limited read RPC dispatcher. Per-conversation message IDs are retained; broader private-account lookup contracts
still need evidence when the request adapter is connected.

## Real guest evidence

[`android_client_bridge.py`](../../tests/probes/android_client_bridge.py) creates a world with Sara,
an Echo bot and a hidden conversation for Bob. A separate bot process receives mixed Persian/English
text, replies through the real local Bot API and acknowledges its update. The guest then fetches
Sara's snapshot with its own capability file. The file is removed after use; capabilities are
checked against stdout/logcat before evidence is written.

The APK's `BridgeProbe` runs through `app_process`, without installation or lifecycle startup.
It constructs the upstream `ApplicationLoader` test context solely to select the existing AppTests
serialization mode, which omits local attachment-path extensions. It does not call `onCreate`,
initialize providers or activate an account. Complete TL dialog/history responses are serialized
and decoded with the pinned client classes before their values are compared with the scenario's
expected identities, direction, order, timestamps and text. This is TL translation evidence, not
a screenshot/rendering or production-wire conformance claim.

The baseline probe failed with `GRAMLAB_SEMANTIC_BRIDGE_UNIMPLEMENTED`; the implemented round trip
passes. Additional real HTTP cases exercise wrong world/persona, another world's capability,
external endpoint rejection and refusal to follow a local redirect to an otherwise valid snapshot.
Run the complete Android gate after the [contained build](android-build.md):

```sh
nix develop .#android
export GRAMLAB_ANDROID_PROBE_APK=.cache/android-build/offline/source/TMessagesProj_GramLab/build/outputs/apk/debug/TMessagesProj_GramLab-debug.apk
unshare --user --map-root-user --net bash -eu <<'BASH'
ip link set lo up
.venv/bin/pytest -m android --basetemp=artifacts/android-bridge-01
BASH
```

Use a fresh ignored artifact directory; pytest removes an existing base directory. Missing KVM,
runtime profile or APK is unavailable coverage, not a passing bridge test. The native transport
guards and independent OS containment remain required. This standalone probe does not establish
rendering, callback, edit or restart recovery; see the separate application evidence.

Verification on 2026-09-06: all six Android tests pass (27 core tests excluded), including the
existing JNI request/init guards and guest networking checks. The new probe returns the expected
TL projection with no pending bot updates and exact errors for all five rejection cases. A fresh
three-patch export matches the adapter inputs, preserves the dependency checksum record and keeps
all 6,666 checked upstream UI/resource files byte-for-byte unchanged. Retained probe output and
logcat contain no capabilities. Static/Nix/workflow, local-link and public-tree privacy checks pass.
The inspected APK has SHA-256
`3c9df7e10917e745753c5552123789311609797e396c57a04ff947b67ad14691`; its v1/v2 signatures verify
and its binary manifest keeps application and backup disabled. This identifies the observed
local build, not a reproducible release artifact or distribution approval.
