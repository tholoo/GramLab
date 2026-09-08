"""Behavioral checks for immutable archived-APK storage."""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import json
import os
import stat
import subprocess
import types
from pathlib import Path
from typing import Any

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools/artifact-store"


def run_tool(*arguments: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [str(TOOL), *(str(argument) for argument in arguments)],
        text=True,
        capture_output=True,
    )


def load_tool() -> types.ModuleType:
    loader = importlib.machinery.SourceFileLoader("artifact_store", str(TOOL))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def archive(tmp_path: Path) -> tuple[Path, Path, dict[str, bytes]]:
    root = tmp_path / "archive"
    store = tmp_path / "store"
    (root / "one").mkdir(parents=True)
    (root / "two").mkdir()
    store.mkdir()
    values = {
        "one/first.apk": b"same apk bytes\x00",
        "two/second.apk": b"same apk bytes\x00",
        "unique.apk": b"different apk bytes\xff",
    }
    for index, (relative, value) in enumerate(values.items()):
        path = root / relative
        path.write_bytes(value)
        path.chmod(0o640 + index)
        timestamp = 1_700_000_000_000_000_000 + index
        os.utime(path, ns=(timestamp, timestamp))
    return root, store, values


def plan(root: Path, store: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return run_tool("plan", "--archive-root", root, "--store", store, "--output", output)


def apply(
    root: Path, store: Path, plan_path: Path, receipt: Path
) -> subprocess.CompletedProcess[str]:
    return run_tool(
        "apply",
        "--archive-root",
        root,
        "--store",
        store,
        "--plan",
        plan_path,
        "--receipt",
        receipt,
        "--completed-quiescent",
    )


def receipt_events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_plan_and_apply_preserve_every_path_and_byte_with_read_only_shared_objects(
    tmp_path: Path,
) -> None:
    root, store, values = archive(tmp_path)
    plan_path = tmp_path / "plan.json"
    receipt = tmp_path / "receipt.jsonl"

    planned = plan(root, store, plan_path)
    assert planned.returncode == 0, planned.stderr
    manifest = json.loads(plan_path.read_text())
    assert [record["path"] for record in manifest["files"]] == sorted(values)
    metadata = {record["path"]: record for record in manifest["files"]}
    assert {record["mode"] for record in manifest["files"]} == {0o640, 0o641, 0o642}

    applied = apply(root, store, plan_path, receipt)
    assert applied.returncode == 0, applied.stderr
    assert json.loads(applied.stdout)["linked_paths"] == 3
    for relative, value in values.items():
        path = root / relative
        assert path.read_bytes() == value
        assert stat.S_IMODE(path.stat().st_mode) == 0o444
    assert (root / "one/first.apk").stat().st_ino == (root / "two/second.apk").stat().st_ino
    assert (root / "unique.apk").stat().st_ino != (root / "one/first.apk").stat().st_ino
    objects = sorted(store.glob("*.apk"))
    assert len(objects) == 2
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o444 for path in objects)

    events = receipt_events(receipt)
    assert events[0]["event"] == "started"
    assert events[-1] == {"event": "complete", "linked_paths": 3}
    originals = {
        event["path"]: event["original"] for event in events if event["event"] == "prepared"
    }
    assert originals == metadata

    repeated = apply(root, store, plan_path, receipt)
    assert repeated.returncode == 0, repeated.stderr
    assert json.loads(repeated.stdout)["linked_paths"] == 3
    assert receipt_events(receipt) == events


@pytest.mark.parametrize("change", ["content", "mode", "inode"])
def test_apply_rejects_stale_plan_before_creating_objects_or_receipt(
    tmp_path: Path, change: str
) -> None:
    root, store, values = archive(tmp_path)
    plan_path = tmp_path / "plan.json"
    receipt = tmp_path / "receipt.jsonl"
    assert plan(root, store, plan_path).returncode == 0
    first = root / "one/first.apk"
    first_inode = first.stat().st_ino
    changed = root / "two/second.apk"
    if change == "content":
        changed.write_bytes(b"changed after plan")
    elif change == "mode":
        changed.chmod(0o600)
    else:
        replacement = root / "replacement"
        replacement.write_bytes(changed.read_bytes())
        replacement.chmod(stat.S_IMODE(changed.stat().st_mode))
        os.utime(replacement, ns=(changed.stat().st_atime_ns, changed.stat().st_mtime_ns))
        os.replace(replacement, changed)

    result = apply(root, store, plan_path, receipt)
    assert result.returncode == 2
    assert "changed since PLAN" in result.stderr
    assert first.read_bytes() == values["one/first.apk"]
    assert first.stat().st_ino == first_inode
    assert stat.S_IMODE(first.stat().st_mode) == 0o640
    assert list(store.iterdir()) == []
    assert not receipt.exists()


