# Quoted code correction

Status: core and native corrections integrated; focused acceptance passes; broader gate in progress.

Pinned [TDLib nesting validation](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/MessageEntity.cpp#L1560-L1607)
admits code/pre entities whose enclosing entities are blockquotes. GramLab previously rejected
them in both its independent Python validator and GPL adapter. The correction fixes that existing
nine-type boundary without changing text, adding HTML parsing, or changing upstream rendering.

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
The corrected codec includes 16 positive combinations and 14 independent rejections, including two
additional equal-extent emphasis/code ancestor permutations added after that red run.

Fresh preparation and the integrated build-cache comparison examine 43,268 exported files and
find only `GramLabBridge.java` different before applying patch 0014 with zero fuzz. All 6,666
checked original UI/resource files and dependency metadata remain unchanged. The normal APK
builds offline in 2 minutes 50 seconds with strict verification; signatures pass. The independent
native codec and real-bot original-renderer scenario both pass in 170.23 seconds. Complete
World/API/native comparisons, account-free guest isolation, live edit and cold restart pass.
All three original PNGs were inspected. Quotes show the original purple treatment and monospaced
code; the preformatted portion is visually separated by the upstream quote layout. No renderer
fix or language-header presentation is claimed.

All 411 core tests pass at 81.01% coverage in 70.49 seconds. Twenty-two documented static scopes
and the pinned workflow check pass. Browser review found seconds passed into the report's
millisecond field; the report now converts units explicitly. Retained-result validation preserves
every native assertion (checked by AST comparison) and every original PNG/XML/JSON/JSONL hash.
The original passing JUnit is retained; no guest was rerun for this presentation correction.
The report writer initially refused replacement of an existing file as designed; the original
report was preserved before regenerating into a fresh destination.

The two focused Android passes are retained for the combined 43-case inventory. Before starting
the remaining 41 serial cases on the same APK, current inputs, both staged APKs, 56 staged Python
files and both runtime profiles were verified against the retained run. The later host-only
report conversion/extraction is separately revalidated as described above; runtime inputs and
native assertions are unchanged. The continuation stopped after six passes and one emulator
startup failure caused by insufficient disk space (631.48 seconds). That failed JUnit remains
unchanged. Disposable userdata overlays from three completed passing suites were reclaimed under
the shared Android lock; all 5,114 retained evidence-file hashes match. Eight passing identities
are now retained and the remaining 35 are running with source/APK/profile equivalence checked.
Combined acceptance and ticket resolution remain pending. Corrected desktop/mobile reports were
inspected: all three images load, timing units are milliseconds and neither viewport overflows.

The second continuation passes seven cases before the list fixture's restart reports activity
launch timeout/unknown state. Its log records the activity displayed after 12.321 seconds, beyond
the command's 10.737-second wait; the edited/restarted XML matches. Host checkbox assertions after
the failing launch check were not executed in that pytest run; they subsequently pass against
the retained result. Original lifecycle acceptance remains failed. One unchanged isolated control
then passes in 72.79 seconds with both cold-launch statuses, and its edited/restarted PNGs were
inspected. This is evidence of variable launch delay, not a proven scheduling fix. Sixteen passing
identities are retained across the four reports; the remaining 27 are running. Both failed JUnit
reports remain unmodified.

The 27-case continuation subsequently reports 27 passes in 1364.02 seconds, but a later import
audit invalidates combined acceptance: the primary virtualenv had been redirected to a worker
checkout before this continuation and the isolated list control. On-disk source hashes did not
verify host import origin. Original counts, images and failed reports remain unchanged. The
earlier 411-case core run and focused quoted-code rendering precede that environment change.
The [checkout guard correction](../../.scratch/developer-tooling/issues/11-checkout-import-preflight.md)
repairs the install and rejects wrong imports before collection. Combined native acceptance must
be repeated on the next integrated normal APK; tickets 26/27 remain pending that gate.
