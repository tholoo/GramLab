"""Native lifetime-scoped rich-button disarm regression and probe packaging."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from test_android_quoted_code import assert_isolation

from gramlab.runtime import RuntimeProfile, Sandbox

sys.path.insert(0, str(Path("tests/probes").resolve()))
from android_button_disarm import probe


def test_patch_and_fixture_are_bounded_to_the_actual_reload_seam() -> None:
    patch = Path("clients/android/patches/0028-rich-button-disarm-lifetime.patch").read_text()
    source = Path("tests/fixtures/android_button_disarm/ButtonDisarmProbe.java").read_text()
    assert patch.count("diff --git ") == 1
    assert patch.count("GramLabButtonObserver.java") == 4
    assert all(term not in patch for term in ("postDelayed", "input", "drawn(", "deadline"))
    series = Path("clients/android/patches/series").read_text().splitlines()
    assert series[27] == "0028-rich-button-disarm-lifetime.patch"
    assert series.count("0028-rich-button-disarm-lifetime.patch") == 1
    assert source.startswith("// SPDX-License-Identifier: GPL-2.0-or-later\n")
    assert 'getDeclaredMethod("reload")' in source
    assert 'field(observer, "invalidatedOperations")' in source
    assert "reload.invoke(null)" in source
    assert "invalidated_operation_rearmed" in source


def test_probe_collects_the_actual_app_process_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    calls: list[tuple[str, ...]] = []
    expected = {
        "schema": 1,
        "passed": 1,
        "failed": 0,
        "total": 1,
        "cases": [{"name": "stale_activation", "passed": True}],
    }

    def guest(*arguments: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        if "/system/bin/app_process" in arguments:
            return subprocess.CompletedProcess(arguments, 0, json.dumps(expected), "")
        return subprocess.CompletedProcess(arguments, 0, "", "")

    observed = probe(guest)
    assert observed == {"returncode": 0, "result": expected}
    assert any("/system/bin/app_process" in call for call in calls)
    retained = json.loads(Path("button-disarm-process.json").read_text())
    assert retained == {"returncode": 0, "stdout": json.dumps(expected), "stderr": ""}


@pytest.mark.android
def test_actual_reload_scopes_valid_disarm_to_its_client_lifetime(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    client_apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    probe_apk = os.environ.get("GRAMLAB_ANDROID_BUTTON_DISARM_PROBE_APK")
    if (
        manifest is None
        or client_apk is None
        or probe_apk is None
        or not os.access("/dev/kvm", os.R_OK | os.W_OK)
    ):
        pytest.skip("Requires the Android profile, reviewed client/probe APKs and accessible KVM")
    profile = RuntimeProfile.load(Path(manifest))
    shutil.copy2(client_apk, tmp_path / "client.apk")
    shutil.copy2(probe_apk, tmp_path / "button-disarm-probe.apk")
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("emulator_process.py", "android_guest.py", "android_button_disarm.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_button_disarm.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image,
        ],
        data=tmp_path,
        kvm=True,
        timeout=420,
    )
    (tmp_path / "button-disarm-result.json").write_text(result.stdout)
    assert result.returncode == 0, result.stderr
    full = json.loads(result.stdout)
    assert_isolation(full)
    observed = full["extra_probe"]
    assert observed["returncode"] == 0, observed
    native = observed["result"]
    assert native == {
        "schema": 1,
        "passed": 10,
        "failed": 0,
        "total": 10,
        "cases": [
            {"name": name, "passed": True}
            for name in (
                "stale_activation",
                "stale_client",
                "matching_current_operation",
                "different_current_operation",
                "malformed_json",
                "extra_field",
                "invalid_schema",
                "invalid_activation_token",
                "invalid_client_token",
                "invalid_operation_token",
            )
        ],
    }
