"""Exercise guarded dependency loans in disposable real Git worktrees."""

import hashlib
import importlib.machinery
import importlib.util
import json
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest

HELPER = Path(__file__).resolve().parents[1] / "tools/worktree-dependency"
GIT = shutil.which("git")
assert GIT is not None


def git(repo: Path, *args: str) -> str:
    assert GIT is not None
    return subprocess.check_output([GIT, "-C", str(repo), *args], text=True).strip()  # noqa: S603


def command(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [str(HELPER), *args], cwd=repo, text=True, capture_output=True
    )


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_helper_module() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader("worktree_dependency", str(HELPER))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@dataclass(frozen=True)
class Repository:
    root: Path
    worker: Path
    base: str
    source: str


@pytest.fixture
def repository(tmp_path: Path) -> Repository:
    root = tmp_path / "project with spaces"
    worker = tmp_path / "linked worker"
    root.mkdir()
    git(root, "init", "--initial-branch=main")
    git(root, "config", "commit.gpgsign", "false")
    git(root, "config", "user.name", "Dependency test")
    git(root, "config", "user.email", "test@example.invalid")
    (root / ".gitignore").write_text(".cache/\n")
    (root / "tracked.txt").write_bytes(b"original\x00bytes\n")
    (root / "unrelated.txt").write_text("base\n")
    git(root, "add", ".")
    git(root, "commit", "-m", "Base")
    base = git(root, "rev-parse", "HEAD")
    (root / "tracked.txt").write_bytes(b"borrowed\x00bytes\n")
    executable = root / "new tool.sh"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    git(root, "add", ".")
    git(root, "commit", "-m", "Source")
    source = git(root, "rev-parse", "HEAD")
    git(root, "worktree", "add", "-b", "worker", str(worker), base)
    return Repository(root, worker, base, source)


def install(repo: Repository, receipt: str = "loan") -> subprocess.CompletedProcess[str]:
    return command(
        repo.root,
        "install",
        "--source",
        repo.source,
        "--target",
        str(repo.worker),
        "--receipt",
        receipt,
        "--",
        "tracked.txt",
        "new tool.sh",
    )


def restore(repo: Repository, receipt: str = "loan") -> subprocess.CompletedProcess[str]:
    return command(repo.root, "restore", "--target", str(repo.worker), "--receipt", receipt)


def test_install_and_restore_tracked_and_absent_files_with_receipt(
    repository: Repository,
) -> None:
    (repository.worker / "unrelated.txt").write_text("owned edit\n")
    result = install(repository)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Installed 2 frozen dependencies under receipt loan.\n"
    assert (repository.worker / "tracked.txt").read_bytes() == b"borrowed\x00bytes\n"
    assert (repository.worker / "new tool.sh").read_text() == "#!/bin/sh\nexit 0\n"
    assert stat.S_IMODE((repository.worker / "tracked.txt").stat().st_mode) == 0o644
    assert stat.S_IMODE((repository.worker / "new tool.sh").stat().st_mode) == 0o755
    assert (repository.worker / "unrelated.txt").read_text() == "owned edit\n"

    receipt_dir = repository.worker / ".cache/worktree-dependencies/loan"
    receipt = json.loads((receipt_dir / "receipt.json").read_text())
    assert receipt == {
        "schema": 1,
        "state": "installed",
        "source_commit": repository.source,
        "base_commit": repository.base,
        "target_worktree": str(repository.worker.resolve()),
        "receipt": "loan",
        "entries": [
            {
                "path": "tracked.txt",
                "original": {
                    "mode": "100644",
                    "sha256": digest(b"original\x00bytes\n"),
                    "stored": "original/0",
                },
                "installed": {
                    "mode": "100644",
                    "sha256": digest(b"borrowed\x00bytes\n"),
                    "stored": "installed/0",
                },
            },
            {
                "path": "new tool.sh",
                "original": None,
                "installed": {
                    "mode": "100755",
                    "sha256": digest(b"#!/bin/sh\nexit 0\n"),
                    "stored": "installed/1",
                },
            },
        ],
    }
    assert (receipt_dir / "original/0").read_bytes() == b"original\x00bytes\n"
    assert (receipt_dir / "installed/0").read_bytes() == b"borrowed\x00bytes\n"
    assert (receipt_dir / "installed/1").read_bytes() == b"#!/bin/sh\nexit 0\n"
    assert git(repository.worker, "status", "--porcelain", "--", ".cache") == ""

    result = restore(repository)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Restored 2 frozen dependencies from receipt loan.\n"
    assert (repository.worker / "tracked.txt").read_bytes() == b"original\x00bytes\n"
    assert not (repository.worker / "new tool.sh").exists()
    assert (repository.worker / "unrelated.txt").read_text() == "owned edit\n"
    receipt["state"] = "restored"
    assert json.loads((receipt_dir / "receipt.json").read_text()) == receipt
    repeated = restore(repository)
    assert repeated.returncode == 2
    assert repeated.stderr == "Receipt loan is already restored.\n"


