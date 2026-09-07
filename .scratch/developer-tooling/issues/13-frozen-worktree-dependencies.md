# Reuse guarded frozen-file dependencies between worker checkouts

Type: tooling
Status: ready-for-agent
Work state: open
Blocked by: none

Own this ticket and new executable `tools/worktree-dependency`, new
`tests/test_worktree_dependency.py`, and `docs/development/worktree-dependencies.md`.
Do not edit tools/worktree, shared workflow/agent guidance, production, lockfiles or other tests.
Coordinator will link the guide after review. The user authorized reusable developer tooling.

The coordinator currently lends a frozen dependency file to a worker by manually checking its
base bytes, copying an exact Git blob, recording both hashes in ignored local notes, and restoring
the base after checks. Make that operation concrete and reusable; do not introduce automatic
branch integration or let workers commit borrowed dependencies.

Implement an explicit coordinator CLI to install a finite list of repo-relative regular files
from an immutable commit into another linked worktree of the same repository, and restore them
using an ignored receipt. Resolve the source commit exactly. Permit clean target files whose
bytes/mode match HEAD, or absent untracked files; refuse dirty targets, symlinks, escaping paths,
wrong repositories, existing receipts and unsupported Git object modes. Preserve every original
byte and mode and record source/base commit, installed/original hashes and paths in ignored local
receipt storage. Never commit machine-specific receipt data or source copies.

Restore only when every selected current file still matches its installed bytes/mode and the
worktree's committed version of each target remains the original version. Refuse changed or
accidentally committed dependencies without altering any target. Validate the entire batch before
mutating and retain installed bytes in the ignored receipt as evidence; removal is restricted to
exact tool-created still-untracked files. Detect already restored receipts. No git reset/clean,
branch merge/cherry-pick or automatic worktree deletion. Operations should not require a clean
whole worker checkout: unrelated owned edits remain untouched.

Prove behavior in real temporary linked Git worktrees: tracked replacement+absent-file restore,
unrelated edits preserved, dirty/committed/modified-installed refusal without partial restore,
symlink/traversal/wrong-repository rejection, immutable commit/receipt collision and repeated restore.
Use precise error messages and portable usage docs. Prefer Python stdlib and Git already present
in the development shell; add no runtime dependency. Run focused tests, Ruff/format/strict typing
and executable syntax as appropriate, retaining JUnit/logs. Do not install a dependency into live
workers as part of tests; coordinator owns real uses after review. Return frozen clean tip and
all test processes terminal.
