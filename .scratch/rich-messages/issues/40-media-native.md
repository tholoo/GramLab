# Deliver photos through the original Android file loader

Type: feature
Status: ready-for-agent
Work state: open
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
