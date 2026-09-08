# Rich-message work index

This index covers the current integration work. The
[handoff](../../docs/development/handoff.md) retains earlier milestones and evidence.

## Verified findings

- [67: semantic captures](issues/67-custom-emoji-semantic-captures.md) preserve canonical
  custom-emoji alternatives; integrated core checks pass.
- [68: virtual callbacks](issues/68-current-semantic-inline-callbacks.md) use current message
  semantics; actual contained callback checks pass.
- [69: Android host compatibility](issues/69-current-android-host-interactions.md) has passing
  host regressions and combined core checks; original native acceptance remains unexecuted.
- [70: shared rich-button contract](issues/70-rich-button-implementation-contract.md) is frozen
  within the approved proposal after independent source and recovery reviews.

## Active implementation

- [71: canonical occurrences and journal](issues/71-rich-button-core-primitives.md).
- [72: original native observation](issues/72-rich-button-native-observer.md).
- [73: control and client integration](issues/73-rich-button-control-integration.md).
- [74: independent public acceptance](issues/74-rich-button-public-acceptance.md).
- [77: exact native storage provenance](issues/77-rich-button-native-persistence.md), following
  actual Android object-identity loss after TL reconstruction.
- [78: independent storage regression](issues/78-rich-button-native-storage-regression.md).
- [79: original emoji settings diagnostic](issues/79-custom-emoji-settings-input.md).

## Remaining uncertainty

Contracts, host tests and collected native scenarios do not prove actual animation, rich input,
clipboard effects or the broader operational milestone. Preserve the pending native gates and
the full product scope documented in the handoff.

## Current follow-ups

- [91: document source contract](issues/91-document-source-contract.md): pinned filename/MIME
  derivation and empty-upload rejection are researched; ordinary file implementation remains open.
- [92: clipboard acceptance](issues/92-rich-button-native-clipboard-acceptance.md): resolved: full four-phase native07 passes actual paste/clear in155.89 seconds; original
  stale-disarm and asynchronous popup-focus failures remain documented.
- [94: multipart metadata](issues/94-multipart-upload-metadata.md): integrated with 12 affected
  checks passing and the 948-test combined core gate passing.
- [95: unrelated target survival](issues/95-native-unrelated-edit-target-survival.md): resolved: fresh normal27 native03 passes the complete
  same-layout unrelated-edit case in95.41 seconds; earlier failures remain recorded.
- [96: shared immutable bytes](issues/96-neutral-media-byte-storage.md): schema-8 migration accepted with 53 affected
  checks and the 968-test combined gate; ordinary document APIs remain open.

- [97: pinned document metadata](issues/97-pinned-document-filename-metadata.md): exact filename
  cleaning and extension-derived MIME are integrated with32 independent focused checks.
- [98: native disarm scope](issues/98-native-disarm-lifetime-scope.md): resolved: actual native red/green proves strict lifetime-scoped handling; complete
  clipboard native07 and1054-test combined core gate pass.

- [99: ordinary document World](issues/99-ordinary-document-world.md): typed storage, schema9
  migration and v5 dependencies are integrated; the 1,126-case core16 gate passes.
- [100: multipart filename decoding](issues/100-multipart-document-filename-decoding.md):
  integrated;83 multipart/photo/metadata checks pass with explicit inspection-connection cleanup.

- [101: ordinary native codec](issues/101-ordinary-document-native-codec.md): resolved with
  34 actual native cases, the intended old-client rejection and combined core16/static15.
- [102: document Bot API](issues/102-ordinary-document-http-delivery.md): resolved for explicit
  forced-file upload/reuse/download, with 50 affected HTTP checks and combined core16/static15.
- [103: document client bridge](issues/103-document-client-bridge.md): resolved with 78 affected
  HTTP/World checks and combined core16/static15.
- [104: original document loading](issues/104-ordinary-document-native-delivery.md) and
  [105: real-bot document UI](issues/105-ordinary-document-native-ui.md): active implementation;
  original external-files publication and complete native acceptance remain pending.

- [106: standalone media edits](issues/106-standalone-media-edits.md): resolved at the World/HTTP
  boundary with core18/static17; native acceptance is assigned separately.
- [108: native media-edit workflow](issues/108-native-standalone-media-edits.md): extend the existing
  real-bot document scenario; original Android execution remains gated on104 delivery.