@pytest.mark.parametrize("kind", ["apk", "directory"])
def test_plan_rejects_symlinks_without_following_them(tmp_path: Path, kind: str) -> None:
    root = tmp_path / "archive"
    store = tmp_path / "store"
    outside = tmp_path / "outside"
    root.mkdir()
    store.mkdir()
    outside.mkdir()
    (root / "safe.apk").write_bytes(b"safe")
    if kind == "apk":
        target = outside / "escape.apk"
        target.write_bytes(b"outside")
        (root / "escape.apk").symlink_to(target)
    else:
        (outside / "hidden.apk").write_bytes(b"outside")
        (root / "escape").symlink_to(outside, target_is_directory=True)

    result = plan(root, store, tmp_path / "plan.json")
    assert result.returncode == 2
    assert "Archive contains a symlink" in result.stderr
    assert (outside / ("escape.apk" if kind == "apk" else "hidden.apk")).read_bytes() == b"outside"


def test_plan_rejects_preexisting_unmanaged_hardlinks(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    store = tmp_path / "store"
    root.mkdir()
    store.mkdir()
    first = root / "first.apk"
    first.write_bytes(b"shared elsewhere")
    os.link(first, root / "second.apk")

    result = plan(root, store, tmp_path / "plan.json")
    assert result.returncode == 2
    assert "already has multiple hardlinks" in result.stderr
    assert first.read_bytes() == b"shared elsewhere"


def test_apply_rejects_plan_path_escape_without_mutation(tmp_path: Path) -> None:
    root, store, _ = archive(tmp_path)
    plan_path = tmp_path / "plan.json"
    receipt = tmp_path / "receipt.jsonl"
    assert plan(root, store, plan_path).returncode == 0
    manifest = json.loads(plan_path.read_text())
    manifest["files"][0]["path"] = "../outside.apk"
    plan_path.write_text(json.dumps(manifest))

    result = apply(root, store, plan_path, receipt)
    assert result.returncode == 2
    assert "Unsupported archive-relative APK path" in result.stderr
    assert list(store.iterdir()) == []
    assert not receipt.exists()


def test_apply_rejects_parent_symlink_substitution_after_plan(tmp_path: Path) -> None:
    root, store, _ = archive(tmp_path)
    plan_path = tmp_path / "plan.json"
    receipt = tmp_path / "receipt.jsonl"
    assert plan(root, store, plan_path).returncode == 0
    original = root / "one-original"
    (root / "one").rename(original)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "first.apk").write_bytes((original / "first.apk").read_bytes())
    (root / "one").symlink_to(outside, target_is_directory=True)

    result = apply(root, store, plan_path, receipt)
    assert result.returncode == 2
    assert "Archive contains a symlink" in result.stderr
    assert (outside / "first.apk").read_bytes() == b"same apk bytes\x00"
    assert list(store.iterdir()) == []
    assert not receipt.exists()


def test_parent_substitution_during_apply_cannot_redirect_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = load_tool()
    root = tmp_path / "archive"
    store = tmp_path / "store"
    nested = root / "nested"
    nested.mkdir(parents=True)
    store.mkdir()
    (nested / "client.apk").write_bytes(b"archived")
    plan_path = tmp_path / "plan.json"
    receipt = tmp_path / "receipt.jsonl"
    helper.plan_archive(root, store, plan_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "client.apk").write_bytes(b"outside")
    saved = tmp_path / "saved"
    actual_append = helper.Journal.append
    substituted = False

    def substitute(self: Any, value: dict[str, Any]) -> None:
        nonlocal substituted
        actual_append(self, value)
        if value.get("event") == "prepared" and not substituted:
            nested.rename(saved)
            nested.symlink_to(outside, target_is_directory=True)
            substituted = True

    monkeypatch.setattr(helper.Journal, "append", substitute)
    with pytest.raises(helper.Refusal, match="changed or is unsafe"):
        helper.apply_archive(root, store, plan_path, receipt, confirmed_quiescent=True)
    assert (outside / "client.apk").read_bytes() == b"outside"
    assert (saved / "client.apk").read_bytes() == b"archived"
    assert not (outside / ".client.apk.artifact-store-link").exists()


