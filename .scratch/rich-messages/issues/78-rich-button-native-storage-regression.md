# Independently verify native rich-button storage provenance

Type: task
Status: ready-for-agent
Work state: open
Blocked by: ticket77 implementation for green execution

Own this ticket and original probe sources under `clients/android/probes/rich-button-storage/`.
Keep Android-derived context within the GPL boundary and preserve applicable notices. Coordinator
owns compilation integration, guest execution, patch queue and shared docs. This task can prepare
independent fixtures and an actual-Android probe while ticket77 implements the storage seam.

Use real original message serialization, `MessageCustomParamsHelper`, native buffers and SQLite
write/load/reopen, with exact normal APK classes. Do not substitute fake Android/TL/storage classes
or count a source-pattern assertion as runtime evidence. If native loader initialization prevents
an independently runnable probe, report the exact missing prerequisite before broadening scope.

The agreed interface adds local `TLRPC.Message.gramLabRichButtonRevision` and
`gramLabRichButtonProvenance` fields. Positive revisions have bounded strict UTF-8 JSON containing
exactly schema1, revision and ordered occurrences with path and complete canonical button. Empty
occurrences are authoritative for button-free/ordinary replacement. `Params_v1` adds `FLAG_14`,
then trailing int64 revision and TL byte array. Observer `capture(message, canonicalMessage,
revision)` captures the same decoded response; `restore(message)` validates all topology before
binding final objects. No public bridge/private observation schema changes.

Specify independently authored row, inline and nested canonical paths with duplicate labels and
actions. Verify final object identities differ after actual storage load and bind to the correct
revision/path. A→B→A revisions remain distinct through write/load/reopen. Exercise incoming
authoritative provenance against old params reads, stale custom-only updates, empty metadata-only
shell reads, legacy absence, ordinary/button-free replacement and existing local fields.
Malformed UTF-8/JSON, duplicate members, truncation, over-limit extension, trailing bytes and
topology/count/path/action mismatch must not grant any partial mapping. Preserve a red on normal25
where the relevant missing behavior is observable; unimplemented fields are not a behavioral red.

Probe code may use reflection to inspect original observer identity bindings at this diagnostic
boundary, but must separately retain full serialized outcomes and exact reconstructed objects.
No fake input/effect success. Full public Android input/clipboard acceptance remains coordinator-owned.
Provide reproducible source/compiler/DEX hashes, exact invocation, expected output and observed
limitations. Do not launch a guest, Gradle build or full gate. Freeze a clean commit for review.
