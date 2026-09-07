# Observe original photo controls and receiver bindings

Type: feature
Status: ready-for-agent
Work state: claimed by media-view-observer worker
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


## Worker handoff

Patch 0020 adds `GramLabPhotoObserver` and one initialization call in `GramLabRuntime`.
The call runs after loading and validating the snapshot/binding, before publishing Runtime's
snapshot reference. Absent activation creates no observer, executor thread or view listener.
Present activation first removes old result/temporary files, then checks the six exact field
names, JSON types, nonce, World/persona, visible snapshot peer, and one to eight distinct
positive native message IDs. Invalid input rejects startup through the existing runtime boundary.

Available results use the frozen fields and message ordering. `cell_bounds` uses the original
cell's screen origin/width/height; `visible_bounds` converts the original global visible rectangle
from root to screen coordinates. ImageReceiver coordinates and a copied radial progress rectangle
use the cell's screen origin plus `getPaddingTopAnimated()` for Y, matching the original canvas
translation. `image_key` is `getImageKey()`, `has_image` is `hasImageLoaded()` (full image/media
Drawable, excluding thumb/key-only state), and icon/progress use the original radial getters.
Only exact original, ungrouped, non-spoiler ordinary-photo cells qualify. Active cell transitions,
nonidentity view matrices, scroll transforms, partial alpha and clipped progress controls reject.
View-tree traversal is bounded to 4,096 views and depth 64. No reflection, rendering replacement,
input dispatch, exported component, manifest change or endpoint is introduced.

Unavailable results have empty messages and explicit reasons: `awaiting_activity`,
`activity_paused`, `activity_destroyed`, `inactive_window`, `message_not_unique_or_visible`,
`unsupported_cell_subclass`, `unsupported_photo`, `unsupported_transform`, `clipped_control`,
`invalid_bounds`, `invalid_progress`, `hierarchy_limit`, or `observation_unavailable`.
Sampling occurs after drawing with at least 50 ms between samples. An opt-in delayed invalidation
requests fresh original frames even when quiet. The writer has at most one active and one latest
pending result; skipped generations are expected. It publishes by same-directory atomic move
outside the UI thread. Lifecycle detach removes draw listeners and pending UI callbacks.

The immutable normal19 `GramLabRuntime.java` preimage SHA-256 is
`3f9c1bc8e001a15766f58b70c0ca23e320e5b2cc7753c1ec7b64062d4acbb744`.
Apply the patch to a fresh copy with `patch --batch --fuzz=0 -p1`; both reconstructed sources
match the private modified sources exactly, without offsets or fuzz. `git diff --check` passes.
Public getter signatures and original canvas/input coordinate handling were checked against the
pinned source. No APK, compilation or guest was assigned or run: these are source checks only.
Coordinator must integrate the patch series/manifest and prove absent/wrong activation, current
identity/generation/age, original control tapping, shared consumers and late completion natively.
Visibility rectangles do not establish absence of overlaid windows; screenshots and current
native state remain required. This diagnostic result never authorizes stale input.