def test_apply_rejects_preexisting_content_object_collision(tmp_path: Path) -> None:
    root, store, values = archive(tmp_path)
    plan_path = tmp_path / "plan.json"
    receipt = tmp_path / "receipt.jsonl"
    assert plan(root, store, plan_path).returncode == 0
    manifest = json.loads(plan_path.read_text())
    digest = manifest["files"][0]["sha256"]
    collision = store / f"{digest}.apk"
    collision.write_bytes(b"not the planned object")
    collision.chmod(0o444)

    result = apply(root, store, plan_path, receipt)
    assert result.returncode == 2
    assert "unsafe metadata" in result.stderr or "does not match its name" in result.stderr
    assert (root / "one/first.apk").read_bytes() == values["one/first.apk"]
    assert not receipt.exists()


def test_apply_rejects_unmanaged_staging_link_before_mutation(tmp_path: Path) -> None:
    helper = load_tool()
    root = tmp_path / "archive"
    store = tmp_path / "store"
    root.mkdir()
    store.mkdir()
    artifact = root / "client.apk"
    artifact.write_bytes(b"immutable apk")
    original_inode = artifact.stat().st_ino
    plan_path = tmp_path / "plan.json"
    receipt = tmp_path / "receipt.jsonl"
    helper.plan_archive(root, store, plan_path)
    record = json.loads(plan_path.read_text())["files"][0]
    canonical = store / f"{record['sha256']}.apk"
    canonical.write_bytes(artifact.read_bytes())
    canonical.chmod(0o444)
    staged = root / helper.staging_name("client.apk")
    os.link(canonical, staged)

    with pytest.raises(helper.Refusal, match="temporary path collision"):
        helper.apply_archive(root, store, plan_path, receipt, confirmed_quiescent=True)
    assert artifact.stat().st_ino == original_inode
    assert artifact.read_bytes() == b"immutable apk"
    assert staged.exists()
    assert not receipt.exists()


def test_apply_rejects_premature_complete_receipt_before_mutation(tmp_path: Path) -> None:
    helper = load_tool()
    root = tmp_path / "archive"
    store = tmp_path / "store"
    root.mkdir()
    store.mkdir()
    artifact = root / "client.apk"
    artifact.write_bytes(b"immutable apk")
    original_inode = artifact.stat().st_ino
    plan_path = tmp_path / "plan.json"
    receipt = tmp_path / "receipt.jsonl"
    helper.plan_archive(root, store, plan_path)
    header = {
        "event": "started",
        "schema": helper.SCHEMA,
        "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "archive_root": str(root.resolve()),
        "store": str(store.resolve()),
    }
    receipt.write_text(
        "\n".join(json.dumps(event) for event in (header, {"event": "complete", "linked_paths": 1}))
        + "\n"
    )

    with pytest.raises(helper.Refusal, match="invalid completion"):
        helper.apply_archive(root, store, plan_path, receipt, confirmed_quiescent=True)
    assert artifact.stat().st_ino == original_inode
    assert artifact.read_bytes() == b"immutable apk"
    assert list(store.iterdir()) == []
    assert len(receipt_events(receipt)) == 2


def test_apply_supports_maximum_length_apk_basename(tmp_path: Path) -> None:
    helper = load_tool()
    root = tmp_path / "archive"
    store = tmp_path / "store"
    root.mkdir()
    store.mkdir()
    artifact = root / ("z" * 251 + ".apk")
    artifact.write_bytes(b"immutable apk")
    plan_path = tmp_path / "plan.json"
    receipt = tmp_path / "receipt.jsonl"
    helper.plan_archive(root, store, plan_path)

    result = helper.apply_archive(root, store, plan_path, receipt, confirmed_quiescent=True)
    assert result["linked_paths"] == 1
    assert artifact.read_bytes() == b"immutable apk"
    assert artifact.stat().st_ino == next(store.glob("*.apk")).stat().st_ino
    assert not (root / helper.staging_name(artifact.name)).exists()


def test_create_only_manifest_write_preserves_a_collision(tmp_path: Path) -> None:
    helper = load_tool()
    collision = tmp_path / "plan.json"
    collision.write_bytes(b"other writer")
    with pytest.raises(FileExistsError):
        helper.create_file(collision, b"planned")
    assert collision.read_bytes() == b"other writer"


