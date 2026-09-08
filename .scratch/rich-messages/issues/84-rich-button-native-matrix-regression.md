# Check coordinate normalization using original Android Matrix and Canvas

Type: task
Status: ready-for-agent
Work state: open
Blocked by: coordinator native execution

Own this ticket and `clients/android/probes/rich-button-matrix/`. Coordinator owns patches,
APK builds, guest execution and public targeting acceptance. Reuse existing probe compilation
and guest-launch patterns where practical; keep code and provenance within the GPL boundary.

Provide a small independently specified regression against the exact normal observer helper
using real Android Canvas/Matrix operations. Compare expected cell-local rectangles under
identity, translation and nonuniformly scaled outer bases, and the explicit screen-origin
addition. Include absent/mismatched draw context, noninvertible entry matrices, empty rectangles
and nonfinite mapped coordinates, including the first-corner case identified in source review.
Exercise nested context restoration. Do not copy the normalization algorithm into the oracle.

If cell identity must be allocated without UI initialization, explain that substitution precisely:
this probe proves actual Android matrix computation and context guards, not visible rendering or
original touch behavior. Do not initialize accounts or native transport. Preserve bounded JSON
results and exact compiler/source/APK provenance. Compile with cached inputs only; no guest,
build, external traffic or full gate. Hand back a clean frozen branch with exact checks and
commands for coordinator execution against normal26 and normal27 where applicable.
