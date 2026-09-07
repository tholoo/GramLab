# Prepare original static and animated custom-emoji assets

Type: task
Status: ready-for-agent
Work state: claimed by fixture worker
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
manifest. WebP bytes repeat under this profile. Two WebM generations differed at mux metadata while
decoding to identical pixels, so the documented WebM reproducibility boundary is decoded content,
not cross-run container identity.

Direct verification decodes both committed WebPs, all four committed WebM frames through the
explicit `libvpx-vp9` decoder, and a separately generated WebM. It checks dimensions, VP9 codec,
four 250ms packets, the WebM alpha-mode tag, actual decoded transparent and opaque alpha pixels,
four distinct frames, expected fixed/moving geometry, manifest hashes, and decoder rejection of the
truncated fixture. Static, thumbnail, first-frame, and last-frame images were also inspected. This
does not establish browser decoding, original Android rendering/playback, custom-emoji ownership,
or Bot API admission.
