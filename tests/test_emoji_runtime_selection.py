"""Trusted launch choices and actual decoder availability across containment."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile, Sandbox


@pytest.mark.parametrize("version", [True, False, 2, 6, "4", 4.0, None])
def test_invalid_bridge_selection_rejects_before_creating_run(
    tmp_path: Path, version: object
) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    output = tmp_path / "run"
    with pytest.raises(ValueError, match="bridge version"):
        run(Path("missing-manifest.toml"), output, profile=profile, bridge_version=version)  # type: ignore[arg-type]
    assert not output.exists()


def test_pinned_decoders_are_available_inside_runtime_without_host_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    monkeypatch.setenv("GRAMLAB_FFMPEG", "/missing-host-decoder")
    monkeypatch.setenv("GRAMLAB_FFPROBE", "/missing-host-probe")
    (tmp_path / "input.webm").write_bytes(
        Path("tests/assets/custom-emoji/emoji-animated.webm").read_bytes()
    )
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "-c",
            """
import json, os, subprocess
probe = subprocess.run([
    os.environ['GRAMLAB_FFPROBE'], '-v', 'error', '-show_entries',
    'stream=codec_name,width,height', '-of', 'json', '/work/input.webm'
], capture_output=True, text=True, check=True)
version = subprocess.run([os.environ['GRAMLAB_FFMPEG'], '-version'],
                         capture_output=True, text=True, check=True).stdout.splitlines()[0]
print(json.dumps({'probe': json.loads(probe.stdout), 'version': version.split()[:3]}))
""",
        ],
        data=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "probe": {"programs": [], "streams": [{"codec_name": "vp9", "width": 100, "height": 100}]},
        "version": ["ffmpeg", "version", "6.1.6"],
    }
    ordinary = Sandbox(profile).run(
        [
            profile.python,
            "-c",
            "import json, os, pathlib, sys; "
            "print(json.dumps({'configured': 'GRAMLAB_FFMPEG' in os.environ, "
            "'readable': pathlib.Path(sys.argv[1]).exists()}))",
            dict(profile.supervisor_environment)["GRAMLAB_FFMPEG"],
        ],
        data=tmp_path,
    )
    assert ordinary.returncode == 0, ordinary.stderr
    assert json.loads(ordinary.stdout) == {"configured": False, "readable": False}


def test_cli_rejects_unsupported_bridge_version(tmp_path: Path) -> None:
    result = subprocess.run(  # noqa: S603 — real CLI with fixed arguments
        [
            sys.executable,
            "-m",
            "gramlab",
            "run",
            "missing.toml",
            "--output",
            str(tmp_path / "run"),
            "--bridge-version",
            "6",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
    assert not (tmp_path / "run").exists()
