# Reuse guarded frozen-file dependencies between worker checkouts

Type: tooling
Status: ready-for-agent
Work state: resolved
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

## Worker handoff

Task `frozen-worktree-dependencies`, branch `task/frozen-worktree-dependencies`, assigned base
`27fcc12b979a02614dc7c7d3535e1f3534706c99`. Only this ticket, the new executable, its focused
test and the portable guide change.

The CLI has explicit `install` and `restore` commands. Install requires a complete immutable
commit ID, another linked worktree of the same repository, a unique bounded receipt name and 1-64
canonical repository-relative paths. It accepts only source blobs with Git mode 100644/100755,
caps each file at 64 MiB and the batch at 256 MiB, and prevalidates every target against both
`HEAD` and the index. Tracked files must have exact committed bytes/mode; untracked files must be
absent. Unrelated worker edits remain untouched.

Ignored schema-1 receipt storage retains exact installed bytes, replaced originals, source/base
commits, target, paths, modes and SHA-256 values. Restore validates every receipt blob, installed
target, current `HEAD` and index before mutation. It refuses modified, staged or committed loans
as one batch. Only an exact tool-created file that remains untracked is removed. A successful
receipt remains as `restored`, so repeated restoration is explicit rather than destructive.
Filesystem write failures use retained values for best-effort batch rollback. An incomplete
rollback retains a `failed` receipt and reports that manual inspection is required. The CLI never
resets, cleans, integrates branches, removes worktrees or accesses remotes.

The test suite creates only temporary repositories and real linked worktrees. Its meaningful red
was 13 cases failing because the executable did not yet exist. Final focused verification through
this checkout's pinned default shell initially passed **13 tests in 2.17 seconds**, covering tracked and
absent restore, executable mode, unrelated edits, full-batch dirty/modified/committed refusals,
symlink and traversal rejection, wrong repositories, unsupported Git modes, immutable source IDs,
receipt collision and repeated restore. Retained evidence is ignored at
`artifacts/worktree-dependency.{xml,log}`. Scoped Ruff check/format and strict mypy pass for the
tool and test; Python bytecode compilation, executable-bit verification, `git diff --check` and
the assigned-worktree check pass. No live worker dependency, full gate, native test or guest ran;
all test processes are terminal.

Independent review then found three bounded defects. A pre-existing deterministic temporary-name
collision was unlinked even though this invocation had not created it; restore trusted a receipt
whose stored bytes and hash were edited together instead of comparing them with the recorded Git
commits; and an exception during install rollback could delete the only recovery evidence. The
follow-up makes temporary cleanup ownership explicit, compares installed/original bytes and modes
with the actual source/base Git blobs, and retains a failed receipt when rollback is incomplete.
Focused collision plus original/installed receipt-tampering regressions bring the suite to **16
passing tests**; final retained evidence supersedes the earlier 13-test JUnit.

## Coordinator acceptance

Reviewed frozen tip `8165b429a2d14dda1169caabc7feeb97ae8d6709` is integrated. All 16 real
temporary-worktree tests pass in 2.64 seconds on the merged checkout, with scoped Ruff, format
and strict typing checks passing. CI and contributor commands include the executable. The guide
distinguishes installation failure-state recording from restoration failures, whose retained
receipt may keep its previous state if additional filesystem errors interrupt rollback. No live
worker dependency was installed; the tool does not authorize concurrent edits to borrowed files.
