"""Checks for bounded private Android patch staging."""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import json
import stat
import subprocess
import sys
import time
import types
from pathlib import Path
from typing import Any

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools/android-patch-stage"


def load_tool() -> types.ModuleType:
    loader = importlib.machinery.SourceFileLoader("android_patch_stage", str(TOOL))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_manifest(path: Path, values: dict[str, bytes]) -> None:
    path.write_text(json.dumps({name: sha(value) for name, value in values.items()}))


def invoke(
    source: Path, patch: Path, before: Path, after: Path, output: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [
            str(TOOL),
            "--source",
            str(source),
            "--patch",
            str(patch),
            "--before-sha256",
            str(before),
            "--after-sha256",
            str(after),
            "--output",
            str(output),
        ],
        text=True,
        capture_output=True,
    )


def fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path, dict[str, bytes]]:
    source = tmp_path / "source"
    existing = source / "app/Main.java"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"class Main {\n    int value = 1;\n}\n")
    patch = tmp_path / "change.patch"
    patch.write_text(
        """diff --git a/app/Main.java b/app/Main.java
index 1111111..2222222 100644
--- a/app/Main.java
+++ b/app/Main.java
@@ -1,3 +1,3 @@
 class Main {
-    int value = 1;
+    int value = 2;
 }
diff --git a/new/Added.java b/new/Added.java
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/new/Added.java
@@ -0,0 +1 @@
+class Added {}
"""
    )
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    original = {"app/Main.java": existing.read_bytes()}
    expected = {
        "app/Main.java": b"class Main {\n    int value = 2;\n}\n",
        "new/Added.java": b"class Added {}\n",
    }
    write_manifest(before, original)
    write_manifest(after, expected)
    return source, patch, before, after, expected


