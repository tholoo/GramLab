# Confirm original effects while an app-owned message popup has focus

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: coordinator native acceptance

Coordinator owns this ticket, `src/gramlab/_android_rich_buttons.py`, focused host tests and the
public rich-target scenario/acceptance files. Other workers must not edit those files.

Native diagnostic09 proves the disabled row opens an original APPLICATION_PANEL popup attached
to the original activity, with the same app PID, package and installed UID. Its complete native
disabled suppression evidence is currently rejected because focus is named PopupWindow rather
than an activity component. Normal27 keeps row/inline bounds stable across this popup redraw.

Preserve strict original activity/cell focus before dispatch. For confirmation only, resolve
the exact focused window token to one unambiguous window record, require the installed package
UID and live app PID, original package, visible surface, APPLICATION_PANEL type and a matching
owned original activity parent. Recheck PID/focus after ownership reads. Reject foreign, missing,
ambiguous, hidden, wrong-parent and restarted cases. Do not trust the title or focused app alone.
Keep native effect/clipboard/World/quiet checks unchanged; do not dismiss menus inside the host.

Order the independent public acceptance actions so the disabled row runs last, preserving its
original menu. The scenario's existing subsequent observation already cold-launches the client.
Do not add an extra launch, synthesize input, alter the renderer or count diagnostic substitution
as uninstrumented acceptance. Preserve diagnostic09 and focused external-boundary red/green;
run the real public scenario after the correction.

## Focused coordinator checkpoint

The positive owned-popup replay fails at the original focus check while 18 rejection controls
pass (`artifacts/rich-button-popup-red-01.xml`). The corrected host and reordered real-bot
simulation pass 108 focused tests (`artifacts/rich-button-popup-green-03.xml`), with scoped Ruff
and strict typing. Post-input confirmation verifies the exact window, package UID, session PID,
visible panel and owned original parent, then rereads focus/PID. Pre-input focus remains strict.
No native effect, clipboard, event or quiet-period check is removed. Native acceptance is next.
