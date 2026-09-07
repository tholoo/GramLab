# Observe original photo controls and receiver bindings

Type: feature
Status: ready-for-agent
Work state: open
Blocked by: none

Own this ticket and new `clients/android/patches/0020-photo-view-observation.patch` only.
Coordinator owns series/manifest integration, source preparation, builds, Python acceptance and
shared docs. Add a bounded opt-in read-only observation seam inside the GPL adapter. Preserve
original rendering and input; no reflective private fields, synthetic action dispatch, new
network endpoints, exported components or changes to original renderer classes.

Freeze the following private diagnostic contract for independent native acceptance:
- Activation file: app-private `files/gramlab/photo-observation.json`, exactly schema (1), nonce
  (1–64 ASCII letters/digits/underscore/hyphen), world_id, user_id, peer_id and message_ids
  (one to eight distinct positive integers). Validate exact types and snapshot world/persona.
- Absent activation installs nothing. Invalid activation rejects startup. Delete an old result
  before installing; never silently reuse it across a process lifetime.
- Result: `photo-observation-result.json`, atomically published outside the UI thread; schema,
  nonce, world_id, user_id, peer_id, pid, generation, uptime_ms, available, reason, messages.
  `reason` is null on availability. `messages` is ordered like message_ids, each with message_id,
  cell_bounds, visible_bounds, image_bounds, progress_bounds (screen-coordinate arrays),
  image_key (nullable string), has_image (boolean), progress_icon (integer), progress (number).
- Observe visible unique original ChatMessageCell instances by dialog/message IDs on UI thread
  after draw. Use existing public ImageReceiver/RadialProgress getters. Report unavailable for
  missing/duplicate/unsupported transforms or clipped control; do not fabricate rectangles.
  Unavailable messages is empty. Use explicit reasons, including awaiting_activity and
  message_not_unique_or_visible. Observe at most every 50 ms, avoiding unbounded writer backlog.
- Installation hooks into GramLabRuntime after loaded snapshot initialization. Observation is
  diagnostic only; the consumer must verify identity, generation, age and current native state
  before ordinary guest input. It is not a public target, action API or atomic input guarantee.

Inspect the pinned prepared source for exact getter semantics. The existing separately licensed
rich-action experiment supplies lifecycle/atomic-write precedent but retains a distinct contract.
Read licensing/upstream docs before source adaptation. Use the already approved normal19 source
as a read-only reference; author a zero-fuzz patch against it in worker-owned scratch output.
Verify patch applicability and review exact scope, but do not build or run a guest. Send exact
field/getter mappings and known limitations for coordinator's independent acceptance. Keep branch
frozen on handoff. Native tests must verify observed original cancellation/retry and stable image
bindings after out-of-order completion; source review alone does not establish those outcomes.
