# Specify real-bot photo upload, reuse and edit acceptance

Type: feature
Status: ready-for-agent
Work state: claimed
Blocked by: none for authoring/red; green requires ticket 39 integration

Follow [the media contract](../../../docs/development/media-implementation-contract.md).
Own `tests/fixtures/media_bot.py`, `tests/fixtures/media-scene.json`,
`tests/probes/media_round_trip.py`, `tests/test_media_round_trip.py`, and this ticket.
Do not edit production source, existing fixtures/probes, shared docs, dependencies or Android.

Author a real contained stdlib HTTP bot sending multipart PNG/JPEG photos and rich photo blocks,
reusing returned file IDs, downloading and comparing original bytes, editing to a different asset
with mixed Persian/English rich captions, and handling callback/answer after media publication.
Use original committed media assets. Provide a reusable scenario hook for coordinator native
observation at initial/edit/restart stages. Keep bot filesystem isolated from World/control data.

Independently specify complete Bot API responses, World history/events, v3 snapshots/revisions,
retained grants, unchanged old bytes, rejected malformed/foreign reuse and restart equivalence.
Random World/file/callback identities may be captured and checked for stability/scope; do not
copy arbitrary actual fields into expected structures. Include ordinary sendPhoto so renderer
acceptance can compare ordinary and rich delivery. No consumer-specific references or fixtures.

Run a public red under the pinned assigned shell and outer network guard. Until core integration,
report that green is unavailable; do not substitute stubs/fake APIs. Run scoped Ruff/format/mypy.
Coordinator owns combining branches, green suite, native guests and original image/report review.
Commit owned files and return a frozen clean branch with exact failed boundary and terminal
resources. Keep claimed until combined acceptance. No build/guest/full suite assigned.

## Worker evidence

The independent scenario is authored on `task/media-real-bot`. It stages the original committed
16x16 PNG and 64x48 JPEG into the bot's private filesystem, sends ordinary and rich uploads plus
file-ID reuses, verifies Bot API downloads against the original bytes, edits the rich photo,
answers a v3 callback and reopens both local services. The three native observation phases are
`initial`, `edited` and `restart`, each with `bridge_version: 3`.

The required public red was reproduced under the outer loopback-only namespace. The contained bot
receives the current core's real HTTP rejection for its first multipart `sendPhoto`; it exits before
the `published` stage, and the boundary test fails on that nonzero exit. This is the expected ticket
39 integration boundary, not media support. Scoped Ruff format/check and mypy pass for all three
Python files. No Android, build or full-suite gate was run by this worker.

The integration review corrections preserve that exact first-request red boundary. They use the
neutral stored photo block, assert every retained v2 snapshot field and complete v3 change object,
verify admitted callback identities and the full bot update, treat `file_path` as an opaque relative
generated path, repeat `getFile`, and release callback polling only after initial native observation.
