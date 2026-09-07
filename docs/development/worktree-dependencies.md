# Frozen worktree dependencies

`tools/worktree-dependency` lets a coordinator temporarily place exact files from one immutable
commit into another linked worktree of the same repository. It is intended for a worker whose
owned change depends on a coordinator-owned fix that is already reviewed but is not part of the
worker's assigned base. The tool does not integrate branches or authorize the worker to commit the
borrowed files.

Run it from the coordinator checkout or another linked checkout, not from the target itself. Give
it the complete 40-character source commit ID, the target worktree root, a unique receipt name and
between one and 64 repository-relative file paths:

```sh
tools/worktree-dependency install \
  --source 8e076158b9a38da682d814780ac3f2bb747ab68d \
  --target /path/to/GramLab-worktrees/custom-emoji-real-bot \
  --receipt ticket-63-world \
  -- src/gramlab/world.py
```

The source must be an existing commit object; branch names, tags and abbreviated IDs are refused.
Each source path must be a regular Git blob with mode `100644` or `100755` and at most 64 MiB. A
batch may contain at most 256 MiB. Paths must use canonical forward-slash repository syntax, and
their parent directories must already be real directories in the target.

Before writing anything, install validates the whole batch. A tracked target must have the exact
bytes and executable mode recorded by its current `HEAD`, and its index entry must match `HEAD`.
An untracked target must be absent. Symlinks, directories, staged paths, dirty files, duplicate or
escaping paths, another repository, the invoking worktree itself and an existing receipt all cause
exit status 2 without changing any requested target. Unrelated worktree edits do not prevent an
install and remain untouched.

The receipt is stored under the target's ignored
`.cache/worktree-dependencies/<receipt>/` directory. `receipt.json` records schema and state,
canonical source and base commits, the target root, paths, modes and SHA-256 values. Separate
`installed/` files retain every installed byte; `original/` files retain every replaced byte.
Receipt storage must be ignored by the target repository and may not contain symlinks. This local
evidence can include machine paths and must never be added to Git.

Run the worker's focused checks while the receipt remains installed. Inspect `git status` before
restore so a borrowed dependency is not staged or committed. Restore from a different linked
checkout of the same repository:

```sh
tools/worktree-dependency restore \
  --target /path/to/GramLab-worktrees/custom-emoji-real-bot \
  --receipt ticket-63-world
```

Restore again validates the entire batch before changing a file. Every target must still match the
installed receipt bytes and mode. Every tracked path's current `HEAD` and index entry must still
match its original version; every tool-created path must still be untracked and absent from
`HEAD`. Receipt evidence must also match its recorded hashes. A modified, staged, committed,
missing or symlinked dependency refuses the whole restore, leaving all targets available for
inspection. Exact tool-created untracked files are removed; tracked files regain their original
bytes and mode.

After success the receipt remains with state `restored`, preserving the evidence and making a
repeated restore fail explicitly. Keep it through worker handoff or copy needed facts into the
ticket, then remove the ignored receipt manually when it is no longer needed. Use a new receipt
name for a later loan. Confirm the worker's final commit contains only owned files before merging.

The tool never runs `git reset`, `git clean`, merge, rebase, cherry-pick, worktree removal or a
remote Git operation. A filesystem write failure triggers a best-effort rollback to the retained
batch bytes and exits with an error; inspect the receipt and target before retrying after such an
external failure.
