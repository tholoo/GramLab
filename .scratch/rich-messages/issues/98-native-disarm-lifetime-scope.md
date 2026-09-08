# Keep stale disarm records from blocking a new native client lifetime

Type: bug
Status: ready-for-agent
Work state: open
Blocked by: none

Clipboard acceptance92 native05 proves an arm acknowledgement timeout after a deliberate public
observation cold-launches the next client lifetime. The old completed operation remains the visible
effect. The retained actual prepare frame fails while waiting for the new operation, before input.
Pinned normal27 source identifies the mechanism: host success writes a disarm record; same-persona
cold launch retains app files; native reload rejects that old record's activation/client identity
before ever reading the new arm, and poll swallows the exception every time. This contradicts the
frozen operation/lifetime-scoped disarm contract. Keep the failed native evidence unchanged.

## Ownership and correction

Own this ticket; new `clients/android/patches/0028-rich-button-disarm-lifetime.patch`; the patch
`series` append only; new focused `tests/test_android_button_disarm.py`,
`tests/probes/android_button_disarm.py`, and bounded GPL Java probe fixture under
`tests/fixtures/android_button_disarm/`. Coordinator owns shared docs, APK staging/building and
combined/native acceptance. Use the current normal27 Observer source as an ignored read-only
reference; never edit the live Android source. Generate the patch from a private minimal file copy.

Keep strict disarm framing, exact fields, schema and token validation. A valid disarm applies only
when both activation nonce and client nonce match the current lifetime, and its operation matches
the live arm. A valid older-lifetime disarm is non-applicable and must not prevent reading the new
arm. Matching current disarm must still invalidate only its operation and prevent rearming it.
Malformed controls remain fail-closed. Do not weaken arm admission, geometry/freshness checks,
clipboard guards, invalidated-operation checks, input, deadlines or original rendering. Do not
replace this correction with deleting guest files, redraws, renewed targets or retries.

## Verification

Reproduce the scope bug through the actual native implementation using a small Android app_process
probe if feasible: old activation/new client and new activation/old client separately, both stale,
matching current operation, different operation in current lifetime, and malformed/schema/token
controls. Reflection may initialize only the original adapter's private control state and call its
real reload method; do not duplicate reload logic in an oracle or claim this as rendered input.
No production test switches or extra drawing/invalidation are allowed. A stale valid record plus
no arm file should leave state unchanged without throwing; a matching current record should
invalidate exactly the matching arm. Verify original invalidated-operation state, not just return
status. Keep any Java-derived fixture under GPL notices and outside the MIT core.

Worker owns focused host/collection/static checks and exact zero-fuzz patch verification only;
coordinator runs normal27 red and normal28 green native probes and the unchanged four-phase92
clipboard endpoint on the newly built APK. Source inspection or host stand-ins do not replace those
native checks. Report any probe compilation needs precisely without building a full APK or guest.
Follow TESTING.md, licensing/upstream and the parallel workflow, keep reference inputs/cache small,
and freeze the clean branch with actual full Git hash and terminal process state.
