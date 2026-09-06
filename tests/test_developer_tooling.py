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
    child = repo.with_name(repo.name + "-worktrees") / "worker"
    assert git(child, "rev-parse", "HEAD") == base
    assert git(child, "branch", "--show-current") == "task/worker"
    assert not (child / "later.txt").exists()
    assert git(repo, "branch", "--show-current") == "main"
    assert str(child) in helper(repo, "list").stdout
    assert helper(repo, "create", "worker", TICKET).returncode == 2
    assert git(child, "status", "--porcelain") == ""


def test_linked_checkout_uses_same_container_and_checks_assignment(repo: Path) -> None:
    assert helper(repo, "create", "first", TICKET).returncode == 0
    container = repo.with_name(repo.name + "-worktrees")
    first = container / "first"
    assert helper(first, "root").stdout.strip() == str(container)
    assert helper(first, "check", "first").returncode == 0
    assert helper(repo, "check", "first").returncode == 2
    assert helper(first, "check", "second").returncode == 2
    assert helper(first, "create", "second", TICKET).returncode == 0
    assert git(container / "second", "branch", "--show-current") == "task/second"
    git(first, "switch", "--detach")
    assert helper(first, "check", "first").returncode == 2


def test_hidden_untracked_work_prevents_creation(repo: Path) -> None:
    git(repo, "config", "status.showUntrackedFiles", "no")
    (repo / "pending.txt").write_text("preserve me")
    assert helper(repo, "create", "worker", TICKET).returncode == 2
    assert git(repo, "branch", "--format=%(refname:short)") == "main"
    assert (repo / "pending.txt").read_text() == "preserve me"


@pytest.mark.parametrize(
    "occupied", ["directory", "file", "symlink", "container-symlink", "branch"]
)
def test_existing_resources_are_preserved(repo: Path, occupied: str) -> None:
    container = repo.with_name(repo.name + "-worktrees")
    destination = container / "worker"
    if occupied == "container-symlink":
        container.symlink_to(repo, target_is_directory=True)
    elif occupied == "branch":
        git(repo, "branch", "task/worker")
    else:
        container.mkdir()
        if occupied == "symlink":
            destination.symlink_to(repo / "absent")
        elif occupied == "file":
            destination.write_text("preserve me")
        else:
            destination.mkdir()
            (destination / "keep.txt").write_text("preserve me")
    assert helper(repo, "create", "worker", TICKET).returncode == 2
    assert len(git(repo, "worktree", "list", "--porcelain").split("worktree ")) == 2
    if occupied == "directory":
        assert (destination / "keep.txt").read_text() == "preserve me"
    elif occupied == "file":
        assert destination.read_text() == "preserve me"
    elif occupied == "symlink":
        assert destination.is_symlink()
    elif occupied == "container-symlink":
        assert container.is_symlink()
    else:
        assert git(repo, "rev-parse", "task/worker") == git(repo, "rev-parse", "HEAD")


def test_ticket_must_exist_at_selected_base(repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    ticket = ".scratch/example/issues/02-new.md"
    (repo / ticket).write_text("Work state: open\n")
    git(repo, "add", ticket)
    git(repo, "commit", "-m", "New ticket")
    assert helper(repo, "create", "worker", ticket, base).returncode == 2
    assert git(repo, "branch", "--format=%(refname:short)") == "main"


@pytest.mark.parametrize(
    "problem", ["dirty", "tracked", "staged", "missing-ticket", "invalid-name"]
)
def test_rejected_setup_does_not_create_branches(repo: Path, problem: str) -> None:
    if problem == "dirty":
        (repo / "pending.txt").write_text("preserve me")
    elif problem in {"tracked", "staged"}:
        (repo / TICKET).write_text("preserve me")
        if problem == "staged":
            git(repo, "add", TICKET)
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
    elif problem in {"tracked", "staged"}:
        assert (repo / TICKET).read_text() == "preserve me"


@pytest.mark.skipif(shutil.which("flock") is None, reason="requires util-linux flock")
def test_lock_is_shared_across_worktrees_and_preserves_exit_status(repo: Path) -> None:
    assert helper(repo, "create", "worker", TICKET).returncode == 0
    child = repo.with_name(repo.name + "-worktrees") / "worker"
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
