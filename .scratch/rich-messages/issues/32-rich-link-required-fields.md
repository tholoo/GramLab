# Reject missing rich-link fields at the native adapter boundary

Type: bug
Status: ready-for-agent
Work state: claimed by native worker
Blocked by: none; normal15 failure retained

Normal15 successfully serializes the baseline, initial/edited scenes and three URL metadata
variants, then a URL node missing its metadata produces no JSON result. The adapter's field
allowlist rejects extras but does not require fields; `JSONObject.get` throws `JSONException`
outside the probe's existing classified rejection boundary. The coordinator retains the failed
51.59-second run and original codec files. This is a native input-validation defect, not evidence
that the rich-link renderer works.

Worker owns only this ticket, `clients/android/patches/0016-rich-link-required-fields.patch` and
patch `series`, on `task/rich-link-required-fields`. Append a narrow patch requiring both visible
`text` and the same-named metadata field before access in each of the three new link branches.
Use the existing rich-message rejection contract. Retain null/type checks, recursive label
validation and existing unsupported-type diagnostics. Do not rewrite patch 0015, alter the
renderer/probe exception envelope, or change unrelated native validation behavior.

Use a private copy of the coordinator's verified normal15 `GramLabRichMessage.java`; record its
preimage digest, zero-fuzz/zero-offset dry-run and exact source difference. No full source export,
APK build, guest, runtime network or cache mutation is assigned. Coordinator owns independently
authored missing-text/metadata cases, process diagnostics, source comparison/build and red/green
native acceptance. Return the frozen branch, exact tip and terminal process state.

## Worker evidence

Patch 0016 adds one existing-contract `require` guard to each URL, email-address, and phone-number
branch immediately after its exact field allowlist. Each guard requires both recursive `text` and
the branch's same-named metadata field before either value is read. No probe, renderer, UI, or
other validation path changes.

The repeated normal15 red observes exit 137 with empty stdout and `Killed` on stderr for the
URL-missing case after baseline, scene, and three valid URL variants passed. It retains no Java
stack; identifying the unguarded `JSONObject.get` as the escape path is a source diagnosis.

The verified normal15 `GramLabRichMessage.java` preimage has SHA-256
`c605b502846f8cc60cfda3a4947b9354a5f9c644bf441e7a75aa9b0e3e33ffaf`; the private ignored copy
compares byte-for-byte with it. The intended postimage is
`7e1f63c4fa8d4020ac4c5fe50f716e434ca7d20a83995443255dc7cf63a271c2` and the patch digest is
`57224b2174e11bd81160955c7ee1aaf9e8a6f7caf693f1fecd169a9a00cf8160`.
`patch --batch --dry-run --fuzz=0 -p1` checks the sole file cleanly with no fuzz or offset output.
Compilation and native red/green acceptance remain coordinator-owned.

Coordinator verification compares all 43,268 reference files with the verified normal15 adapter
postimages. Only the three presence checks change; zero-fuzz application and exact postimage
verification pass. The normal16 strict offline build passes in 1 minute 59 seconds (78 tasks,
8 executed), and APK signature/source-digest checks pass. Native codec and real-bot rendering
both pass in 135.98 seconds, including all 29 invalid records and 11 valid shapes. The original
failure reports remain unchanged. The remaining43 combined gate is running on this APK.
