# Deliver photos through the original Android file loader

Type: feature
Status: ready-for-agent
Work state: claimed by media-native worker
Blocked by: none; approved shared contract frozen

Follow [the media contract](../../../docs/development/media-implementation-contract.md).
Own `clients/android/patches/0017-local-photo-delivery.patch`, patch `series`, and this ticket.
Patch only GPL adapter/probe sources plus the narrow FileLoader/ImageLoader integration required
by the contract. Preserve upstream RichPhotoBlock, ImageReceiver, renderer and resources.
Coordinator owns Python probes, full source preparation, builds, guests and shared documentation.

Implement explicit v3 snapshot/change/callback negotiation, strict asset dependency parsing,
ordinary and rich original photo projection and reverse codec observation. Install dependencies
before messages; retain old granted mappings for retries and clear on World lifetime change.
Synthetic dc_id=0 locations must never reach normal FileLoadOperation/DC queues, even missing.
Load bounded authenticated loopback bytes into original cache locations; verify size/digest,
atomic rename, preserve original progress/success/failure, cancellation and duplicate coalescing.
No null FileLoadOperation dereference; exactly one terminal event; interrupted transfers leave no
readable final object and can explicitly retry. Late old completion must not replace edited media.

Use private copies of only needed files from the coordinator's verified normal16 source export;
do not mutate the acquired upstream or shared prepared export. Record exact preimage hashes and
zero-fuzz append-only patch applicability. Expose bounded adapter/probe evidence for descriptors,
photo metadata and loader outcomes without replacing renderer behavior or adding test-only success.
Return any required probe commands/interfaces early so coordinator can author independent oracles.
Source checks are not compilation/rendering proof. No worker build/guest is assigned. Commit owned
files and return frozen clean branch and terminal resources; retain claim until integration.

Negotiation is explicit through optional app configuration `bridge_version`: absent selects legacy
version 2 for retained fixtures, while the normal runtime supplies 3. Version 3 never falls back;
composer sends remain on `/v2/messages`, and callback/snapshot/change reads use their v3 routes.

## Worker handoff

Patch 0017 adds the explicit configuration negotiation, dependency-first photo projection and
synthetic loader seam. Absent `bridge_version` retains version 2; version 3 uses only its snapshot,
change and callback routes, while composer sends retain `/v2/messages`. Rich photos use the
original `pageBlockPhoto`, native `Photo`, `PhotoSize`, `ImageLocation`, `RichPhotoBlock` and
`ImageReceiver`. Normal photos use the original `TL_messageMediaPhoto`.

The loader recognizes reserved DC-zero locations before `loadFileInternal`, coalesces by the
original filename, streams only from the configured authenticated loopback bridge, validates
Content-Length, MIME, byte count and SHA-256, and atomically publishes into the selected original
cache directory. Missing mappings, redirects, malformed responses and integrity failures terminate
locally. Original delegate completion/failure and progress remain the handoff to ImageLoader;
ImageLoader's progress callback is null-safe only for this synthetic branch. App-private trace rows
contain no endpoint or capability.

Immutable normal16 preimages used for the patch have SHA-256 values
`32c93329848e5091128c78740e6bd69ba7149e6a60826bfa27198c32ffcd2c14` (bridge),
`7e1f63c4fa8d4020ac4c5fe50f716e434ca7d20a83995443255dc7cf63a271c2` (rich decoder),
`14fe9ab8c6bb39f853f0b0a520afbeb5570f1109c977dc4390dd9c62f9c2a50a` (FileLoader), and
`bf36a0c22b9e1ff9c9cf6c631cda024f01b4eecb0265cbb2b533e5526dba1099` (ImageLoader).
The patch applies to these copies with `patch --dry-run --batch --fuzz=0 -p1`. This worker did not
compile, build an APK or run a guest; coordinator-owned build, transfer faults, original rendering,
cache bytes, cancellation and retry remain required acceptance evidence.

Follow-up review adds the immutable BridgeProbe preimage
`3424cba845735756c3113dd92e61368c0c0ebd7775c14f585cfd4c1d2c406baf` and corrects cancellation,
retry ownership, failure reasons, strict mixed-version media rejection, repeated rich-photo reuse
and message field combinations. Its ordinary-message observation adds `native_photo`; a rich
message adds canonical photo blocks and `native_photos`. Each native photo object is exactly
`asset_id`, `dc_id`, `access_hash`, `file_reference_bytes`, `size_type`, `volume_id`, `local_id`,
`width`, `height`, and `file_size`. Existing non-media probe output remains unchanged.
