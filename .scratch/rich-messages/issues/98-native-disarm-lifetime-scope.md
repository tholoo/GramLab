# Keep stale disarm records from blocking a new native client lifetime

Type: bug
Status: ready-for-agent
Work state: implemented on `task/native-disarm-lifetime-scope`; coordinator acceptance pending
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

## Answer

Patch 0028 keeps exact disarm framing, schema and token validation, then applies a valid record only
when its activation nonce, client nonce and live operation all match. A foreign-lifetime record is
left non-applicable so reload continues to the arm file. No polling cadence, deadline, geometry,
drawing, input or arm-admission code changed.

The GPL reflection fixture initializes only the actual observer's private control fields and invokes
its real `reload()` method. It covers old activation/current client, current activation/old client,
matching and different current operations, malformed JSON, extra fields, schema and all three token
failures. The matching case writes a fully valid current arm after invalidation, invokes reload
again, and verifies that the invalidated operation cannot rearm. One reusable probe APK is suitable
for the coordinator's normal27 red and normal28 green runs.

Worker verification:

- `tools/android-patch-stage` applied patch SHA-256
  `f2f25cd8360fc5a93c12fa7ac8bae3b15b37df6e200150482c59fffd487e33b2` with fuzz zero to the
  exact normal27 Observer preimage `0ac9b14f507166eeed269989f74ea64a64f12c8f152c6615149924606cf4da3d`;
  postimage `614a1df5c01f38f9b3d6df72cfedf28eb1d81de6e4a3ade7a9a4a747c2cfdc72`.
- Focused non-Android pytest passes 2 tests. Focused Ruff lint and strict mypy pass; Bash syntax is
  valid. The pinned offline Android shell compiles the fixture with Java 17, Android API 36 and D8
  36.0.0; probe APK SHA-256 is
  `8aa6232c5f4d72eb49628c494f2546ea3429ba2013f8ee5aa6f7cab21add2fa6`.

No guest or full APK build ran in this worker. Coordinator acceptance remains the normal27 red,
normal28 green, unchanged four-phase clipboard endpoint and combined checks specified above.
