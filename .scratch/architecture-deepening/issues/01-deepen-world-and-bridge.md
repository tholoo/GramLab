# Deepen World publication, media-group topology and bridge schema policy

Type: task
Status: ready-for-agent
Work state: claimed
Owner: coordinator
Blocked by: none

Replace the parallel message-creation protocols with one private final-publication module. World
operations retain transaction ownership; the module owns canonical message persistence, events,
revisions, grants and pending bot delivery once content is resolved. Preserve atomic media-group
publication and all existing public results.

Replace repeated media-group validation and change-page reconstruction with one private topology
module used by snapshot, changes and callback delivery. Preserve the frozen bridge-v6 complete-
group, cursor and contiguous revision rules. Grouped edits remain unsupported.

Centralize client bridge schema admission, feature capabilities and semantic envelope construction
in a private World-adjacent module. Keep existing World client methods as stable façades and leave
authentication and HTTP framing in the bridge adapter. Remove bridge access to World private
implementation. Preserve schemas 1–6 exactly.

## Acceptance

- Public World, Bot API and client bridge results remain byte-for-byte equivalent where ordering
  is part of the contract.
- Standalone text, rich, photo and document messages plus media-group members share one private
  publication seam; public rollback tests inject failure only there.
- Snapshot, change-page and callback media-group validation share one topology seam.
- Bridge version meaning has one source and HTTP routing no longer reads World private state.
- Focused World, media, document, media-group, bridge and representative tests pass.
- Strict typing, Ruff and the complete non-Android gate pass; Android execution is not rerun.

## Comments

The user accepted the architecture report's three Strong candidates and all recommended grilling
decisions on 2026-09-12. New modules remain private and use immutable typed records internally;
public dictionary-shaped results and persisted formats remain unchanged.
