# Original rich-button identity, observation and effect evidence

Type: task
Status: implementation-in-progress
Work state: claimed by task/rich-button-native-observer
Blocked by: frozen contract70; host integration and native acceptance are coordinator-owned

Own this ticket and new `clients/android/patches/0025-rich-button-observation.patch` only.
Coordinator owns patch-series registration, shared docs, Python host integration, compilation and
all guest gates. Follow licensing/upstream requirements and the
[frozen contract](../../../docs/development/rich-button-implementation-contract.md).

Implement the strict private schema1 observe/arm/disarm/effect protocol atop unchanged semantic
v4. Retain successfully applied message revisions, exact canonical path-to-original-object
mapping, process-lifetime nonce and post-draw observations. Enumerate canonical order separately
from visual RTL order; preserve invisible occurrences and explicit unavailability. No action or
hit-test replacement, invented labels, exported component, listener, renderer approximation or
pre-populated callback. Original row PageButton and inline textButton identity must survive decode.

Bind one consumed arm through exact original touch/action, native callback request object/token,
actual HTTP request_id and returned callback_id/revision. Missing or duplicate linkage is uncertain.
Copy requires the actual original handler plus foreground clipboard evidence; disabled reports
original DOWN suppression and absent UP action. Preserve original branch return values and drawing.
Use the source-reviewed seams supplied in the dispatch, not payload/label coincidence.

Limit patch scope to the normal adapter/runtime and the smallest observational hooks in original
rich touch, callback send and clipboard action paths. Report any additional source ownership need.
Use the immutable normal24 prepared sources supplied read-only in dispatch; stage only affected
files in an ignored worker directory to avoid another complete source export. Never edit the
coordinator build tree or acquired upstream. Retain selected source hashes and demonstrate the
patch applies exactly to those inputs. The patch must include applicable GPL notices/context.

Acceptance for this worker is reviewable source mapping, strict protocol behavior and patch
applicability; these are not native success. Add no speculative fake-native tests. Request a
coordinator build after freezing, retain any available focused compile/static evidence honestly,
and provide the exact source mapping and unexecuted native cases. No guest, full source export,
Gradle build, Python changes, series edit or full gate. Return a frozen clean commit and terminal
process/resource state. Remain claimed until actual integration and required acceptance pass.

## Worker evidence

Patch `0025` binds canonical paths during rich-message decoding and observes only original
row/inline draw, DOWN suppression, delegate dispatch and copy-handler branches. Its private reader
rejects malformed UTF-8, trailing input, duplicate/extra/missing members and invalid identity or
generation fields. One arm is acknowledged, consumed once and released only by its matching
disarm command. Callback evidence follows the exact request object through native token, HTTP
request ID and returned callback ID/revision. Canonical button JSON is retained unchanged,
including object-shaped `copy_text` and `disabled` members.

The patch dry-applies with `patch --dry-run -p1` to the selected normal24 inputs. Their SHA-256s
are `9a2aafbc...5721a` (GramLabBridge), `fa0d15a2...57dc` (GramLabRichMessage),
`a240f8db...e4a` (GramLabRuntime), `f231ba1c...1ffa9` (RichMessageLayout) and
`54511290...25b5` (ChatActivityEnterView). Compilation and native behavior remain coordinator
acceptance work; this worker did not run Gradle or a guest.
