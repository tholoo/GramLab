"""Upstream effect controls, persistent flags and actual shader execution in one guest."""

import json
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

import pytest

from gramlab.reports import Finding, Report, Screenshot, write_report
from gramlab.runtime import RuntimeProfile, Sandbox

pytestmark = pytest.mark.android


def test_original_blur_and_glass_controls_preserve_chat_and_execute_shader(tmp_path: Path) -> None:
    manifest = os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    apk = os.environ.get("GRAMLAB_ANDROID_PROBE_APK")
    if manifest is None or apk is None or not os.access("/dev/kvm", os.R_OK | os.W_OK):
        pytest.skip("Requires the dedicated Android profile, debug APK and KVM")
    profile = RuntimeProfile.load(Path(manifest))
    shutil.copy2(apk, tmp_path / "client.apk")
    shutil.copytree(
        "src/gramlab", tmp_path / "gramlab", ignore=shutil.ignore_patterns("__pycache__")
    )
    (tmp_path / "emulator-profile.json").write_text(json.dumps(asdict(profile)))
    for name in ("android_guest.py", "emulator_process.py", "android_effects.py", "jdwp.py"):
        shutil.copy2(Path("tests/probes") / name, tmp_path / name)
    result = Sandbox(profile).supervise(
        [
            profile.python,
            "/work/android_effects.py",
            profile.executables["emulator"],
            profile.executables["adb"],
            profile.executables["avdmanager"],
            "system-images;android-36;default;x86_64",
        ],
        data=tmp_path,
        kvm=True,
        timeout=600,
    )
    (tmp_path / "effects-result.json").write_text(result.stdout)
    (tmp_path / "effects-stderr.txt").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    runtime = json.loads(result.stdout)
    observed = runtime["extra_probe"]
    assert runtime["network"]["ipv4"]["returncode"] != 0
    assert runtime["network"]["ipv6"]["returncode"] != 0
    assert runtime["api"] == "36"
    expected = [
        {
            "id": 1,
            "chat_id": 1,
            "sender_id": 1,
            "date": 1700000000,
            "text": "Observe original effects",
        },
        {
            "id": 2,
            "chat_id": 1,
            "sender_id": 2,
            "date": 1700000000,
            "text": "",
            "rich_message": {
                "blocks": [
                    {"type": "heading", "size": 2, "text": "Native effects"},
                    {
                        "type": "paragraph",
                        "text": ["سلام دنیا — ", {"type": "bold", "text": "GramLab"}],
                    },
                    {
                        "type": "blockquote",
                        "blocks": [
                            {"type": "paragraph", "text": "Same world and original renderer"}
                        ],
                    },
                ]
            },
        },
    ]
    phases = observed["phases"]
    assert set(phases) == {"baseline", "blur", "glass", "restored"}
    assert phases["baseline"]["preferences"] == {}
    for name, mask in (
        ("baseline", None),
        ("blur", 198940),
        ("glass", 461084),
        ("restored", 198684),
    ):
        phase = phases[name]
        assert phase["history"] == expected
        assert "Accounts: 0" in phase["accounts"]
        assert "level: 100" in phase["battery"]
        assert "Status: ok" in phase["launch"] and "LaunchState: COLD" in phase["launch"]
        assert "Native effects" in phase["ui"] and "GramLab" in phase["ui"]
        assert (tmp_path / f"{name}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        if mask is not None:
            assert phase["preferences"] == {
                "lite_mode6": {"type": "int", "value": str(mask)},
                "lite_mode_battery_level": {"type": "int", "value": "10"},
            }
    for name, blur, glass in (
        ("blur", "true", "false"),
        ("glass", "true", "true"),
        ("restored", "false", "false"),
    ):
        assert observed["selected"][name]["blur"]["checked"] == blur
        assert observed["selected"][name]["glass"]["checked"] == glass
    shader = observed["shader"]
    assert shader["class"] == "Lorg/telegram/ui/Components/blur3/LiquidGlassEffect;"
    assert shader["method"] == "update" and shader["descriptor"] == "(FFFFFFFFFFFI)V"
    assert shader["thread_name"] == "main" and shader["suspend_policy"] == "event_thread"
    assert set(shader["arguments"]) == {"foregroundColor"}
    assert type(shader["arguments"]["foregroundColor"]) is int
    assert shader["history_after_trigger"] == expected
    assert "Original glass observation with a wrapping unsent draft" in shader["trigger_ui"]
    composer_bounds = []
    for ui in (phases["glass"]["ui"], shader["trigger_ui"]):
        tree = ET.fromstring(ui)  # noqa: S314 — dedicated guest XML
        fields = [n for n in tree.iter("node") if n.get("class") == "android.widget.EditText"]
        assert len(fields) == 1
        composer_bounds.append(fields[0].get("bounds"))
    assert composer_bounds[0] != composer_bounds[1]
    write_report(
        tmp_path / "report.html",
        Report(
            run_id="native-effects-comparison",
            title="Original Android blur and liquid glass",
            mode="headless-android",
            outcome="passed",
            seed=7,
            profile={
                "Android": "Pinned debug client; AOSP API 36",
                "Graphics": runtime["graphics"],
                "Display": "320 x 640, 160 dpi; same guest, world and default theme",
                "Controls": "Original Power Usage checkboxes; no performance override",
            },
            evidence={
                "Phases": phases,
                "Native controls": observed["selected"],
                "Original shader method observation": shader,
            },
            timings=observed["timings"],
            screenshots=[
                Screenshot(caption=name, png=(tmp_path / f"{name}.png").read_bytes())
                for name in ("baseline", "blur", "glass", "restored")
            ],
            findings=[
                Finding(
                    stage="verified",
                    title="Native shader path reached",
                    detail="An external one-shot breakpoint observes the original "
                    "LiquidGlassEffect.update on the main thread after the glass capture.",
                )
            ],
            limitations=[
                "Settings change only this disposable guest; defaults remain unchanged.",
                "Screenshots need visual review; this is not pixel-perfect conformance.",
                "The measured performance class is not directly observed.",
                "Launch/capture timings exclude guest boot and the debugger observation.",
            ],
        ),
    )
