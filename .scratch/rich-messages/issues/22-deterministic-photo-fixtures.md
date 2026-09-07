# Prepare original deterministic PNG fixtures for the media milestone

Type: task
Status: claimed
Work state: claimed by rich-photo-fixtures worker; awaiting coordinator integration and independent decoding
Blocked by: none for fixtures; media API and delivery design remain unchosen

Prepare reusable original image inputs while the coordinator finishes native rich effects and
prepares the media design for user consultation. This task does not introduce media support,
public file identifiers, a storage schema, a download endpoint or Android cache injection.
Read tests/assets/README.md, TESTING.md, licensing and the parallel workflow.

Own only `tests/assets/rich-media/` and this ticket. Use branch `task/rich-photo-fixtures` in its
own checkout. Write a small stdlib-only generator that emits deterministic original RGBA PNGs:
16×16 square, 48×8 wide and 8×48 tall, with distinctive corner colors and a simple diagnostic
pattern so crop/aspect/orientation mistakes are visible. Include one deliberately truncated input,
clearly marked invalid. No external images, fonts, library dependencies or copied upstream assets.

Commit generation inputs/code, the four tiny fixtures, and a JSON manifest with filename, validity,
dimensions for valid images, MIME, SHA-256 and original MIT provenance. Include concise README
reproduction instructions. Generation must take an explicit output directory, refuse to overwrite
existing files unless their contents match, and never write outside that selected directory.
The generator is developer tooling, not a GramLab asset API.

Verify byte-identical output in two fresh temporary directories; verify committed files and hashes
match a fresh generation. Run scoped lint/format/typing. Use an available independent image decoder
for valid images if one is already provisioned; otherwise report that check as pending and let the
coordinator browser-decode them. Do not add a dependency just for this task or claim runtime media
acceptance. No bot/guest/APK/build/network acquisition is assigned. Retain clean branch and terminal
resource evidence for coordinator review and merge. Keep ticket claimed until integration and
independent decoding pass; coordinator owns shared docs and native media implementation.
