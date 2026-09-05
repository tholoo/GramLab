# Keep TL translation in the client and persist one authoritative world

Approved for the foundation prototype on 2026-09-05: use an independently specified semantic JSON
bridge over authenticated local HTTP, with all upstream TL conversion inside the client-derived
adapter, so Python does not acquire a generated upstream schema dependency. Persist each world's
state, ordered events and delivery outbox transactionally in its own SQLite database; keep Android's
database as a recoverable replica and explicitly map world events to client update cursors. This
accepts translation work and initially serialized writes to preserve the licensing boundary and
make bot/client restart recovery testable; public APIs and final replay semantics follow the real
interaction proof in the [approved proposal](../development/android-foundation-proposal.md).
