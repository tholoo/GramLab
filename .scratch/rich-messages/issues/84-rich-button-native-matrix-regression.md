# Check coordinate normalization using original Android Matrix and Canvas

Type: task
Status: ready-for-review
Work state: frozen on task/rich-button-native-matrix-regression
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

## Worker evidence

The probe compiles and dexes against the reviewed normal27 APK and exact cached normal27 classes.
It reflectively invokes the production helper while using Android's real Canvas, Matrix and RectF.
Seven independently specified cases cover outer-basis invariance with an expected-only reference cell origin, missing
and mismatched contexts, nested restoration, mismatched-end cleanup, singular entry, empty bounds and
a projective nonfinite first corner. Cell identities are constructor-free; rendering and touch remain
for the public native gate. No guest was run.

Coordinator reproduction uses the README commands and a fresh app-private output directory. The
worker compile output and complete input hashes are retained under the ignored
`.cache/rich-button-matrix-probe-04/`; compilation used javac 17.0.20.1, Android API/build tools 36,
probe source SHA-256 `cbd33c18f6c38c5bcf20abfcef27fc56c7a261361e36a3e206c53b83dc962dba`,
probe APK SHA-256 `88865fbee76c1cd7daf12e9325c3e62c96fbeaa3d9aac05f892144056fcbddd1`,
normal27 classes SHA-256 `f52d2fdff65e5c9bd59689bf0c00d30742dacb5d7d057001ee388cdf4bad5b46`
and normal27 APK SHA-256 `141415076e8727cfbffc6eacfe759f339e3640fa363ba5932e95cd7dc4a52375`.

The probe does not invoke production `getLocationOnScreen`; its expected screen bounds are explicitly
labeled `reference_only`. The projective negative records Android's raw eight mapped coordinates and
requires the first corner itself to be nonfinite before testing helper rejection. A failed premise is
a fixture/precondition failure, not a helper regression. Public native09 separately covers stable
production screen bounds across the popup redraw.
