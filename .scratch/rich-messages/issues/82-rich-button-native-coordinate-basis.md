# Normalize observed button bounds to the original cell coordinate system

Type: task
Status: ready-for-review
Work state: frozen on task/rich-button-coordinate-basis
Blocked by: coordinator source review, compilation and native acceptance

Own this ticket, one new GPL patch `clients/android/patches/0027-rich-button-coordinate-basis.patch`
and its entry in `clients/android/patches/series`. Coordinator owns host readiness, integration,
cached build source and guest execution. Do not edit previous patches or upstream rendering.

The observer maps a button through the complete current Canvas matrix, calls that cell-local,
then adds the cell screen location. Original draw paths can supply different outer canvas bases.
The retained public run shows a 112-pixel basis change between generations. Normalize against an
explicit matching cell-draw entry matrix before adding the screen location exactly once.
Prove the chosen seam has cell-local coordinates; account for current/outgoing crossfades and
reject missing, mismatched or noninvertible contexts. Preserve original placement, hit testing,
input propagation and drawing, including disabled row propagation to parent handling.

Use the frozen observation contract. Keep the normal patch self-contained and applicable after
0026 with zero fuzz/offset. Verify the source boundary and report an independent actual-Android
matrix regression plan covering different outer translations/scales, cell origin, missing context,
noninvertible matrices and row/inline carriers. No guest/build/full gate is assigned. Coordinator
will compile and run the original public scenario with screenshots and actual effect correlation.

## Worker evidence

Patch 0027 captures the Canvas matrix at each exact `ChatMessageCell` rich-layout draw boundary.
The observer maps each button through the current matrix and the inverse entry matrix, producing a
cell-local axis-aligned bound before adding `getLocationOnScreen` exactly once. Contexts are
thread-local, nested, cell-identity checked and scoped with `finally`; missing, mismatched,
noninvertible, nonfinite or empty geometry fails closed and makes that binding stale. Outgoing and
current crossfade layouts have separate contexts. Original drawing, button hit testing and disabled
row propagation are unchanged.

Zero-fuzz/offset dry application against verified normal26 passed for both source files. The
modified observer compiles against the pinned Android 36 SDK and normal26 cached classes with eight
missing-Kotlin-annotation warnings only. A standalone full `ChatMessageCell` javac check remains
unavailable because its cached partial classpath lacks unrelated AndroidX `ColorUtils`/`MathUtils`
types (33 errors, none at patch hunks). No Gradle build or guest was run. Coordinator regression
should exercise row and inline rectangles under identity and translated/scaled outer matrices,
assert equal cell-local results plus one cell-origin offset, and reject missing, mismatched and
noninvertible contexts. The public guest must verify stable bounds across redraws and actual taps.