@pytest.mark.parametrize("moment", ["before", "after"])
def test_interrupted_atomic_replacement_is_readable_and_resumable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, moment: str
) -> None:
    helper = load_tool()
    root = tmp_path / "archive"
    store = tmp_path / "store"
    root.mkdir()
    store.mkdir()
    artifact = root / "client.apk"
    artifact.write_bytes(b"immutable apk")
    artifact.chmod(0o640)
    plan_path = tmp_path / "plan.json"
    receipt = tmp_path / "receipt.jsonl"
    helper.plan_archive(root, store, plan_path)
    original_inode = artifact.stat().st_ino
    actual_replace = helper.replace_atomic

    def interrupt(parent: int, source: str, destination: str) -> None:
        if moment == "after":
            actual_replace(parent, source, destination)
        raise RuntimeError(f"interrupted {moment} replacement")

    monkeypatch.setattr(helper, "replace_atomic", interrupt)
    with pytest.raises(RuntimeError, match=f"interrupted {moment}"):
        helper.apply_archive(root, store, plan_path, receipt, confirmed_quiescent=True)
    assert artifact.read_bytes() == b"immutable apk"
    if moment == "before":
        assert artifact.stat().st_ino == original_inode
        assert stat.S_IMODE(artifact.stat().st_mode) == 0o640
    else:
        assert artifact.stat().st_ino != original_inode
        assert stat.S_IMODE(artifact.stat().st_mode) == 0o444
    assert receipt_events(receipt)[-1]["event"] == "prepared"

    monkeypatch.setattr(helper, "replace_atomic", actual_replace)
    resumed = helper.apply_archive(root, store, plan_path, receipt, confirmed_quiescent=True)
    assert resumed["linked_paths"] == 1
    assert artifact.read_bytes() == b"immutable apk"
    assert stat.S_IMODE(artifact.stat().st_mode) == 0o444
    assert not (root / ".client.apk.artifact-store-link").exists()
    assert receipt_events(receipt)[-1] == {"event": "complete", "linked_paths": 1}


def test_interrupted_object_publication_gets_a_recovered_receipt_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = load_tool()
    root = tmp_path / "archive"
    store = tmp_path / "store"
    root.mkdir()
    store.mkdir()
    artifact = root / "client.apk"
    artifact.write_bytes(b"immutable apk")
    plan_path = tmp_path / "plan.json"
    receipt = tmp_path / "receipt.jsonl"
    helper.plan_archive(root, store, plan_path)
    actual_append = helper.Journal.append

    def interrupt(self: Any, value: dict[str, Any]) -> None:
        if value.get("event") == "object":
            raise RuntimeError("interrupted before object receipt")
        actual_append(self, value)

    monkeypatch.setattr(helper.Journal, "append", interrupt)
    with pytest.raises(RuntimeError, match="before object receipt"):
        helper.apply_archive(root, store, plan_path, receipt, confirmed_quiescent=True)
    assert artifact.read_bytes() == b"immutable apk"
    assert receipt_events(receipt)[-1]["event"] == "started"
    assert len(list(store.glob("*.apk"))) == 1

    monkeypatch.setattr(helper.Journal, "append", actual_append)
    helper.apply_archive(root, store, plan_path, receipt, confirmed_quiescent=True)
    object_events = [event for event in receipt_events(receipt) if event["event"] == "object"]
    assert len(object_events) == 1
    assert object_events[0]["recovered"] is True
    assert receipt_events(receipt)[-1] == {"event": "complete", "linked_paths": 1}


def test_plan_and_receipt_bounds_are_checked_before_archive_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = load_tool()
    root, store, values = archive(tmp_path)
    oversized_plan = tmp_path / "oversized-plan.json"
    monkeypatch.setattr(helper, "MAX_MANIFEST_BYTES", 200)
    with pytest.raises(helper.Refusal, match="PLAN would exceed"):
        helper.plan_archive(root, store, oversized_plan)
    assert not oversized_plan.exists()

    monkeypatch.setattr(helper, "MAX_MANIFEST_BYTES", 16 * 1024 * 1024)
    plan_path = tmp_path / "plan.json"
    helper.plan_archive(root, store, plan_path)
    monkeypatch.setattr(helper, "MAX_MANIFEST_BYTES", plan_path.stat().st_size)
    receipt = tmp_path / "receipt.jsonl"
    with pytest.raises(helper.Refusal, match="Complete RECEIPT would exceed"):
        helper.apply_archive(root, store, plan_path, receipt, confirmed_quiescent=True)
    assert not receipt.exists()
    assert list(store.iterdir()) == []
    assert {relative: (root / relative).read_bytes() for relative in values} == values


def test_apply_requires_explicit_quiescent_archive_confirmation(tmp_path: Path) -> None:
    root, store, _ = archive(tmp_path)
    plan_path = tmp_path / "plan.json"
    receipt = tmp_path / "receipt.jsonl"
    assert plan(root, store, plan_path).returncode == 0

    result = run_tool(
        "apply",
        "--archive-root",
        root,
        "--store",
        store,
        "--plan",
        plan_path,
        "--receipt",
        receipt,
    )
    assert result.returncode == 2
    assert "--completed-quiescent" in result.stderr
    assert list(store.iterdir()) == []
    assert not receipt.exists()
