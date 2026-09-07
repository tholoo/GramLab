# Original custom-emoji fixtures

These small fixtures are original GramLab geometry under the repository's MIT license. The 100px static
WebP has a fixed green marker and an opaque colored square on transparency. The VP9 WebM has four
frames: the marker stays fixed while the colored square moves and changes color. The 16px WebP
thumbnail is a blue diamond on transparency. `emoji-truncated-invalid.webm` is deliberately
incomplete.

Generation uses local raw RGBA bytes and no input URL. Reproduce into an existing directory with
the recorded FFmpeg profile:

```sh
mkdir -p /tmp/gramlab-custom-emoji
python tests/assets/custom-emoji/generate.py /tmp/gramlab-custom-emoji
python tests/assets/custom-emoji/verify.py
```

The verifier repeats generation, checks byte-identical assets and manifest hashes, and decodes the
committed WebPs with exact alpha and exact visible RGB from lossless VP8L payloads. It compares
repeated WebM generation by decoded pixels, decodes every
committed WebM frame through `libvpx-vp9`, checks the full expected alpha geometry and interior
colors, and checks the WebM container, VP9 stream, and every frame timestamp/duration. Both ffprobe
and ffmpeg must reject the truncated fixture. A seekable WebM output lets the muxer record the final
one-second duration; output-side bitexact flags make repeated bytes stable under this profile.
Codec or FFmpeg version changes may produce different valid bytes or pixels and require review.

These assets establish controlled static/animated inputs. They do not establish Bot API admission,
custom-emoji ownership, Android media delivery, original-client rendering, or animation playback.
The locally retained contract sources do not establish an upload dimension limit; 100px square
inputs were selected conservatively and successful decoding is not an API-admission claim.
The manifest records FFmpeg and libavcodec versions. The selected executable reports libvpx and
libwebp support without their exact library revisions, so those revisions are explicitly unpinned.
