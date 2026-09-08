# Validate authored animation at the original rendered scale and sampling cadence

Type: task
Status: ready-for-agent
Work state: resolved
Owner: custom-emoji-sampled-visual-oracle worker
Blocked by: none

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


## Implementation and focused evidence

`locate_animation_sequence` measures color-core pixel centers, then fits one origin and isotropic
scale for the entire carrier sequence. It checks compact occupied shapes, both square extents
within two screenshot pixels and every center against the common transform within one pixel.
The original color tolerance 38, alpha/background tolerance 30, full-canvas containment, moving
position, transparent margin and vacated-region checks remain. The single-frame helper uses the
same bounded fit; a sequence cannot substitute independent per-frame transforms.

`capture_intervals` uses newly recorded acquisition ends. For the retained old probe it uses
next-start minus the existing 80ms post-capture sleep and omits the final unknown end. Intervals
must be positive, nonoverlapping, shorter than half a period, and cannot span a potentially hidden
whole-period gap between neighboring acquisitions. Sampled cycle validation requires all four
states, unwraps only forward deltas 0/1/2 without inventing complete wraps, and intersects one
shared phase for the exact authored four 250ms bins. The returned inclusive phase bounds are
integer nanoseconds relative to the first capture start. The old no-timestamp helper mode retains
its stricter adjacent-state behavior; native acceptance always supplies acquisition intervals.

Only three burst timestamp lines are added to the guest probe: declare ends, record an end after
each screenshot, and include ends in observed results. Renderer, APK, authored media, capture
cadence and display settings are unchanged.

Verification used this checkout's pinned offline environment and its own editable import:

- `tools/dev default --offline --command unshare --user --map-root-user --net .venv/bin/pytest
  tests/test_custom_emoji_visual.py --junitxml=artifacts/custom-emoji-sampled-red.xml` initially
  produced **2 meaningful failures / 7 passes**: threshold edge loss hides known states and
  an independently authored sampled cyclic order fails the original adjacent-only checker.
  The temporal positive subsequently supplies acquisition intervals to the new optional API.
- The same focused command with `artifacts/custom-emoji-sampled-verified.xml` passes **32 tests**.
  Independent controls cover edge loss, individually valid drifting/scaling frames, wrong
  extents/positions, opaque/global changes, isolated colors, shuffled/reversed/missing states,
  impossible speed, acquisition uncertainty, overlapping/unbounded intervals and arbitrary wraps.
  Fixture self-review corrected two test-input mistakes without changing acceptance tolerances:
  an initially feasible exact-start timing fixture and a scaled color core outside the stated
  raster bound. The final negative controls first establish individual-frame validity where needed.
- Scoped Ruff lint/format, strict mypy on all four Python files and whitespace checks pass.

## Separate retained UI06 replay

`artifacts/replay_custom_emoji_ui06.py` reproduces the host-only replay using the unchanged primary
`artifacts/gramlab-custom-emoji-ui-06-qsf3r2ae/work/test_original_custom_emoji_edi0` capture directory.
Its `artifacts/custom-emoji-ui06-verified-replay.json` records exact hashes of every original input
and all four oracle/capture source files; it rechecks input hashes after reading. The original
failed native JUnit is untouched and is explicitly identified as failed in this new evidence.

The baseline oracle recognizes 0 ordinary, 0 rich and 6 button burst frames. The corrected shared
fit recognizes all 24 frames for each of the three carriers, with fixed scales approximately
0.23414, 0.28146 and 0.17869. All three sequences' first 23 bounded acquisitions share phase
`[189686425, 248161161]` nanoseconds. The six standalone edited/restarted carrier checks also pass.
This replay does not rerun the bot/guest or establish a newly successful native test execution.
The coordinator owns full retained lifecycle revalidation and original-image/report inspection.

Final oracle SHA-256: `96ad9e7f1f88dd56e4e3a7bbb45211c61c0917d2c35570d017cd5191dc941870`.
Replay JSON SHA-256: `5da5e149c9619651a142dae281479c6a0e4dc5a8ab4c92aef11084fe338bd48d`.

No native guest, Android build, full gate, fixture/profile change or runtime network was used.

## Coordinator integration

The integrated oracle passes all 32 focused tests, scoped Ruff/format and strict typing.
Full retained lifecycle revalidation also passes the real-bot semantic, isolation, PNG/XML,
original settings, static/animated carrier, native requests and exact cold-cache assertions.
`artifacts/custom-emoji-ui06-revalidation-01/assessment.json` records immutable input hashes and
explicitly distinguishes this host revalidation from a fresh guest run. The original failed
JUnit remains unchanged; the separate report accompanies the new assessment. Fresh native
execution and report inspection remain next.

## Fresh native lifecycle acceptance

`artifacts/custom-emoji-ui-09.xml` records one passing original Android lifecycle test in
130.06 seconds on unchanged normal24. Initial static carriers, actual bot callback edit, original
settings enable, all three animated carriers, native download and unchanged cold-cache restart
pass. All 24 conservative raw acquisition intervals are 140–210 ms (median 160 ms), below the
unchanged half-period bound; the unchanged spatial/phase oracle accepts all 72 carrier frames.
Independent Pillow decoding verifies every derived PNG against its exact retained raw pixels.
Original initial/edited/restarted PNGs and desktop/mobile report previews are inspected. Raw
frames, derivation metadata, JSON/logs and the passing report remain; the successful guest disk
is removed. Earlier failed JUnits remain failed. Resolver/shared-transfer faults and wider
current-message/native coverage remain separate gates.
