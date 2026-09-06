"""Exercise developer coordination through real Git worktrees and OS locks."""

import fcntl
import shutil
import subprocess
from pathlib import Path

import pytest

HELPER = Path(__file__).resolve().parents[1] / "tools/worktree"
GIT = shutil.which("git")
assert GIT is not None
TICKET = ".scratch/example/issues/01-work.md"


def git(repo: Path, *args: str) -> str:
    assert GIT is not None
    # Arguments are fixed by these tests; Git operates only on disposable repositories.
    return subprocess.check_output([GIT, "-C", str(repo), *args], text=True).strip()  # noqa: S603


def helper(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    # Invoke the reviewed local helper with test-owned arguments, without shell evaluation.
    return subprocess.run(  # noqa: S603
        [str(HELPER), *args], cwd=repo, text=True, capture_output=True
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "project with spaces"
    root.mkdir()
    git(root, "init", "--initial-branch=main")
    git(root, "config", "commit.gpgsign", "false")
    git(root, "config", "user.name", "Development test")
    git(root, "config", "user.email", "test@example.invalid")
    ticket = root / TICKET
    ticket.parent.mkdir(parents=True)
    ticket.write_text("Work state: open\n")
    git(root, "add", ".")
    git(root, "commit", "-m", "Baseline ticket")
    return root


def test_create_isolated_branch_at_explicit_base(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    (repo / "later.txt").write_text("later change")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "Later work")
    result = helper(repo, "create", "worker", TICKET, base)
    assert result.returncode == 0, result.stderr
    child = repo.with_name(repo.name + "-worker")
    assert git(child, "rev-parse", "HEAD") == base
    assert git(child, "branch", "--show-current") == "task/worker"
    assert not (child / "later.txt").exists()
    assert git(repo, "branch", "--show-current") == "main"
    assert str(child) in helper(repo, "list").stdout
    assert helper(repo, "create", "worker", TICKET).returncode == 2
    assert git(child, "status", "--porcelain") == ""


@pytest.mark.parametrize("problem", ["dirty", "missing-ticket", "invalid-name"])
def test_rejected_setup_does_not_create_branches(repo: Path, problem: str) -> None:
    if problem == "dirty":
        (repo / "pending.txt").write_text("preserve me")
    result = helper(
        repo,
        "create",
        "../escape" if problem == "invalid-name" else "worker",
        ".scratch/example/issues/02-missing.md" if problem == "missing-ticket" else TICKET,
    )
    assert result.returncode != 0
    assert git(repo, "branch", "--format=%(refname:short)") == "main"
    assert len(git(repo, "worktree", "list", "--porcelain").split("worktree ")) == 2
    if problem == "dirty":
        assert (repo / "pending.txt").read_text() == "preserve me"


@pytest.mark.skipif(shutil.which("flock") is None, reason="requires util-linux flock")
def test_lock_is_shared_across_worktrees_and_preserves_exit_status(repo: Path) -> None:
    assert helper(repo, "create", "worker", TICKET).returncode == 0
    child = repo.with_name(repo.name + "-worker")
    assert helper(repo, "lock", "android-gate", "true").returncode == 0
    lock = repo / ".git/gramlab-locks/android-gate.lock"
    marker = child / "command-ran"
    with lock.open("r+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        blocked = helper(child, "lock", "android-gate", "touch", str(marker))
        assert blocked.returncode == 75
        assert not marker.exists()
        assert helper(child, "lock", "independent", "true").returncode == 0
    assert helper(child, "lock", "android-gate", "touch", str(marker)).returncode == 0
    assert marker.exists()
    assert helper(repo, "lock", "android-gate", "bash", "-c", "exit 23").returncode == 23
    assert git(repo, "status", "--porcelain") == ""