@pytest.mark.parametrize("problem", ["tracked", "untracked", "symlink"])
def test_install_refuses_dirty_or_unsafe_targets_without_partial_changes(
    repository: Repository, problem: str
) -> None:
    target = repository.worker / "tracked.txt"
    if problem == "tracked":
        target.write_text("worker edit\n")
    elif problem == "untracked":
        (repository.worker / "new tool.sh").write_text("worker file\n")
    else:
        target.unlink()
        target.symlink_to(repository.worker / "unrelated.txt")
    result = install(repository)
    assert result.returncode == 2
    assert "Refusing dependency path" in result.stderr
    assert not (repository.worker / ".cache/worktree-dependencies/loan").exists()
    if problem == "tracked":
        assert target.read_text() == "worker edit\n"
        assert not (repository.worker / "new tool.sh").exists()
    elif problem == "untracked":
        assert target.read_bytes() == b"original\x00bytes\n"
        assert (repository.worker / "new tool.sh").read_text() == "worker file\n"
    else:
        assert target.is_symlink()
        assert not (repository.worker / "new tool.sh").exists()


def test_restore_refuses_modified_installed_batch_without_partial_restore(
    repository: Repository,
) -> None:
    assert install(repository).returncode == 0
    (repository.worker / "new tool.sh").write_text("changed after install\n")
    result = restore(repository)
    assert result.returncode == 2
    assert result.stderr == "Installed dependency changed: new tool.sh\n"
    assert (repository.worker / "tracked.txt").read_bytes() == b"borrowed\x00bytes\n"
    assert (repository.worker / "new tool.sh").read_text() == "changed after install\n"
    receipt = json.loads(
        (repository.worker / ".cache/worktree-dependencies/loan/receipt.json").read_text()
    )
    assert receipt["state"] == "installed"


def test_exact_write_preserves_preexisting_temporary_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = load_helper_module()
    target = tmp_path / "target"
    target.write_text("original target\n")
    collision = tmp_path / ".target.worktree-dependency-17"
    collision.write_text("preexisting collision\n")
    monkeypatch.setattr(helper.os, "getpid", lambda: 17)
    with pytest.raises(FileExistsError):
        helper.write_exact(target, b"replacement\n", "100644")
    assert target.read_text() == "original target\n"
    assert collision.read_text() == "preexisting collision\n"


@pytest.mark.parametrize("kind", ["original", "installed"])
def test_restore_rejects_tampered_receipt_bytes_even_with_matching_receipt_hash(
    repository: Repository, kind: str
) -> None:
    assert install(repository).returncode == 0
    directory = repository.worker / ".cache/worktree-dependencies/loan"
    receipt_path = directory / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    tampered = b"tampered receipt bytes\n"
    if kind == "original":
        (directory / "original/0").write_bytes(tampered)
        receipt["entries"][0]["original"]["sha256"] = digest(tampered)
        expected = "Receipt original differs from base commit: tracked.txt\n"
    else:
        (directory / "installed/0").write_bytes(tampered)
        receipt["entries"][0]["installed"]["sha256"] = digest(tampered)
        (repository.worker / "tracked.txt").write_bytes(tampered)
        expected = "Receipt installed differs from source commit: tracked.txt\n"
    receipt_path.write_text(json.dumps(receipt))
    result = restore(repository)
    assert result.returncode == 2
    assert result.stderr == expected
    assert (repository.worker / "tracked.txt").read_bytes() == (
        b"borrowed\x00bytes\n" if kind == "original" else tampered
    )
    assert (repository.worker / "new tool.sh").read_text() == "#!/bin/sh\nexit 0\n"


