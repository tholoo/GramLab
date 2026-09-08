# Observe and enable the original animation checkbox reliably

Type: task
Status: ready-for-agent
Work state: open
Blocked by: coordinator native acceptance

Own this ticket and `tests/probes/android_custom_emoji.py` only. The coordinator owns guest
execution, shared docs and integration. Follow ticket65's original settings diagnostic boundary.
No APK, renderer, profile, fixture, product runtime or animation-oracle changes.

The retained original run reaches the expanded Animated Emoji category, then fails after one tap
on the text child of Autoplay in keyboard. The before/after XML and screenshots are identical and
show one unchecked checkbox. This establishes no observed state change; it does not establish why
the tap failed or prove a product defect. Preserve that failure and its original captures.

Use the unique original CheckBox accessibility row with exact label and fresh bounded geometry,
targeting its visible checkbox side rather than the text child. Re-read state before input;
already checked means no input. Observe the resulting checked state with bounded polling before
any further attempt. At most three freshly authorized checkbox-enable attempts are allowed in
this disposable diagnostic. Never blindly toggle, silently ignore ambiguity, extend scenario
deadlines or apply this retry policy to product input. Still fail if the actual checkbox is not
enabled. Retain each original hierarchy/screenshot and bounded preferences before/after, including
on failure, so the next run distinguishes unchanged preferences from delayed visual state.

Apply the same helper to keyboard and chat settings. Preserve original category navigation,
the narrow per-guest opt-in and the cold restart before edited rendering. Confirm relevant original
LiteMode setting-versus-effective flag behavior from pinned local source before drawing a cause
conclusion. Focused lint/format/type checks are sufficient for this small diagnostic correction;
do not add fake Android tests. The actual unchanged-renderer guest is the acceptance boundary.
Return a clean frozen branch and scope/evidence handoff. No guest or build execution.
