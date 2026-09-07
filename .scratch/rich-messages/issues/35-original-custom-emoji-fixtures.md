# Prepare original static and animated custom-emoji assets

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: none for original fixtures; runtime media architecture remains unapproved

Implementation worker owns only `tests/assets/custom-emoji/` and this ticket on
`task/custom-emoji-fixtures`. Read the handoff, parallel workflow, testing, licensing and upstream
guidance. This is asset preparation, not World/API/native implementation. The coordinator owns
shared docs, dependency files, native gates and integration.

Create independently authored static WebP, transparent VP9 WebM animation and usable WebP
thumbnail fixtures with a small source generator, portable provenance/manifest and verification
instructions. Use a simple visibly changing geometric pattern with transparent and opaque regions;
do not acquire Telegram art. The required animated workflow uses WebM, so TGS alone is insufficient.
Keep source fixtures and derived binaries small. Include a deliberately truncated invalid input.

Use an explicitly selected encoder executable and record its software/codec versions and flags;
keep actual host paths outside the repo. Prefer the existing pinned Nix package revision if
available offline. Do not change the flake, lockfiles, shared environment or provision another
checkout's virtualenv. If exact encoded bytes depend on codec versions, state the reproducibility
boundary instead of claiming cross-version identity. Keep all inputs local and encoding/decoding
contained with no external input protocols.

Acceptance: inspect container/codec/dimensions/duration/frame count and alpha support, independently
decode multiple frames, verify visible change plus opaque/transparent regions, decode the WebP
thumbnail and reject the truncated fixture. Compare repeated generation under the same recorded
encoder profile and retain results. Verification must decode the committed bytes, not only compare
the generator with itself. Expected pattern assertions must come from the specified geometry.
Report unavailable independent decoding honestly; the coordinator can add browser inspection.

Avoid adding tests to the normal pytest inventory or changing any existing source/fixture inputs
while the current native gate runs. Run focused static checks on new scripts with the assigned
checkout's environment, and direct artifact generation/validation checks. No APK build, Android
guest, bot, API, premium/ownership model or media delivery work is assigned. Commit only owned
files, leave the branch frozen/clean and return exact provenance, checks and terminal resources.
These fixtures cannot establish original Android animation or Bot API custom-emoji support.

## Worker evidence

The original fixture set contains a 100×100 transparent static WebP, a 100×100 four-frame
transparent VP9 WebM at 4 fps, a 16×16 transparent WebP thumbnail, and a deliberately truncated
WebM. Geometry has a fixed opaque marker, transparent background, and an opaque square that moves
and changes color in every animation frame. The locally retained contract sources do not establish
an upload dimension limit; choosing 100×100 is conservative and is not an API-admission claim.

Generation used FFmpeg 6.1.6 with locally available `libwebp` and `libvpx-vp9`, one encoder thread,
local raw RGBA input, and no input URL. The exact flags and full fixture hashes are portable in the
manifest. An initial pipe-muxed WebM lacked final container duration and varied mux metadata; that
red output was replaced. The final generator writes WebM to a seekable temporary file and applies
bitexact flags to the output, producing byte-identical repeated assets with an explicit one-second
duration. Removing the WebP preset makes the requested lossless option effective; final WebPs use
VP8L and preserve visible colors exactly.

Direct verification decodes both committed WebPs, all four committed WebM frames through the
explicit `libvpx-vp9` decoder, and a separately generated WebM. It checks dimensions, VP9 codec,
four 250ms packets, the WebM alpha-mode tag, actual decoded transparent and opaque alpha pixels,
four distinct frames, complete expected fixed/moving alpha geometry and interior colors, exact
per-frame timestamps/durations, WebM container identity/duration, manifest hashes, and decoder
rejection of the truncated fixture. Static, thumbnail, first-frame, and last-frame images were also
inspected. This does not establish browser decoding, original Android rendering/playback, custom-emoji ownership,
or Bot API admission.

Review follow-up preserves the original browser reds: the first static WebP used lossy VP8 despite
the requested option, and the pipe-muxed WebM exposed only 0.75 seconds to Chromium. Removing the
WebP preset produces VP8L with exact independently decoded visible colors. Seekable WebM output
plus output-side bitexact flags records the intended one-second duration and repeats byte-for-byte.
The strengthened verifier checks the full alpha mask, fixed/moving interior colors, exact packet
timestamps and durations, and actual WebM container identity. Pinned Ruff 0.16.5 format/check and
strict mypy 1.20.2 pass for both scripts. The manifest records libavcodec 60.31.102; the selected
executable exposes libvpx/libwebp support but not their exact linked revisions, which remain
explicitly unavailable rather than described as fully pinned.


## Integrated acceptance

The coordinator reviews the frozen worker branch and merges without conflict. Pinned integrated
Ruff lint/format and strict mypy pass. Direct regeneration and decoding pass inside a network
namespace. Independent Chromium decoding of the exact final blobs checks every WebP visible pixel
and alpha value, all four WebM alpha masks and interior colors, each selected frame, one-second
container duration and decoder rejection of the truncated video. No external browser resource is
requested; the owned review tab is closed.

The initial browser color and duration failures remain in ignored evidence and the earlier commit.
Final static/thumbnail WebPs use VP8L and preserve exact specified colors. Output-side bitexact
flags and seekable WebM muxing preserve the final frame duration and deterministic bytes under
the recorded profile. The helper reports unavailable exact linked codec library revisions honestly.
Contributor guidance and CI cover strict typing; the pinned offline workflow validator passes.
No World/API/native behavior or normal pytest
inventory changed, so the accepted 447-core/45-Android feature gates were not repeated for assets.
