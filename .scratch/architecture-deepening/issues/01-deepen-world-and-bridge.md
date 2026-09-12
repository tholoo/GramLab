# Deepen World publication, media-group topology and bridge schema policy

Type: task
Status: resolved
Work state: implemented; focused acceptance passed
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

Implementation is split into the three requested reviewable commits:

- `1da28fd` deepens final message publication behind `MessagePublication`; text, rich, photo,
  document and media-group sends share the same final-value publication seam.
- `266d804` concentrates complete media-group validation and album-aware change-page slicing in
  `MediaGroupTopology`.
- `7d169f2` centralizes the version matrix and complete semantic envelopes in
  `ClientBridgeSchema`; the HTTP bridge has no remaining access to World private members.

Focused evidence passes 161 publication/World cases, 19 media-group World cases, 40 complete HTTP
bridge cases in the loopback-only namespace, and 129 schema/World cases including the new 24-case
public version matrix. Scoped Ruff lint/format and strict mypy pass.

The complete non-Android gate was run from the current `tools/dev default --offline` shell inside
the documented outer network namespace. It passes 1,581 tests at 88.61% coverage and has one
failure: `test_contained_scenario_taps_current_semantic_inline_keyboards`. The same test fails at
pre-branch commit `f1a5200`: the CLI retains default bridge v3 while that scenario expects a custom-
emoji callback requiring v4. This branch does not change that default or the unrelated test; follow-
up issue 02 records the baseline decision. Full Ruff lint passes. Full Ruff format reports only the
unchanged pre-branch layout in `tests/test_media_group_runner_v6.py`; all files changed here pass
format checking. Android was not rerun, as agreed.
