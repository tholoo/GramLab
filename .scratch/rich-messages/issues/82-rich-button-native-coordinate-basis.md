# Normalize observed button bounds to the original cell coordinate system

Type: task
Status: ready-for-agent
Work state: open
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
