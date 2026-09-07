# Prepare original static and animated custom-emoji assets

Type: task
Status: ready-for-agent
Work state: open
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
