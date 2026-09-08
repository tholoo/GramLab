# Measure original animation pixels before PNG encoding

Type: task
Status: ready-for-agent
Work state: open
Blocked by: coordinator native acceptance

Own this ticket, `tests/probes/guest_screenshot_burst.py` and its focused tests in
`tests/test_guest_screenshot_burst.py`. Coordinator owns the caller/staging list, animation
oracle, native runs, shared documentation and acceptance. No APK, renderer, animation fixture,
profile, sampling count, delay or temporal/spatial acceptance changes.

UI08 proves that guest PNG screencap calls can exceed the unchanged half-period bound even
without intervening host transfer. A fixed eight-capture PNG/raw experiment in the matrix-suite-02
guest shows a lower raw-capture median, and an original raw frame's pixels equal a separately
captured PNG's decoded RGBA pixels exactly. This is a system-display benchmark, not emoji
acceptance; preserve the timing failures and do not infer fresh UI success from it.

Use original guest raw screencap for all 24 ordered frames with the existing 80 ms delay. Bracket
its actual command with the same conservative guest monotonic reads; never subtract estimated
costs from previous captures. Transfer raw frames only after the burst. Keep every original raw
file, its exact byte count/hash and original timing manifest. Produce PNG derivatives on the host
using lossless encoding only: no resize, recolor, crop, alpha changes or favorable-frame selection.
The derived PNG pixels must equal the independently decoded raw pixels exactly.

First verify the pinned Android raw framing and pixel semantics using primary source and the
retained benchmark. Restrict supported framing to the verified profile: reject unexpected
width/height, pixel format, color space, stride/length, count, ordering, path or trailing data.
Do not guess or silently convert an unknown layout. Preserve existing shell quoting, bounded
subprocess/file parsing, immutable input hashes and failure-safe publication. Keep input format
and PNG derivation explicit in retained metadata so reports never call derived PNGs original
screencap PNG bytes. The original raw pixels remain the rendering evidence.

Add focused independent parser/encoding controls, including exact pixel comparison through an
independent PNG decoder, wrong framing/format/dimensions/length, partial transfer, publication
failure and boundary-sized input. Preserve meaningful existing capture controls. Reuse existing
stdlib or pinned dependencies; do not add a new dependency or runtime network access. No native
run or build assigned. Return a frozen branch, original failure evidence, focused/static checks,
and precise caller/staging/doc integration needs. Native animation acceptance remains required.
