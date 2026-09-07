# Specify real-bot photo upload, reuse and edit acceptance

Type: feature
Status: ready-for-agent
Work state: open
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