def source_snapshot(source: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.relative_to(source).as_posix(): (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
        for path in source.rglob("*")
        if path.is_file()
    }


def test_stages_exact_existing_and_new_postimages_without_changing_source(tmp_path: Path) -> None:
    source, patch, before, after, expected = fixture(tmp_path)
    unchanged = source_snapshot(source)
    output = tmp_path / "stage"

    result = invoke(source, patch, before, after, output)
    assert result.returncode == 0, result.stderr
    assert source_snapshot(source) == unchanged
    assert {
        path.relative_to(output / "after").as_posix(): path.read_bytes()
        for path in (output / "after").rglob("*")
        if path.is_file()
    } == expected
    assert (output / "before/app/Main.java").read_bytes() == unchanged["app/Main.java"][0]
    assert not (output / "before/new/Added.java").exists()
    manifest = json.loads((output / "stage.json").read_text())
    assert manifest["status"] == "ready"
    assert manifest["affected"] == ["app/Main.java", "new/Added.java"]
    assert manifest["new_files"] == ["new/Added.java"]
    assert (output / "inputs/patch.diff").read_bytes() == patch.read_bytes()


@pytest.mark.parametrize("failure", ["stale", "postimage", "undeclared", "offset"])
def test_failed_staging_retains_diagnostics_and_never_changes_source(
    tmp_path: Path, failure: str
) -> None:
    source, patch, before, after, _expected = fixture(tmp_path)
    if failure == "stale":
        before.write_text(json.dumps({"app/Main.java": "0" * 64}))
    elif failure == "postimage":
        after_values = json.loads(after.read_text())
        after_values["app/Main.java"] = "f" * 64
        after.write_text(json.dumps(after_values))
    elif failure == "undeclared":
        after_values = json.loads(after.read_text())
        del after_values["new/Added.java"]
        after.write_text(json.dumps(after_values))
    else:
        patch.write_text(patch.read_text().replace("@@ -1,3 +1,3 @@", "@@ -4,3 +4,3 @@"))
    unchanged = source_snapshot(source)
    output = tmp_path / "stage"

    result = invoke(source, patch, before, after, output)
    assert result.returncode == 2
    assert source_snapshot(source) == unchanged
    assert json.loads((output / "stage.json").read_text())["status"] == "failed"
    assert (output / "inputs/patch.diff").read_bytes() == patch.read_bytes()


@pytest.mark.parametrize(
    "marker",
    [
        "GIT binary patch\n",
        "rename from app/Main.java\nrename to app/Renamed.java\n",
        "deleted file mode 100644\n",
    ],
)
def test_rejects_non_textual_patch_operations(tmp_path: Path, marker: str) -> None:
    source, patch, before, after, _expected = fixture(tmp_path)
    patch.write_text(patch.read_text().replace("index 1111111", marker + "index 1111111"))
    unchanged = source_snapshot(source)

    result = invoke(source, patch, before, after, tmp_path / "stage")
    assert result.returncode == 2
    assert "binary, rename, delete" in result.stderr
    assert source_snapshot(source) == unchanged


def test_rejects_symlinked_source_path_and_duplicate_manifest_fields(tmp_path: Path) -> None:
    source, patch, before, after, _expected = fixture(tmp_path)
    outside = tmp_path / "outside.java"
    outside.write_bytes((source / "app/Main.java").read_bytes())
    (source / "app/Main.java").unlink()
    (source / "app/Main.java").symlink_to(outside)
    unchanged = outside.read_bytes()

    result = invoke(source, patch, before, after, tmp_path / "symlink-stage")
    assert result.returncode == 2
    assert "contains a symlink" in result.stderr
    assert outside.read_bytes() == unchanged

    (source / "app/Main.java").unlink()
    (source / "app/Main.java").write_bytes(unchanged)
    duplicate = before.read_text().rstrip("}") + ', "app/Main.java": "' + sha(unchanged) + '"}'
    before.write_text(duplicate)
    result = invoke(source, patch, before, after, tmp_path / "duplicate-stage")
    assert result.returncode == 2
    assert "duplicate field" in result.stderr
    assert source_snapshot(source)["app/Main.java"][0] == unchanged


def test_rejects_output_collision_and_traversal_before_source_mutation(tmp_path: Path) -> None:
    source, patch, before, after, _expected = fixture(tmp_path)
    unchanged = source_snapshot(source)
    collision = tmp_path / "stage"
    collision.mkdir()
    (collision / "owned").write_text("keep")
    result = invoke(source, patch, before, after, collision)
    assert result.returncode == 2
    assert "OUTPUT must be fresh" in result.stderr
    assert (collision / "owned").read_text() == "keep"

    values: dict[str, Any] = json.loads(after.read_text())
    values["../escape.java"] = values.pop("new/Added.java")
    after.write_text(json.dumps(values))
    result = invoke(source, patch, before, after, tmp_path / "traversal-stage")
    assert result.returncode == 2
    assert source_snapshot(source) == unchanged
    assert not (tmp_path / "escape.java").exists()


def test_rejects_a_traversing_patch_header_without_changing_source(tmp_path: Path) -> None:
    source, patch, before, after, _expected = fixture(tmp_path)
    patch.write_text(patch.read_text().replace("+++ b/app/Main.java", "+++ b/../outside.java", 1))
    unchanged = source_snapshot(source)

    result = invoke(source, patch, before, after, tmp_path / "stage")
    assert result.returncode == 2
    assert "unsafe new path" in result.stderr
    assert source_snapshot(source) == unchanged
    assert not (tmp_path / "outside.java").exists()


def test_rejects_unframed_create_delete_prefix_before_patch_execution(tmp_path: Path) -> None:
    source, patch, before, after, _expected = fixture(tmp_path)
    prefix = """--- /dev/null
+++ b/undeclared
@@ -0,0 +1 @@
+temporary
--- a/undeclared
+++ /dev/null
@@ -1 +0,0 @@
-temporary
"""
    patch.write_text(prefix + patch.read_text())
    unchanged = source_snapshot(source)
    output = tmp_path / "stage"

    result = invoke(source, patch, before, after, output)
    assert result.returncode == 2
    assert "before its first file diff" in result.stderr
    assert source_snapshot(source) == unchanged
    assert not (output / "after").exists()
    assert not (output / "patch.stdout").exists()
    assert json.loads((output / "stage.json").read_text())["status"] == "failed"


def test_patch_output_is_stopped_and_retained_at_the_runtime_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = load_tool()
    monkeypatch.setattr(helper, "MAX_COMMAND_BYTES", 32)

    _returncode, stdout, stderr, failure = helper.run_patch(
        [sys.executable, "-c", "import sys; sys.stdout.write('x' * 1000000)"], tmp_path
    )
    assert failure == "output"
    assert stdout == b"x" * 32
    assert stderr == b""


def test_all_new_patch_accepts_empty_before_and_keeps_source_empty(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    patch = tmp_path / "new.patch"
    patch.write_text(
        """diff --git a/new/Only.java b/new/Only.java
new file mode 100644
index 0000000..1111111
--- /dev/null
+++ b/new/Only.java
@@ -0,0 +1 @@
+class Only {}
"""
    )
    before = tmp_path / "before.json"
    before.write_text("{}")
    after = tmp_path / "after.json"
    write_manifest(after, {"new/Only.java": b"class Only {}\n"})

    result = invoke(source, patch, before, after, tmp_path / "stage")
    assert result.returncode == 0, result.stderr
    assert list(source.iterdir()) == []
    assert (tmp_path / "stage/after/new/Only.java").read_bytes() == b"class Only {}\n"
    assert json.loads((tmp_path / "stage/stage.json").read_text())["new_files"] == ["new/Only.java"]


def test_descendant_held_output_pipe_is_terminated_within_the_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper = load_tool()
    monkeypatch.setattr(helper, "PATCH_TIMEOUT_SECONDS", 0.2)
    child = "import time; time.sleep(60)"
    parent = (
        f"import subprocess, sys; subprocess.Popen([sys.executable, '-c', {child!r}]); sys.exit(0)"
    )
    started = time.monotonic()
    _returncode, stdout, stderr, failure = helper.run_patch(
        [sys.executable, "-c", parent], tmp_path
    )
    elapsed = time.monotonic() - started
    assert failure == "timeout"
    assert elapsed < 2
    assert stdout == b""
    assert stderr == b""
