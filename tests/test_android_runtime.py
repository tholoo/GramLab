"""Android toolchain checks through the real containment boundary."""

import json
import os
import shutil
import zipfile
from dataclasses import asdict
from pathlib import Path

import pytest

from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def test_android_builds_can_execute_a_pinned_posix_shell(tmp_path: Path) -> None:
    manifest_path = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    if manifest_path is None:
        pytest.skip("Requires the provisioned Android runtime profile")
    core = RuntimeProfile.load(Path(os.environ["GRAMLAB_RUNTIME_PROFILE"]))
    android = RuntimeProfile.load(Path(manifest_path))
    command = ["/bin/sh", "-c", "printf '%s' gramlab-toolchain"]
    absent = Sandbox(core).run(command, data=tmp_path)
    assert absent.returncode != 0
    assert absent.stdout == ""
    result = Sandbox(android).run(command, data=tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "gramlab-toolchain"
    assert result.stderr == ""


def test_provisioned_emulator_runs_inside_the_private_filesystem(tmp_path: Path) -> None:
    manifest_path = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    if manifest_path is None:
        pytest.skip("Requires the provisioned Android runtime profile from nix develop .#android")
    profile = RuntimeProfile.load(Path(manifest_path))
    result = Sandbox(profile).run([profile.executables["emulator"], "-version"], data=tmp_path)
    assert result.returncode == 0, result.stderr
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    assert f"Android emulator version {toolchain['runtime']['emulator']}" in result.stdout


def test_kvm_access_requires_explicit_opt_in(tmp_path: Path) -> None:
    manifest_path = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    if manifest_path is None:
        pytest.skip("Requires the Android runtime profile")
    if not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires an accessible KVM device; no host policy changes are made")
    profile = RuntimeProfile.load(Path(manifest_path))
    command = [
        profile.python,
        "-c",
        """
import fcntl, json, os
try:
    descriptor = os.open('/dev/kvm', os.O_RDWR)
except FileNotFoundError:
    print(json.dumps({'kvm': 'unavailable'}))
else:
    try:
        print(json.dumps({'kvm': fcntl.ioctl(descriptor, 0xAE00, 0)}))
    finally:
        os.close(descriptor)
""",
    ]
    denied = Sandbox(profile).run(command, data=tmp_path)
    assert denied.returncode == 0, denied.stderr
    assert json.loads(denied.stdout) == {"kvm": "unavailable"}
    allowed = Sandbox(profile).run(command, data=tmp_path, kvm=True)
    assert allowed.returncode == 0, allowed.stderr
    assert json.loads(allowed.stdout) == {"kvm": 12}


def test_dedicated_aosp_guest_boots_with_no_accounts(tmp_path: Path) -> None:
    manifest_path = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    if manifest_path is None:
        pytest.skip("Requires the Android runtime profile")
    if not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires an accessible KVM device")
    profile = RuntimeProfile.load(Path(manifest_path))
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    (tmp_path / "world-secret").write_text("synthetic authoritative world data")
    (tmp_path / "bot-secret").write_text("synthetic private bot state")
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    shutil.copy2("tests/probes/emulator_process.py", tmp_path / "emulator_process.py")
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "-c",
            Path("tests/probes/android_guest.py").read_text(),
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed["emulator_filesystem"] == {
        "world_visible": False,
        "bot_visible": False,
        "private_avd_visible": True,
        "same_pid_namespace": False,
        "same_network": True,
    }
    assert observed["api"] == toolchain["sdk"]["platform"]
    assert observed["abi"] == toolchain["runtime"]["abi"]
    assert "ANGLE" in observed["graphics"] and "SwiftShader" in observed["graphics"]
    assert "Accounts: 0" in observed["accounts"]
    assert observed["network"]["local"] == "gramlab-local-reply\n"
    assert observed["network"]["local_error"] == ""
    for family in ("ipv4", "ipv6"):
        assert observed["network"][family] == {
            "returncode": 1,
            "stdout": "",
            "stderr": "nc: connect: Network is unreachable\n",
        }
    assert observed["host_interfaces"] == [[1, "lo"]]
    assert (tmp_path / "guest.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_native_transport_request_is_rejected_before_network_initialization(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None:
        pytest.skip("Requires the Android profile and the built native probe APK")
    if not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires an accessible KVM device")
    profile = RuntimeProfile.load(Path(manifest))
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    image_package = (
        f"system-images;android-{toolchain['sdk']['platform']};"
        f"{toolchain['runtime']['imageType']};{toolchain['runtime']['abi']}"
    )
    shutil.copy2(apk, tmp_path / "client.apk")
    with zipfile.ZipFile(apk) as archive:
        (tmp_path / "libtmessages.49.so").write_bytes(archive.read("lib/x86_64/libtmessages.49.so"))
    for name in ("android_guest.py", "android_native_guard.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    shutil.copy2("tests/probes/emulator_process.py", tmp_path / "emulator_process.py")
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_native_guard.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            image_package,
        ],
        data=tmp_path,
        kvm=True,
        timeout=240,
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed["extra_probe"]["returncode"] == 0, observed["extra_probe"]
    assert json.loads(observed["extra_probe"]["stdout"]) == {
        "request_blocked": True,
        "initialization_blocked": True,
        "buffer_round_trip": True,
    }


@pytest.mark.parametrize("supervisor_kvm", [False, True])
def test_component_kvm_requires_both_outer_and_component_opt_in(
    tmp_path: Path, supervisor_kvm: bool
) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    if manifest is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the Android profile and accessible KVM")
    profile = RuntimeProfile.load(Path(manifest))
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "profile.json").write_text(json.dumps(asdict(profile)))
    data = tmp_path / "component"
    data.mkdir()
    (data / "probe.py").write_text(
        """
import fcntl, json, os
try:
    descriptor = os.open('/dev/kvm', os.O_RDWR)
except FileNotFoundError:
    print(json.dumps({'kvm': 'unavailable'}))
else:
    try:
        print(json.dumps({'kvm': fcntl.ioctl(descriptor, 0xAE00, 0)}))
    finally:
        os.close(descriptor)
"""
    )
    (tmp_path / "supervisor.py").write_text(
        """
import json, pathlib
from gramlab.runtime import RuntimeProfile, Sandbox
profile = RuntimeProfile(**json.loads(pathlib.Path('profile.json').read_text()))
command = [profile.python, '/work/probe.py']
results = []
with Sandbox(profile).component(command, data=pathlib.Path('component')) as child:
    stdout, stderr = child.communicate(timeout=5)
    results.append({'returncode': child.returncode, 'stdout': stdout, 'stderr': stderr})
with Sandbox(profile).component(command, data=pathlib.Path('component'), kvm=True) as child:
    stdout, stderr = child.communicate(timeout=5)
    results.append({'returncode': child.returncode, 'stdout': stdout, 'stderr': stderr})
print(json.dumps(results))
"""
    )
    result = Sandbox(profile).supervise(
        [profile.python, "/work/supervisor.py"], data=tmp_path, kvm=supervisor_kvm
    )
    assert result.returncode == 0, result.stderr
    denied, requested = json.loads(result.stdout)
    assert denied == {"returncode": 0, "stdout": '{"kvm": "unavailable"}\n', "stderr": ""}
    if supervisor_kvm:
        assert requested == {"returncode": 0, "stdout": '{"kvm": 12}\n', "stderr": ""}
    else:
        assert requested["returncode"] != 0
        assert requested["stdout"] == ""
        assert "/dev/kvm" in requested["stderr"]
