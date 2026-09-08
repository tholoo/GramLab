# Check coordinate normalization using original Android Matrix and Canvas

Type: task
Status: ready-for-review
Work state: frozen on task/rich-button-native-matrix-regression
Blocked by: none

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

## Worker evidence

The probe compiles and dexes against the reviewed normal27 APK and exact cached normal27 classes.
It reflectively invokes the production helper while using Android's real Canvas, Matrix and RectF.
Seven independently specified cases cover outer-basis invariance with an expected-only reference cell origin, missing
and mismatched contexts, nested restoration, mismatched-end cleanup, singular entry, empty bounds and
an affine finite-input overflow at the first corner. Cell identities are constructor-free; rendering and touch remain
for the public native gate. No guest was run.

Coordinator reproduction uses the README commands and a fresh app-private output directory. The
worker compile output and complete input hashes are retained under the ignored
`.cache/rich-button-matrix-probe-05/`; compilation used javac 17.0.20.1, Android API/build tools 36,
probe source SHA-256 `71b8a5cd988e25b92367d76a7263561c38a4d673f661614a5d61734959dda418`,
probe APK SHA-256 `42ca5f29e96e33c56854cc0f873c40ab46d7c51d5e3d027eea871fd8947bdf83`,
normal27 classes SHA-256 `f52d2fdff65e5c9bd59689bf0c00d30742dacb5d7d057001ee388cdf4bad5b46`
and normal27 APK SHA-256 `141415076e8727cfbffc6eacfe759f339e3640fa363ba5932e95cd7dc4a52375`.

The probe does not invoke production `getLocationOnScreen`; its expected screen bounds are explicitly
labeled `reference_only`. The overflow negative records Android's raw eight mapped coordinates and
requires only the first corner to be nonfinite before testing helper rejection. It replaces the
projective zero-denominator fixture rejected by native matrix-suite-01 because Android mapped every
corner to finite zero. A failed premise is
a fixture/precondition failure, not a helper regression. Public native09 separately covers stable
production screen bounds across the popup redraw.

## Coordinator integration

The reviewed probe source and exact cached classes/APK/DEX/probe fingerprints match the final
compile manifest. Both shell scripts pass syntax and ShellCheck checks in the pinned environment;
`git diff --check` passes. Actual guest execution remains pending, including class initialization
and the explicitly guarded nonfinite fixture premise. This is not native acceptance yet.

## Native acceptance

`artifacts/rich-button-matrix-suite-01` retains six passing cases and the failed projective
fixture premise. The corrected finite-input affine fixture produces infinity only at its first
corner; all later coordinates remain finite. The helper rejects it as required. All seven cases
pass in `artifacts/rich-button-matrix-suite-02`, with unchanged staged input hashes, matching
normal27 APK/probe provenance and independent guest isolation assertions. This verifies actual
Android arithmetic and context guards, not visible rendering or original input. Dedicated guest
disks were removed after retaining per-case JSON and provenance.
