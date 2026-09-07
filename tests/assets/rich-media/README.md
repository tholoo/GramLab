# Original deterministic photo fixtures

These tiny RGBA PNGs are original GramLab test inputs generated under the repository's MIT
license. Their colored corners and coordinate-based pattern make orientation, aspect-ratio and
crop mistakes visible. `photo-truncated-invalid.png` is deliberately incomplete and must fail
image decoding.

The separate opaque JPEG fixture is a 64 by 48 four-quadrant RGB image. Its generator uses the
pinned media shell's FFmpeg MJPEG encoder with full-range 4:4:4 output. The JPEG manifest records
the complete portable encoder arguments and toolchain provenance. The invalid JPEG is the first
32 bytes of the valid image.

Reproduce the generated files with an explicit, existing output directory:

```sh
mkdir -p /tmp/gramlab-rich-media
python tests/assets/rich-media/generate.py /tmp/gramlab-rich-media
```

The generator refuses symlink output directories and existing files whose bytes differ. Run
`python tests/assets/rich-media/verify.py` to compare the committed files with fresh generated
bytes and the SHA-256 values in `manifest.json`.

Generate and verify the JPEG files inside the offline network guard:

```sh
mkdir -p /tmp/gramlab-rich-media-jpeg
tools/dev media --offline --command unshare --user --map-root-user --net \
  python tests/assets/rich-media/jpeg_generate.py /tmp/gramlab-rich-media-jpeg
tools/dev media --offline --command unshare --user --map-root-user --net \
  python tests/assets/rich-media/jpeg_verify.py
```
