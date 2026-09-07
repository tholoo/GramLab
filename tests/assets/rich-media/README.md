# Original deterministic photo fixtures

These tiny RGBA PNGs are original GramLab test inputs generated under the repository's MIT
license. Their colored corners and coordinate-based pattern make orientation, aspect-ratio and
crop mistakes visible. `photo-truncated-invalid.png` is deliberately incomplete and must fail
image decoding.

Reproduce the generated files with an explicit, existing output directory:

```sh
mkdir -p /tmp/gramlab-rich-media
python tests/assets/rich-media/generate.py /tmp/gramlab-rich-media
```

The generator refuses symlink output directories and existing files whose bytes differ. Run
`python tests/assets/rich-media/verify.py` to compare the committed files with fresh generated
bytes and the SHA-256 values in `manifest.json`.
