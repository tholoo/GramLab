# Update selection and tail recovery

`getUpdates` now accepts persistent `allowed_updates` selections and negative offsets against the
existing Bot API 10.3 baseline. The [pinned reference review](update-delivery-references.md)
distinguishes documented behavior from source-level qualifications. GramLab generates private
text-message and callback-query updates; accepting other subscription names does not implement
their underlying operations.

## Selection and persistence

`allowed_updates` is a JSON array, either in a JSON request or serialized as a form/query parameter.
Omission retains the bot's current selection. An empty array restores defaults. Known names are
case-insensitive, duplicates collapse, and unknown names are ignored. An all-unknown array also
restores defaults. The default excludes `chat_member`, `message_reaction` and
`message_reaction_count`; neither of GramLab's currently generated types is excluded.

A malformed filter value leaves the selection alone and still performs the poll, including its
offset acknowledgment. This covers malformed serialized JSON, non-arrays and arrays containing
non-string elements. A malformed overall request, invalid integer, unsupported parameter or wrong
capability still fails before changing delivery state. Existing stricter request validation remains.

Selection applies when a future world event would enter the bot's queue. It does not remove
previously queued updates, hide client messages or suppress authoritative world events. Excluded
events consume no update IDs. Callback actions remain durable even if delivery is excluded;
retrying the same action after resetting the filter does not create another callback notification.

Storage version 4 adds the selection to each bot. Atomic migration from earlier supported formats
preserves world identity, messages, callbacks, pending delivery and capability hashes. Concurrent
openers recheck the version after acquiring the writer lock. Selection and enqueueing use the
same SQLite writer ordering. The public world/client snapshot schemas and Android adapter remain
unchanged. A world/server restart retains the selection; it is scoped to one bot in one world.

## Negative offsets

An offset of `-N` keeps the last N queued updates by count and forgets older entries. The response
then applies `limit` from the beginning of that retained suffix. For example, with update IDs
1–4 pending, offset -2 and limit 1 returns ID 3 while keeping IDs 3 and 4 pending. Returned updates
are acknowledged only by a later higher offset. Fewer than N pending entries retains the entire
queue. This operation does not delete messages from chat history or alter another bot's queue.

A negative offset is applied once before a long-poll wait. If the initial queue is empty, later
arrivals are read normally; repeatedly trimming them would lose updates. Filter changes likewise
apply only at the initial read. The existing monotonic timeout and bounded reread strategy remain.

## Behavioral evidence and limits

[HTTP/world tests](../../tests/test_update_delivery.py) check complete delivery envelopes, pending
rows across filter changes and restarts, default resets, malformed values, query/JSON/form encoding,
scope isolation, callback deduplication, sparse-queue suffixes and limits, later selection changes,
waiting arrivals and migration.
A test-only scheduling barrier pauses a real empty queue read while two subsequent messages arrive;
it detects repeated negative trimming without relying on a guessed sleep. The initial regression
run rejected filters and negative offsets. The legacy capability fixture was corrected to use the
existing synthetic token format before its preservation check could test migration.

The [recovery example](../../examples/recovery/scenario.py) now sends a user message after the bot
subscribes only to callbacks. That message remains in client history. Its actual inline tap reaches
the bot as update 2, survives a bot hard stop before acknowledgment, and is handled by the replacement
without resetting the subscription. Simulation and Android tests compare the same resulting state;
the headless case additionally requires the filtered message to be visible in an original capture.

This remains a bounded polling implementation. GramLab rejects malformed integers and invalid
limits instead of reproducing the server's permissive parsing/clamping. Every newer valid same-bot
poll cancels an outstanding poll in the same server; the pinned server only does so when the new
request enters a wait. Positive offsets retain GramLab's deletion of lower IDs, including arrivals
during a wait; the pinned server also has distance-dependent queue-error fallback that is not
implemented. Expiry, webhook coordination, flood/backoff timing and distributed poll ownership
remain unsupported. These differences prevent a claim of exact server conformance.

Run the [required offline gates](../../CONTRIBUTING.md). Generated reports, screenshots, logs and
local execution details stay in ignored artifacts. No upstream implementation was copied into the
MIT core, and no external conformance service or Telegram account was used.

Final verification passes 179 core tests at 82.16% measured coverage and all 19 Android tests.
The Android collection predates two additional core-only regressions (177 deselected). Strict
typing across 47 files, lint/format, Nix/workflow checks, offline distributions and privacy/local
links pass. Original before/after images were inspected; the self-contained report loads both
at desktop/mobile widths without overflow or external resources. The approved APK is unchanged.
