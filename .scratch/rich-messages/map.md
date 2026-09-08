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
