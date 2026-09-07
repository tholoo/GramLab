# Reject missing rich-link fields at the native adapter boundary

Type: bug
Status: ready-for-agent
Work state: ready for native worker
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
