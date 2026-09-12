# Proposed default document classification

Status: frozen fidelity policy; approved and implemented on 2026-09-12.

The user approved the complete recommended bounded local policy and its signature table. General
files remain ordinary documents, recognized specialized families reject until their complete typed
contracts exist, and explicit forced-file uploads remain unchanged. Changing that policy requires
renewed consultation.

This contract closes the omitted/false `disable_content_type_detection` gap without claiming to
reproduce Telegram's inaccessible server detector. The approved classification table is now a
versioned GramLab compatibility surface.

## Established behavior and source limits

The [pinned document review](documents-references.md) establishes that:

- explicit `true` selects TDLib's forced-file path, while omitted or false permits remote
  classification;
- the public `sendDocument` result carries a `Document`, not a photo-size array;
- PNG/JPEG decoding is not part of the inspected document-upload path;
- returned document attributes can distinguish animation, audio, video, voice, sticker,
  custom-emoji and general-document families; and
- the detector behind those returned attributes is not in the reviewed client or server adapter.

It follows that an earlier candidate rule—turn valid PNG/JPEG document uploads into photos—is not
recommended. It would contradict the public return shape, change reusable media type and apply a
photo decoder where the source contract explicitly says not to do so.

## Recommended bounded local policy

For a fresh multipart upload, GramLab would clean and validate the complete request before any
visible World mutation, then apply one deterministic byte-family classifier:

1. Explicit `disable_content_type_detection=true` keeps the implemented behavior unchanged: every
   otherwise valid admitted payload from 1 through 50,000,000 bytes follows the ordinary-document
   path. Existing multipart, attachment, filename, caption, keyboard and request-envelope rules
   still apply.
2. Omitted and explicit false are equivalent. PNG, JPEG, PDF, ZIP/Office, text, arbitrary binary
   and unknown formats remain ordinary documents under the same 50,000,000-byte limit.
3. Recognized specialized families reject with
   `GRAMLAB_UNSUPPORTED: default document content classification` until GramLab implements their
   complete Bot API, World and original-Android contracts. The exact proposed byte table is:

   | Family | Exact recognition rule |
   | --- | --- |
   | GIF | at least 6 bytes; bytes 0–5 equal `GIF87a` or `GIF89a` |
   | RIFF media | at least 12 bytes; bytes 0–3 equal `RIFF` and bytes 8–11 equal `WEBP`, `WAVE` or `AVI ` |
   | EBML media | at least 4 bytes; bytes 0–3 equal `1a 45 df a3` |
   | ISO-BMFF media | at least 8 bytes; bytes 4–7 equal `ftyp` |
   | Ogg | at least 4 bytes; bytes 0–3 equal `OggS` |
   | FLAC | at least 4 bytes; bytes 0–3 equal `fLaC` |
   | ID3 audio | at least 3 bytes; bytes 0–2 equal `ID3` |
   | TGS | at least 2 bytes; bytes 0–1 equal `1f 8b` and the cleaned filename's ASCII-case-insensitive extension derives `application/x-tgsticker` |

   A generic gzip remains an ordinary document.
4. Classification ignores the declared multipart content type. It also ignores filename-derived
   MIME except for the `.tgs` discriminator, preserving the pinned filename/MIME behavior for any
   admitted document.
5. A value shorter than a complete discriminator and any near-signature or unrecognized specialized
   format remains a document. Once the complete discriminator above matches, the file rejects even
   if the rest of its container is truncated. This is deliberate determinism, not evidence that
   Telegram would make the same decision.
6. Typed `file_id` reuse is never reclassified. It retains its existing media kind and bot-scoped
   authority; the request flag has no effect on reuse.
7. The same rule applies to a fresh multipart `InputMediaDocument` in standalone
   `editMessageMedia`. Document albums bypass it because the pinned album route always forces
   ordinary-file behavior.

The classifier should expose one pure request-boundary interface,
`require_supported_default_document(upload: DocumentUpload) -> None`, which returns normally for an
ordinary document and raises the stable unsupported error for a matched family. World methods
remain explicitly typed and do not acquire detector policy. Validation and classification precede
publication; any rejection must leave blobs, typed identities, grants, messages, revisions, events
and public allocation unchanged.

This policy intentionally detects only whether GramLab knows an upload belongs to an unsupported
specialized family. It does not manufacture partial animation/audio/video/sticker attributes, and
it does not turn detection into a no-op by silently treating false as true.

## Approved consequences

- This is a conservative GramLab emulation. It may reject files Telegram would retain as ordinary
  documents and admit files Telegram would specialize.
- The exact signature table and the `.tgs` exception become versioned local behavior.
- Applying the same policy to document media edits means a newly uploaded recognized specialized
  file rejects before the existing message is changed.
- Implementing real specialized media later should replace the corresponding rejection with a
  separately reviewed typed contract; it must not silently change existing ordinary identities.

The source-aligned alternative is to leave omitted/false detection unsupported until independent
server observations or complete specialized-media implementations exist. Treating PNG/JPEG as
photos is not retained as an alternative.

## Acceptance boundary

Implementation requires direct and named multipart coverage for omitted, false and true; exact and
near-match cases for every signature; PNG/JPEG controls; ordinary PDF/ZIP/text/opaque files; empty,
50,000,000-byte and over-limit cases; same-bot reuse; default media edits; and full logical-state
rollback/retry comparisons. One contained real-bot scenario must show an admitted default document
and an unsupported specialized rejection. Existing forced-document original-Android evidence may be
reused because admitted output remains the already verified ordinary-document type.

Passing those checks would establish only this documented offline policy, not Telegram-server
classification parity.
