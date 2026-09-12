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

## Accepted foundations

- [71: canonical occurrences and journal](issues/71-rich-button-core-primitives.md),
  [72: original native observation](issues/72-rich-button-native-observer.md), and
  [73: control/client integration](issues/73-rich-button-control-integration.md) are integrated.
- [74: independent public acceptance](issues/74-rich-button-public-acceptance.md) passes its bounded
  row/inline action scenario; residual frozen-contract native cases move to115.
- [77: exact native storage provenance](issues/77-rich-button-native-persistence.md) and
  [78: its independent regression](issues/78-rich-button-native-storage-regression.md) pass after
  correcting actual Android object-identity loss through TL reconstruction.
- [79: original emoji settings diagnostic](issues/79-custom-emoji-settings-input.md) is incorporated
  into accepted custom-emoji lifecycle evidence.

## Remaining uncertainty

Actual animation, public rich input and clipboard effects now have bounded original-client evidence.
They remain split across normal24/27/28 checkpoints; residual current-APK and final composed
acceptance are tracked below. The current approval-independent host selection passes52/52 at
`artifacts/rich-button-current-host-01.xml`. Preserve the full product scope documented in the
handoff.

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
  [105: real-bot document UI](issues/105-ordinary-document-native-ui.md): resolved on normal30 with
  original external-files publication, transfer/cache/restart evidence and inspected UI.

- [106: standalone media edits](issues/106-standalone-media-edits.md): resolved at the World/HTTP
  boundary with core18/static17; native acceptance is assigned separately.
- [108: native media-edit workflow](issues/108-native-standalone-media-edits.md): resolved by the
  original Android D1→P1→D2 workflow, exact transfer/cache state and cold restart.

- [107: public document runner](issues/107-document-runner-v5.md): resolved through the explicit-v5
  public CLI, contained real bot, original inline tap, stable reuse and two inspected Android views.

- [109: public-source preparation](issues/109-public-source-readiness.md): resolved with audited
  source/history, explicit source licenses, an original English glass preview and a verified README
  example. Both GitHub branches use the approved cleaned history; visibility remains private.

## Awaiting fidelity decisions

- [110: default document classification](issues/110-default-document-classification.md): proposed
  conservative specialized-family detection; implementation awaits user approval.
- [111: album contract](issues/111-album-contract.md): proposed atomic 2–10 member photo/document
  albums, bridge-v6 complete-group delivery and explicit local identity/bounds choices.
- [112: album core and bridge](issues/112-album-core-and-bridge-v6.md),
  [113: Android adapter](issues/113-album-android-adapter.md) and
  [114: native/public acceptance](issues/114-album-native-and-public-acceptance.md) remain unassigned
  and blocked on ticket111. Core classification and album parsing must be serialized where their
  ownership overlaps.
- [93: rich automatic detection](issues/93-rich-auto-detection-policy-proposal.md) remains an
  unapproved local fidelity proposal.

## Approval-independent current work

- [115: residual rich-button native acceptance](issues/115-rich-button-residual-native-acceptance.md)
  owns true RTL input, clipped rejection, restart recovery and lost-reply reconciliation on normal30.
- [116: current-APK public custom emoji](issues/116-custom-emoji-current-apk-public-runner.md) owns
  the complete bridge-v5 public runner and focused normal30 regression.
- [118: current reproducible setup docs](issues/118-current-reproducible-setup-docs.md) corrects
  stale scaffold/build/patch-queue instructions without claiming pending behavior.
- [117: final representative workflow](issues/117-final-representative-workflow.md) remains blocked
  on the fidelity decisions and all focused implementation/acceptance tickets.
