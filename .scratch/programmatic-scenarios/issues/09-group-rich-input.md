# Drive group rich actions through the selected member

Type: task
Status: resolved
Work state: resolved
Blocked by: 08-group-android-client.md

Complete the generic client-input seams needed by consumers whose group messages use GramLab rich
buttons. Keep the World, scenario and Android behavior independent of any consumer application.

## Acceptance

- A selected non-bot group member can type the first message into an empty group through the public
  composer API; the private-chat requirement to press Start before typing remains unchanged.
- Rich-button observation accepts an explicit group member persona and carries that actor through
  target allocation, simulation/native dispatch, callback creation, receipts and recovery.
- Missing, bot, outsider and mismatched personas fail at public boundaries without allocating a
  target or creating a callback. Existing private rich-button calls remain compatible.
- A public runner test proves an actual group rich-button callback in the original Android client,
  including exact callback actor/chat, retained native evidence and a screenshot.
- Focused red/green tests, strict typing, the non-Android gate and serialized Android acceptance pass
  before support is claimed. Documentation records the supported seam and remaining limits.

## Public seams

Tests use the typed scenario composer, versioned scenario HTTP operations, canonical rich-target
API, World-visible events and the public Android runner. Private helpers, direct database writes and
UI injection are not acceptance seams.

## Comments

Claimed on 2026-09-13 after a consumer-neutral causal scenario replaced semantic group injection
with public composer and rich-button input. Its retained simulation run failed when GramLab applied
the new-private-chat Start requirement to an empty supergroup. Static inspection then identified
the adjacent private-only actor lookup in rich-target allocation. The user approved completing and
landing the causal consumer scenario; this ticket owns only the generic GramLab prerequisite.

Resolved on 2026-09-13. The initial public tests failed on the empty-group Start invariant and the
missing `user_id` rich-observation parameter. The green implementation keeps private Start behavior,
requires a non-bot member for group rich input, carries signed group IDs through the host/journal and
adds patch 0035 for the Android observer's existing signed-ID mapping. The one-file patch stages with
preimage `614a1df5c01f38f9b3d6df72cfedf28eb1d81de6e4a3ade7a9a4a747c2cfdc72`, postimage
`10753fc4f339c630ab36fa08e22910b91f2d3e8ee1301c12255c74da23d27664` and no fuzz/offsets.

The complete offline build passed in 19m10s. APK SHA-256:
`fff0c33f6991202b08a63e77a501f3bc188eecda9ae45047bf1cf39400c11521`. The retained public Android
run `artifacts/group-rich-native-05/` passed in 110.19s with callback actor `3`, chat `-1`, one native
composer send after bot restart, blocked IPv4/IPv6 probes, zero accounts and three inspected original
PNGs. Result SHA-256: `910176a564bbdbdda4ae09b5cabb006b612ca2d156ebb94f3ffc542246bdb3ab`.
Focused host/World/scenario/patch coverage passed 167 tests before formatting. The final contained
non-Android gate passed all 1,623 tests in 119.62s at 89% coverage with zero failures or skips;
JUnit SHA-256: `19ce0aef52550ac08d989eb0580b66cc8f109fa043815e1cb1d958afed6f718d`.
The maintained strict rich-input, interaction and Android-host typing scopes pass, as do repository
Ruff lint and format checks.
