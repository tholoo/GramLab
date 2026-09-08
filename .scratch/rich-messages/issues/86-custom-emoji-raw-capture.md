# Measure original animation pixels before PNG encoding

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: none

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


## Verified format and implementation

The Android 16 tagged [original screencap source](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-16.0.0_r1/cmds/screencap/screencap.cpp)
(source SHA-256 `d96446a2953ee572924df5c295fdfb466ef80ff7b5fe2a1e89f33909a967b3c0`)
writes four native uint32 values: width, height, pixel format and colorspace. It writes only the
active pixels of each row, excluding buffer stride padding. Raw output skips bitmap compression
and the PNG filename's media-scanner notification. The [Android pixel format definition](https://android.googlesource.com/platform/hardware/interfaces/+/master/graphics/common/1.0/types.hal)
defines format 1 as increasing-address R, G, B, A bytes. These are protocol facts; no upstream
implementation was copied or adapted into the helper.

The retained `artifacts/rich-button-matrix-suite-02/capture-benchmark/` files independently establish
the supported x86_64 profile: little-endian header `(320, 640, 1, 1)`, exactly 819216 bytes,
packed RGBA8888 sRGB, with every alpha byte 255. The buffer is premultiplied; this implementation
rejects translucent alpha rather than attempting an unverified conversion. Other dimensions,
byte orders, formats, colorspaces, lengths and row padding fail closed.

The guest command now retains `edited-burst-NN.raw` files. Its version-2 manifest explicitly
identifies `RAW_RGBA_8888_SRGB`, binds all 24 ordered sizes and SHA-256 values, and retains the
unchanged conservative uptime brackets and 80 ms sleeps. One pull follows the burst. All 24
originals must validate before a stdlib encoder writes RGBA8 PNG derivatives with sRGB metadata.
The encoder preserves every pixel byte and performs no geometry or color transformation.

All raw originals remain in `custom-emoji-burst-<nonce>/`; staged derivatives remain in its `png/`
child. The existing top-level `edited-burst-NN.png` interface contains lossless host derivatives.
`edited-burst-derivation.json` records the input format, header, opaque condition, timing bounds,
raw paths/sizes/hashes, RGBA hashes, and derivative PNG paths/sizes/hashes. It also binds the
original manifest's hash. Output links never overwrite evidence; caught publication failures
remove newly published links while retaining original and staged evidence. The derivation record
is published last. Abrupt process death does not provide atomic multi-file publication and never
establishes successful native acceptance.

## Focused evidence and integration

The raw-only external screencap boundary in a real POSIX shell first failed because the old
command passed `-p`; retained `.cache/raw-capture-evidence/red.txt` records that behavioral red.
The authored raw fixture deliberately varies x, y and RGB channels; Pillow independently decodes
the resulting PNG and compares every pixel. Negative controls cover malformed framing, unsupported
raw profiles, exact-size boundaries, alpha, partial or changed transfers, existing evidence and
mid-PNG/final-metadata publication failures. Only external screencap/transfer results are substituted;
the shell, uptime reads, sleep, size/hash tools, filesystem validation and PNG codec run for real.

Read-only replay `.cache/raw-capture-evidence/benchmark-replay.json` confirms all four original raw
files retain SHA-256 `de02a7ed9e57ee5bdbfbb8a2a1b2ab506a6e1986755b06f1d7f7952afaebadbe` and all
four derivatives decode exactly to their source RGBA bytes. Raw `01` also equals the independent
original PNG `00` decoded pixels, whose PNG SHA-256 is
`9711ad8433fb0abb22de9025da9bf9d8413bfa915b23a24b9fe6c35622459896`. Original benchmark files and
UI08 timing failures remain unchanged. This is encoding evidence from a system-display benchmark,
not fresh custom-emoji acceptance.

Final-source verification: all 47 focused controls pass under network isolation; scoped Ruff
lint/format and strict mypy pass. Commands and evidence:

- `tools/dev default --offline --command unshare --user --map-root-user --net .venv/bin/pytest -q tests/test_guest_screenshot_burst.py --junitxml=artifacts/custom-emoji-raw-capture-distinct-final.xml`
- `tools/dev default --offline --command uv run --locked --offline ruff check tests/probes/guest_screenshot_burst.py tests/test_guest_screenshot_burst.py`
- `tools/dev default --offline --command uv run --locked --offline ruff format --check tests/probes/guest_screenshot_burst.py tests/test_guest_screenshot_burst.py`
- `tools/dev default --offline --command env MYPYPATH=tests uv run --locked --offline mypy --strict --explicit-package-bases tests/probes/guest_screenshot_burst.py tests/test_guest_screenshot_burst.py`

No additional staged module or runtime package is required: the helper uses only stdlib. The
coordinator must describe edited-burst PNGs as lossless derivatives of retained original raw
pixels, retain the derivation JSON/raw directory, and run fresh native acceptance with the existing
500 ms temporal oracle. Guest dependencies remain original `screencap` (without `-p`), shell,
`/proc/uptime`, `toybox wc`, `toybox sha256sum`, fractional sleep and one directory pull. No guest,
APK build, fixture/profile/oracle change or full gate ran for this worker task.


### Independent ordered-frame review correction

The initial transfer fixture reused identical hardlinked bytes. A new first/last content-permutation
control reproduced its coverage gap: the expected rejection did not occur, retained in
`artifacts/custom-emoji-raw-capture-permutation-red.xml`. The transfer fixture now writes 24 separate
files with independently distinguishable opaque RGB identifiers and digests. The success control
requires all 24 unique hashes/inodes and checks each index's exact original bytes, independently
decoded PNG pixels, manifest record, metadata raw/PNG/RGBA hashes and sizes, and acquisition bounds.
The changed-file fault mutates only one RGB byte in frame 00 and verifies frames 01–23 remain intact.
The permutation control now passes. All 47 isolated controls pass in
`artifacts/custom-emoji-raw-capture-distinct-final.xml`; scoped Ruff lint/format and strict mypy pass.
The capture helper and its source-backed format/encoding behavior are unchanged by this correction.

## Coordinator integration

All 79 combined raw-capture and unchanged visual-oracle controls pass in
`artifacts/custom-emoji-raw-capture-integrated-01.xml`; scoped Ruff/format and strict typing
pass. The native acceptance caller independently decodes each of the 24 PNG derivatives with
Pillow and compares every RGBA byte to the retained raw payload, as well as checking frame/hash/
timing bindings. Reports retain derivation metadata and distinguish these burst PNGs from
original PNG screencap output. Fresh native UI09 is the next acceptance gate.

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
