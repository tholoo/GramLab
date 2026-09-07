# Admit pinned code and preformatted entities inside blockquotes

Type: bug
Status: ready-for-agent
Work state: claimed by coordinator for boundary reproduction
Blocked by: none for reproduction; freeze core/native ownership before parallel implementation

Pinned TDLib `MessageEntity.cpp` at `bc9c263e2bfee06aaab41e82db51a103376030bc`,
`are_entities_valid` lines 1588–1594, permits pre-like entities inside blockquotes. GramLab's
`entities.py` rejects every code/pre overlap, including a containing quote; the GPL bridge in
patch 0006 repeats that rejection. This is an existing nine-entity compatibility discrepancy,
independent of adding HTML parsing or the pending photo architecture.

First reproduce the discrepancy through the public World boundary with independently authored
text and UTF-16 ranges. Then freeze a shared core/native contract before dispatch: ordinary and
expandable quotes may contain code or pre, including identical extents; canonical ordering must
put the containing quote first at equal extents. Preserve code/pre rejection inside emphasis or
other code/pre, code/pre containing quotes, crossing ranges, nested quotes, invalid UTF-16
boundaries and unsupported types. Do not infer that permitting this nesting normalizes arbitrary
HTML or establishes the whole HTML contract.

Implementation acceptance needs complete World/HTTP send/edit, persistence, snapshots/events,
normalized no-op edits, both input orders at equal extents, and unchanged state after rejections.
The native validator must admit the same canonical records while preserving its independent
rejections. Use an actual real-bot original-renderer fixture, exact native serialization,
live edit/cold restart, source preservation, account-free guest isolation and reviewed PNGs.
The coordinator owns shared docs, APK/guest work, combined checks and integration; worker files
and the native follow-up ticket are to be assigned after reproduction. No renderer rewrite,
new entity type, schema version or photo storage/delivery change is authorized by this ticket.

## Reproduction

The coordinator's pinned, network-isolated public World check fails as expected on the current
implementation with `ValueError: Code entities cannot overlap other formatting`. Its independent
input is `Q\ncode\nZ`, an ordinary blockquote at UTF-16 offset 0/length 8, and code at offset
2/length 4. It expects a complete message and persisted history; the exception occurs at entity
validation before insertion. The process is terminal with exit status 1 and its original log is
retained in ignored artifacts. No production code has changed yet. The pinned source contract is
linked from [the HTML findings](../../../docs/development/html-formatting-references.md#gramlab-boundary-and-next-evidence).