def test_restore_refuses_accidentally_committed_dependency_without_mutation(
    repository: Repository,
) -> None:
    assert install(repository).returncode == 0
    git(repository.worker, "add", "tracked.txt")
    git(repository.worker, "commit", "-m", "Accidental dependency commit")
    result = restore(repository)
    assert result.returncode == 2
    assert result.stderr == "Committed dependency changed since install: tracked.txt\n"
    assert (repository.worker / "tracked.txt").read_bytes() == b"borrowed\x00bytes\n"
    assert (repository.worker / "new tool.sh").exists()


@pytest.mark.parametrize("path", ["../outside", "/absolute", "nested/../../outside", "a\\b"])
def test_install_rejects_nonportable_or_escaping_paths(repository: Repository, path: str) -> None:
    result = command(
        repository.root,
        "install",
        "--source",
        repository.source,
        "--target",
        str(repository.worker),
        "--receipt",
        "bad-path",
        "--",
        path,
    )
    assert result.returncode == 2
    assert result.stderr == f"Invalid repository-relative path: {path}\n"
    assert not (repository.worker / ".cache/worktree-dependencies/bad-path").exists()


def test_install_rejects_source_symlink_and_tree_modes(repository: Repository) -> None:
    link = repository.root / "link"
    link.symlink_to("tracked.txt")
    tree = repository.root / "tree"
    tree.mkdir()
    (tree / "item").write_text("item\n")
    git(repository.root, "add", "link", "tree/item")
    git(repository.root, "commit", "-m", "Source symlink")
    source = git(repository.root, "rev-parse", "HEAD")
    for path, mode in (("link", "120000"), ("tree", "040000")):
        result = command(
            repository.root,
            "install",
            "--source",
            source,
            "--target",
            str(repository.worker),
            "--receipt",
            "unsupported-" + mode,
            "--",
            path,
        )
        assert result.returncode == 2
        assert result.stderr == f"Unsupported source object mode {mode}: {path}\n"


def test_install_rejects_mutable_source_wrong_repository_and_receipt_collision(
    repository: Repository, tmp_path: Path
) -> None:
    mutable = command(
        repository.root,
        "install",
        "--source",
        "HEAD",
        "--target",
        str(repository.worker),
        "--receipt",
        "mutable",
        "--",
        "tracked.txt",
    )
    assert mutable.returncode == 2
    assert mutable.stderr == "SOURCE must be a complete 40-character commit ID.\n"

    other = tmp_path / "other repository"
    other.mkdir()
    git(other, "init", "--initial-branch=main")
    git(other, "config", "commit.gpgsign", "false")
    git(other, "config", "user.name", "Other")
    git(other, "config", "user.email", "other@example.invalid")
    (other / "file").write_text("other\n")
    git(other, "add", ".")
    git(other, "commit", "-m", "Other")
    wrong = command(
        repository.root,
        "install",
        "--source",
        repository.source,
        "--target",
        str(other),
        "--receipt",
        "wrong",
        "--",
        "tracked.txt",
    )
    assert wrong.returncode == 2
    assert wrong.stderr == "TARGET must be another linked worktree of this repository.\n"

    collision = repository.worker / ".cache/worktree-dependencies/collision"
    collision.mkdir(parents=True)
    marker = collision / "keep"
    marker.write_text("preserve\n")
    occupied = install(repository, "collision")
    assert occupied.returncode == 2
    assert occupied.stderr == "Receipt collision already exists.\n"
    assert marker.read_text() == "preserve\n"
    assert (repository.worker / "tracked.txt").read_bytes() == b"original\x00bytes\n"


def test_restore_prevalidates_missing_and_symlinked_installed_files(repository: Repository) -> None:
    assert install(repository).returncode == 0
    new = repository.worker / "new tool.sh"
    new.unlink()
    new.symlink_to(repository.worker / "unrelated.txt")
    result = restore(repository)
    assert result.returncode == 2
    assert result.stderr == "Installed dependency is not a regular file: new tool.sh\n"
    assert (repository.worker / "tracked.txt").read_bytes() == b"borrowed\x00bytes\n"
    assert new.is_symlink()
