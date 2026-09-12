# Local custom emoji

GramLab has an immutable World catalog for original local WebP and VP9 WebM custom emoji,
with Bot API lookup/download and version-4/5 client delivery. The adapter passes 99 independent
native codec cases and the photo/mention codec regressions. Normal24 lifecycle acceptance proves
four initial static carriers, a real bot callback/edit, original animation settings, three animated
carriers, native download and unchanged cold-cache restart. All24 burst captures pass its unchanged
spatial/temporal checks; PNG derivatives are independently verified pixel-for-pixel against retained
original raw frames.

On the current immutable normal30 APK, the complete public bridge5 runner and codec gate pass. The
public run registers static WebP and animated VP9 WebM through `gramlab run`, renders incoming,
ordinary, rich and rich-button carriers, performs the original inline callback/edit, and retains the
edited state across a cold relaunch. A fresh full fault run also passes exact failed/idle pixels,
three recovery paths, shared progressive transfer, cache reuse, zero accounts and offline
containment. Original screenshots were inspected. The clean lifecycle timing run retains exact
authored pixels and lockstep states across all three animated carriers, including a22-frame exact
phase window, but its complete24-frame phase intersection misses by80 milliseconds. That JUnit
therefore remains failed under the unchanged criterion; normal24 is still the latest full temporal
acceptance. [Ticket116](../../.scratch/rich-messages/issues/116-custom-emoji-current-apk-public-runner.md)
records the artifacts and pending fidelity decision. See the
[implementation contract](custom-emoji-implementation-contract.md) for exact shapes and
[the current handoff](handoff.md) for combined verification and limits.

## Registration

A trusted scenario can supply selected local fixture bytes through the experimental SDK:

```python
from pathlib import Path
from gramlab.scenario import Scenario

scenario = Scenario.from_environment()
emoji = scenario.register_custom_emoji(
    request_id="example-emoji-v1",
    custom_emoji_id="1109",
    main=Path("fixtures/emoji.webm").read_bytes(),
    thumbnail=Path("fixtures/thumbnail.webp").read_bytes(),
    fallback="✨",
)
```

Declare both files in the scenario manifest. A static main must be one-frame 100×100 WebP,
at most 512 KiB. An animated main must be 100×100 VP9 WebM, at most 256 KiB, with one video
stream, no audio, at most 30 frames per second and a positive duration of at most three seconds.
The WebP thumbnail is one frame, 1–100 pixels in each dimension and at most 128 KiB. Registration
fully decodes the original bytes; it does not re-encode or fetch them. Transparent fixtures are
supported by the validator, while native alpha playback still needs visual acceptance.

The WebM profile validates complete outer framing as well as decoding. Finite Segments must end
at input EOF. Unknown-sized outer Segments support at most 4096 finite immediate children;
unknown-sized children are explicitly unsupported. This bounded framing check is not a general
Matroska parser. Decoder stdout/stderr and total execution time are bounded. The trusted Nix
supervisor supplies pinned decoder paths; scenario and bot processes do not receive that closure.

The returned descriptor contains `custom_emoji_id`, `fallback`, `free`, `needs_repainting`,
`main_asset_id`, `thumbnail_asset_id` and `duration_ms`. Logical IDs are canonical positive
signed-64 decimal strings. Callers can choose an integer or string ID at registration, or omit it
for a separate allocator. Choosing a large ID does not advance that allocator. Equal media bytes
reuse immutable assets. Registration neither sends a message nor grants a persona access.

`request_id` identifies the normalized registration. Repeating identical input returns its original
descriptor, including after reopen; changing bytes or metadata conflicts without a partial mutation.
The SDK never retries automatically. A lost response may follow a committed registration: callers
can retry the same request ID with the same inputs to recover it. An actual forwarding peer verifies this lost-response recovery, and a contained public CLI
scenario registers both static and animated original fixtures through the trusted supervisor.

## Messages and delivery

Ordinary `custom_emoji` entities use UTF-16 offsets and lengths and retain the exact covered text.
The local admission predicate is the pinned BSL-licensed TDLib emoji predicate described in
[its provenance](tdlib-emoji-provenance.json), not an assertion of production server admission.
Rich custom-emoji leaves retain their explicit `alternative_text`, including different or empty
alternatives and leaves inside supported rich-button labels. Public semantic captures use those
canonical alternatives, including nested button-label arrays; they do not substitute the catalog
fallback. The contained capture regression and existing capture controls pass focused checks. Free/repainting metadata describes
local fixtures; it does not prove a real entitlement or production document availability.

`getCustomEmojiStickers` accepts up to 200 decimal-string IDs, returns unique known entries sorted
numerically and omits unknown IDs. Main and thumbnail `file_id` values belong to the requesting
bot. `getFile` and file downloads preserve those capabilities; logical IDs and file-unique IDs do
not authorize downloads. Emoji file IDs cannot be reused as PNG/JPEG photos.

Publishing or editing an emoji-bearing message atomically grants its recipient the required
documents and bytes. Old grants remain after edits for frozen callbacks and client cache recovery.
Version-4 snapshot, changes, callbacks and incoming messages carry their required dependencies.
Document lookup authorizes the complete requested set: an unknown or ungranted ID makes the whole
request unavailable, with no partial documents. Older bridge versions explicitly reject selected
emoji content rather than silently removing it.

The trusted runner accepts explicit bridge4 and bridge5 and records that choice with Android
inputs. Its default remains3 for older reviewed APKs. This choice is not a scenario TOML field.
Use only a reviewed APK supporting the chosen version. Public registration/capture pieces and the
complete incoming/static/animated/button/edit/restart workflow through `gramlab run` pass on
normal30. This public composition result does not substitute for the separate codec,
lifecycle-timing and fault oracles.

The GPL adapter constructs original Telegram Documents and routes their original resolver and
file loaders through authorized local delivery. Static original rendering may use the thumbnail;
an animated document uses its main WebM. Snapshot metadata does not pre-populate the original
Document memory/SQLite cache. Streaming, remote assets and real Telegram accounts are unsupported.
