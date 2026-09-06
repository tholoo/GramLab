# Versioned Bot API update delivery

Status: ready-for-agent
Work state: resolved

Expand the approved Bot API 10.3 compatibility baseline with documented update selection and
negative recovery offsets. Keep authoritative SQLite world state, offline execution and the
current Android adapter. Research the official contract before changing filtering or acknowledgment.
No real accounts, external conformance runs or upstream implementation copying are authorized.

## Acceptance

- Cite the official specification and a resolved official server source revision where available.
- Preserve filter configuration across world/server restarts and distinguish it from queue reads.
- Verify existing queued updates, future events, default/reset filters, invalid requests, negative
  offsets and long-poll interaction through real HTTP and reopened world state.
- Migrate existing worlds without losing identities, pending updates or capabilities.
- State unsupported update types and fidelity limits explicitly; compare actual Android delivery
  through the unchanged adapter where the new configuration affects callbacks.

## Tickets

- [01: Delivery references](issues/01-delivery-references.md)
- [02: Update queue implementation](issues/02-update-queue.md)

Completed the bounded delivery acceptance through pinned reference research, HTTP/world migration
and recovery tests, and the unchanged actual Android adapter. See the
[implementation and limits](../../docs/development/update-delivery.md). The complete Bot API
catalog and wider product goal remain open.
