# Deepen current World and client bridge modules

The recent media-group and representative-workflow work exposed three architectural seams whose
policy is spread across callers. Preserve all accepted behavior while concentrating final message
publication, complete media-group topology, and client bridge schema interpretation in private
typed modules.

Public World and HTTP behavior, persisted schema, bridge schemas 1–6, Android fidelity, licensing
separation, and deferred grouped-media edits remain unchanged. The implementation uses one task
branch with one reviewable commit per deepening and no Android guest rerun.
