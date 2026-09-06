# Native composer and interrupted send recovery

The pinned actual Android composer now sends ordinary text through the
[durable version 2 bridge](client-sends.md). The focused guest case passes: one ASCII send,
two equal Unicode sends, real bot replies, cold restart and a send interrupted after the world
commits but before Android receives its acknowledgment. This does not complete the scenario
composer API, the full Android gate or every interrupted replica-write boundary.

## Implementation boundary

[Patch eight](../../clients/android/patches/0008-native-composer-and-client-sequences.patch)
keeps the original composer, send helper, controller, storage and renderer. Its GPL adapter
maps ordinary `messages.sendMessage` to authenticated semantic sends and returns the pinned
compact acknowledgment with the accepted message ID, date, entities and persona message position.
Unsupported flags, media, replies, scheduling and alternate senders fail explicitly before a
world mutation. The ordinary self `send_as` field populated by the pinned client is accepted.

Persona message positions drive `pts` and `seq`; callbacks, clock changes and other personas'
messages do not consume them. Live delivery uses a fresh full updates envelope for each position.
An active local send holds its envelope and later positions until the original acknowledgment
handler's UI/storage/UI completion fence. State and bounded difference responses use the same
positions. This is the approved semantic translation, not an MTProto server.

On restart, authoritative history is stored before opening the chat. Accepted receipts reconcile
negative pending message IDs using the original random ID **and destination**. The same-package
GPL seam calls the stock storage remap and completion paths; it does not insert synthetic pending
rows or clear the retained application database. Cursor persistence completes before startup is
released. Projection preserves acknowledged outgoing read state rather than inventing a peer
read receipt at restart. General read receipts and presence remain unimplemented.

The original shell helper carries bounded UTF-8 JSON over stdin, connects to Android accessibility,
checks the foreground package and unique editable node, verifies the expected draft, sets text,
verifies the exact resulting text, and clicks the original Send control once. Read-only readiness
waits do not retry an input action. The custom empty-hint predicate and its limitations are
documented in the [input source review](android-input-tooling-references.md). This is dedicated
guest automation; it is not a general concurrent desktop input API.

## Verified behavior

The [actual guest test](../../tests/test_android_composer.py) checks:

- Persian, ZWNJ, a combining accent, an emoji sequence and multiline text survive actual composer
  input. Repeated equal text produces distinct accepted messages and durable request IDs.
- A literal `Message` draft at cursor zero is rejected when empty input was expected. Explicitly
  replacing that known draft succeeds, without an extra send during the rejected operation.
- Original client storage contains positive IDs, final send state and exact persona cursors
  before and after cold restart; bot delivery is acknowledged and the full history agrees.
- A controlled local forwarder withholds a successful send response after commit. The app is
  stopped with its database intact. The actual negative pending ID has the accepted random-ID
  correlation. Restart leaves exactly one positive message, no pending duplicate and one bot
  update; a real bot produces exactly one reply.
- A separate synthetic serialization probe round-trips the compact acknowledgment and paginated
  difference responses through the pinned TL codec. Seventeen unsupported/conflicting commands
  are rejected without additional sends; an identical accepted retry returns identical bytes.

The baseline actual Send failed with the old adapter's unsupported-request error. A separate
read-state regression reproduced an outgoing database value changing across restart; the new
projection passes the same explicit before/after assertion. The latest focused case passes in
about two minutes. Original PNGs, UI trees, named client SQLite copies, semantic observations,
APK hash and guest profile stay in ignored run artifacts. The
[report helper](../../tests/composer_report.py) attaches those original captures and complete
observations to the existing report writer after assertions pass.

Fresh preparation reproduces all five Java files in patch eight and leaves 6,666 upstream
UI/resource files byte-identical. The source lock and strict dependency verification metadata
also match the offline build. The core send milestone passes 186 core tests at 82.55% coverage;
that result does not establish the new APK's full Android regression gate.

Use the [provisioned Android environment](environment.md) and
[outer offline guard](runtime-boundary.md), setting `GRAMLAB_ANDROID_PROBE_APK` to the prepared
local APK, then run:

```sh
.venv/bin/pytest tests/test_android_composer.py
```

## Remaining acceptance

Scenario composer input and simulation parity remain open. The original composer trims boundary
spaces/newlines, interprets formatting delimiters and splits long input; raw typed text is not
always the submitted semantic message. These transformations need explicit cross-mode proof.
Controlled acknowledgment-before-storage interruption, live gap recovery, broader targeting and
formatting rejection cases, and the full Android regression gate also remain open. Track them in
[native composer ticket 04](../../.scratch/programmatic-scenarios/issues/04-native-composer.md).
