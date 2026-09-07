# Quoted code correction

Status: core and native corrections integrated; combined/native acceptance in progress.

Pinned [TDLib nesting validation](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageEntity.cpp#L1560-L1607)
admits code/pre entities whose enclosing entities are blockquotes. GramLab currently rejects
them in both its independent Python validator and GPL adapter. Correct that existing nine-type
boundary without changing text, adding HTML parsing, or changing upstream rendering.

## Frozen core/native contract

- Ordinary and expandable quotes may contain code or pre, including the same UTF-16 extent.
  The pre language field retains its existing validation and serialization.
- Canonical core order is offset ascending, length descending, quotes before other types at
  equal extents, then the existing alphabetical type tie-break. Remove exact duplicates as before.
  Native validation also orders an equal-extent quote before code/pre, independent of input order.
- A code/pre entity may have only quote ancestors. Inspect all active ancestors: an emphasis
  outside an intervening quote still makes contained code/pre invalid. Code/pre may contain no
  other entity. Crossing ranges, nested quotes, split UTF-16 symbols and unsupported types/fields
  retain explicit rejection. Do not normalize arbitrary invalid inputs into success.
- Same-extent quote and code/pre mean quote containment after canonical ordering. A strictly
  smaller quote inside code/pre remains invalid. Existing quote/style equal extents now put the
  quote first consistently; cover canonical no-op edits to make the ordering change observable.
- Message schemas, bot/client identity, history/events, text/limits, decoding and renderer stay
  within existing boundaries. This does not implement the separate HTML normalization pipeline.

Core owns `entities.py` and new public World/HTTP tests; native owns an appended GPL patch 0014
and the patch series. Coordinator owns real-bot/native codec/rendering scenarios, builds, shared
docs and combined checks. Both implementations must independently reject invalid ancestor chains
and admit valid UTF-16 ranges; passing one validator is not evidence for the other.

## Required evidence

Cover both quote kinds crossed with code/pre, equal and strictly contained extents, both input
orders, supplementary-plane text, pre language, duplicates and formatting-only edits. Reopen
World storage and compare complete HTTP responses, history, snapshots and events. Invalid sends
and edits must leave state and IDs unchanged. Retain the pre-fix public failure.

The coordinator separately checks a trusted canonical/adversarial snapshot through the actual
native serializer, then a real form-encoded bot send/edit through original Android rendering and
cold restart. Retain complete native/World/API semantics and inspect original PNG/XML/report
evidence. The old normal APK must reject a valid quoted-code fixture at the native boundary;
the new APK must accept it and preserve the independent malformed rejections. Fresh preparation
and source comparison must show that only the adapter changes, with original rendering preserved.

## Current verification

The independent real-bot send fails on the old core with HTTP 400 in 0.99 seconds. After the
core merge, 37 focused World/HTTP/real-bot tests pass, including the unchanged rich harness
defaults. The old normal APK passes its baseline codec, then rejects valid quoted code with
`GRAMLAB_BRIDGE_INVALID_DATA`; the original native failure is retained (119.72 seconds).
The next codec includes 16 positive combinations and 14 independent rejections, including two
additional equal-extent emphasis/code ancestor permutations added after that red run.

Fresh preparation and the integrated build-cache comparison examine 43,268 exported files and
find only `GramLabBridge.java` different before applying patch 0014 with zero fuzz. All 6,666
checked original UI/resource files and dependency metadata remain unchanged. The normal APK
build and actual native/rendering acceptance remain in progress; none is claimed from source
inspection or core tests alone.
