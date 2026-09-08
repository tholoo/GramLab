# Validate authored animation at the original rendered scale and sampling cadence

Type: task
Status: ready-for-agent
Work state: open
Blocked by: coordinator retained-evidence validation and review

Own this ticket, `tests/custom_emoji_visual.py`, `tests/test_custom_emoji_visual.py`,
`tests/test_android_custom_emoji.py` and the burst timestamp capture portion of
`tests/probes/android_custom_emoji.py`. Coordinator owns other integration, native execution and
shared docs. No renderer, APK, display profile, fixture media or product-runtime changes.

The original guest now completes real bot edit, original settings enable, download and cold-cache
restart. The retained test fails its pixel oracle. Read-only replay identifies two checker errors:
thresholded color bounding boxes shrink at small native scale, and screenshot acquisition gaps
exceed one authored frame interval. The existing adjacent-four-state check contradicts ticket65's
explicit allowance for skipped sampled transitions. Preserve the original failed JUnit.

Use the authored marker and moving-square geometry to fit one fixed origin and isotropic scale
per carrier across the sequence, accounting for bounded raster edge uncertainty. Centroid fitting
must independently verify both shapes/extents and bounded residuals. Preserve current color and
alpha tolerances, full canvas bounds, transparent margins, vacated regions and distinct carriers.
Reject unrelated colored pixels, wrong extents, drifting canvas/scale and opaque backgrounds.
Do not fit a new transform independently for every frame and call that stationary animation.

Temporal acceptance must use the authored one-second period and four quarter-second states,
require all four states and a shared feasible phase across acquisition intervals. Recorded host
start times are not exact capture instants. Capture start/end timestamps for future bursts; for
retained evidence, a conservative end is the next recorded start minus the probe's explicit
post-capture delay, with the final sample omitted when its end is unknown. Validate ordered,
nonoverlapping, bounded intervals. Reject reverse order, shuffled states, impossible timing,
single-frame changes, arbitrary wraps and insufficient state/cycle coverage. Do not silently
weaken cycle evidence to a set of four colors.

Keep the existing public helper surface where useful and make the temporal/geometry result
reviewable. Add independent synthetic positive and negative controls for native-scale edge loss,
skipped transitions, acquisition uncertainty and the incorrect behaviors above. Replay the
unchanged retained frames as a separate diagnostic with exact source/input hashes; do not relabel
the original run green or regenerate its frames. New guest execution and original-image/report
inspection remain coordinator-owned. Run focused pure tests, strict typing and lint/format only.
Return a clean frozen branch with detailed evidence and remaining acceptance limits.
