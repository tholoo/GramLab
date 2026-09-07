# Integrate media scenarios with original rendering and public captures

Type: feature
Status: ready-for-agent
Work state: claimed by coordinator
Blocked by: tickets 39/40/41 for combined acceptance; independent probe authoring is available

Coordinator owns `src/gramlab/_android.py`, `src/gramlab/_captures.py`, new media-specific
Android/public capture probes and tests, shared documentation/configuration, source preparation,
APKs, branch merges and combined gates. Follow the shared media contract and TESTING.md.

The production Android runner explicitly selects bridge version 3. GPL config accepts optional
`bridge_version` 2 or 3, defaulting to 2 only for existing legacy configurations. No fallback from
v3 to v2 may discard media. New media scenarios select v3; existing explicit legacy fixtures
remain valid compatibility evidence. Ordinary photo captions must be available to public semantic
captures without treating asset IDs or file metadata as visible text.

Reuse the real-bot worker's three-stage show(config) hook (initial, edited, restart) and final
observe() collector. Strip orchestration-only stage before writing strict native configuration.
Check empty-cache original ordinary/rich image display, live photo edit, cold restart, expected
color/aspect and original PNG/XML/report artifacts alongside full World/API semantics.
Separately exercise native loader interruption, integrity, duplicate/cancel/retry, denied/unknown
assets and old completion after edit. Preserve failed evidence; never substitute a prefilled cache
or manually drawn image for original delivery. Hold common build/guest locks and verify exact
source/APK/profile/import identity before combining any retained gates.

Static fixture/source checks are not native rendering evidence. Finish applicable core/static and
Android gates, update compatibility and handoff with precise limitations, and retain the full
operational milestone (files/albums/emoji/mentions/input remain required).

## Coordinator preparation evidence

The independent local transfer fixture sends complete, truncated, corrupt, redirected, missing and
explicitly gated bodies. Seven guarded real-HTTP checks pass, including changing a snapshot while
an earlier transfer is held partially delivered and denying unauthorized requests without consuming
the planned fault. Scoped Ruff/format and strict typing pass. This validates fault stimuli only;
Android loader cancellation/retry/integrity and original visual acceptance remain incomplete.

The pinned Pillow runtime fully decodes original PNG/JPEG and rejects a truncated JPEG inside
Sandbox. All nine existing runtime boundary checks pass. Core and Android runtime profiles include
the new decoder closure; historical native gates retain their original profile fingerprints.

The public runner photo-capture fixture records the expected pre-media red: the real bot's first
multipart sendPhoto receives `GRAMLAB_UNSUPPORTED: request content type`, with no photo message
published. Coordinator capture traversal now handles ordinary caption text and separate rich-photo
text/credit, and the production Android configuration explicitly selects v3. Source typing and
scoped lint/format pass; combined behavioral green awaits core/native integration. The fault
fixture additionally serves explicit change batches, allowing a real client poll/edit while an
old download remains gated; all seven updated HTTP checks pass.
