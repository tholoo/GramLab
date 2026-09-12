# Freeze the atomic album contract

Type: task
Status: ready-for-agent
Work state: resolved
Owner: coordinator
Blocked by: none

The source facts are recorded in [albums-references.md](../../../docs/development/albums-references.md).
The complete proposed local contract is in
[albums-implementation-proposal.md](../../../docs/development/albums-implementation-proposal.md).

Before implementation, obtain explicit choices for the 100,000,000-byte logical aggregate,
World-wide rollback-safe group IDs, bridge-v6 complete-group pagination and grouped-edit scope.
After approval, update the proposal status to frozen, record any chosen alternative verbatim, and
release tickets112–114 in dependency order. This ticket owns only coordinator contract/ticket/docs
work; it does not authorize schema, runtime, Android, guest or build changes.

## Answer

On 2026-09-12 the user approved the complete recommended album contract with grouped edits
deferred. The frozen proposal therefore keeps its exact first-profile fields, repeated-attachment
rules and byte bounds; rollback-safe World-wide group IDs; bridge-v6 complete-group pagination,
split-cursor recovery and one-batch native application; and explicit rejection of grouped edits in
the first slice. No schema, runtime, Android, guest or build change was made in this ticket.
