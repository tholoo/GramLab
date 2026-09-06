# Native composer and interrupted send recovery

The pinned actual Android composer now sends ordinary text through the
[durable version 2 bridge](client-sends.md). The focused guest case passes: one ASCII send,
two equal Unicode sends, real bot replies, cold restart and a send interrupted after the world
commits but before Android receives its acknowledgment. The complete 20-test Android gate also
passes for this APK. The additional [composer-text contract case](composer-text-references.md)
then passed seven fixtures separately. This does not complete the scenario composer API or every
interrupted replica-write boundary. The 20-test gate predates that additional case.

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
released. Projection preserves acknowledged outgoing database read state rather than inventing
a peer read receipt at restart. General read receipts and presence remain unimplemented.

The visible bot-chat checkmark has a separate upstream policy:
[ChatActivity](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/ChatActivity.java#L21015)
marks loaded outgoing bot messages read in memory. Captured accessibility text correspondingly
changes from `Not seen` after acknowledgment to `Seen` after history loading, while stored
`read_state` remains 2 and the dialog's outbox read maximum remains 0. The same visible transition
was reproduced in two focused runs. Preserve this original UI rule; its checkmark is not evidence
of a simulated peer read receipt. A preliminary assertion equating display status with database
state failed and was corrected against this pinned source behavior without modifying the UI.

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
also match the offline build. The core send milestone passes 186 core tests at 82.55% coverage.
The full Android gate passes 20 tests with 186 core tests deselected. Its composer case also
generates the evidence report after assertions. Later display-status assertions pass when replayed
against three runs' retained original captures; the new text-transformation case passes separately.
The generated report was served successfully over local HTTP, but the configured browser returned
`ERR_FAILED`; its current browser layout review remains unverified.

Use the [provisioned Android environment](environment.md) and
[outer offline guard](runtime-boundary.md), setting `GRAMLAB_ANDROID_PROBE_APK` to the prepared
local APK, then run:

```sh
.venv/bin/pytest tests/test_android_composer.py
```

## Remaining acceptance

The [scenario composer](scenario-composer.md) now exposes Start Bot and bounded typed input.
Its independent text model matches seven native fixtures, and a consumer scenario passes in both
simulation and actual Android with matching histories, events and accepted sends. Long input,
nested formatting, links and dice remain outside that verified profile. The original composer
transforms raw input before sending; broader transformations still need cross-mode proof.
Controlled acknowledgment-before-storage interruption, live gap recovery, broader targeting and
formatting rejection cases also remain open. Track them in
[native composer ticket 04](../../.scratch/programmatic-scenarios/issues/04-native-composer.md).
