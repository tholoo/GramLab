"""Prepare explicit inputs, invoke trusted containment and retain local run evidence."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import subprocess
import time
import tomllib
from dataclasses import asdict
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

from gramlab._android import IMAGE_PACKAGE
from gramlab.reports import Report, Screenshot, _Redactor, write_report
from gramlab.runtime import RuntimeProfile, Sandbox, _data_directory
from gramlab.world import World

_FILE_LIMIT = 32 * 1024 * 1024
_TOTAL_LIMIT = 128 * 1024 * 1024


def _report_sections(evidence: dict[str, Any]) -> dict[str, Any]:
    sections = {
        "Conversation histories": evidence.get("histories", {}),
        "Process logs": evidence["processes"],
        "Scenario captures": evidence["captures"],
        "Android runtime": evidence["android"],
        "World state": evidence.get("world", {}),
        "Event trace": evidence.get("events", []),
        "Run configuration": evidence["configuration"],
        "Source fingerprints": evidence["sources"],
        "Failure": evidence["failure"],
    }
    for name, value in sections.items():
        serialized = json.dumps(value, ensure_ascii=True, indent=2)
        if len(serialized) > 128 * 1024:
            sections[name] = {
                "truncated": True,
                "full_evidence": "result.json",
                "serialized_bytes": len(serialized),
                "preview": serialized[:16384],
            }
    return sections


def _source(root: Path, relative: str, *, limit: int = _FILE_LIMIT) -> bytes:
    path = PurePosixPath(relative)
    if (
        not relative
        or not path.parts
        or path.is_absolute()
        or str(path) != relative
        or ".." in path.parts
        or "\\" in relative
        or "\x00" in relative
    ):
        raise ValueError("Input paths must be canonical relative paths")
    with _data_directory(root / path.parent) as directory:
        descriptor = os.open(
            path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
        )
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("Inputs must be regular files without symlinks")
            content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError("Input file exceeds its size limit")
    return content


def _inputs(manifest: Path) -> tuple[dict[str, Any], dict[str, dict[str, bytes]]]:
    config = tomllib.loads(_source(manifest.absolute().parent, manifest.name, limit=65536).decode())
    if config.keys() - {"schema", "seed", "now", "timeout", "mode", "scenario", "bots"}:
        raise ValueError("Unknown run manifest field")
    if type(config.get("schema")) is not int or config["schema"] != 1:
        raise ValueError("Unsupported run manifest schema")
    for name in ("seed", "now"):
        if type(config.get(name)) is not int or not 0 <= config[name] < 2**63:
            raise ValueError("Run seed and time must be nonnegative signed 64-bit integers")
    timeout = config.get("timeout", 30)
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 86400:
        raise ValueError("Run timeout must be positive and at most one day")
    config["timeout"] = timeout
    config.setdefault("mode", "simulation-only")
    if config["mode"] not in ("simulation-only", "headless-android"):
        raise ValueError("This runner supports simulation-only and headless-android modes")
    bots = config.get("bots", {})
    if not isinstance(bots, dict) or len(bots) > 64:
        raise ValueError("Bots must be a table with at most 64 entries")
    if any(re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", alias) is None for alias in bots):
        raise ValueError("Bot aliases must use lowercase letters, digits, underscores or hyphens")
    config["bots"] = bots
    programs = {"scenario": config.get("scenario"), **{f"bots/{k}": v for k, v in bots.items()}}
    inputs: dict[str, dict[str, bytes]] = {}
    total = count = 0
    for name, program in programs.items():
        if not isinstance(program, dict) or program.keys() != {"entry", "files"}:
            raise ValueError("Each program requires exactly entry and files")
        files = program["files"]
        if (
            not isinstance(program["entry"], str)
            or not isinstance(files, list)
            or not files
            or any(not isinstance(item, str) for item in files)
            or len(files) != len(set(files))
            or program["entry"] not in files
        ):
            raise ValueError("Program files must be distinct paths including its entry")
        selected: dict[str, bytes] = {}
        for relative in files:
            if name == "scenario" and PurePosixPath(relative).parts[:1] == ("gramlab",):
                raise ValueError("The scenario gramlab package is reserved for the SDK")
            count += 1
            if count > 512:
                raise ValueError("Run inputs exceed 512 files")
            content = _source(manifest.absolute().parent, relative)
            total += len(content)
            if total > _TOTAL_LIMIT:
                raise ValueError("Run inputs exceed 128 MiB")
            selected[relative] = content
        inputs[name] = selected
    config["sources"] = {
        component: {name: hashlib.sha256(value).hexdigest() for name, value in files.items()}
        for component, files in inputs.items()
    }
    # Reject ambiguous evidence labels before creating output or starting consumer code.
    _Redactor(()).clean(config)
    return config, inputs


def run(
    manifest: Path,
    output: Path,
    *,
    profile: RuntimeProfile,
    android_profile: RuntimeProfile | None = None,
    android_apk: Path | None = None,
) -> str:
    """Run a TOML manifest using a trusted, already provisioned runtime profile."""
    config, inputs = _inputs(manifest)
    apk = None
    android_json = None
    selected_profile = profile
    if config["mode"] == "headless-android":
        if android_profile is None or android_apk is None:
            raise ValueError("Headless Android requires a trusted Android profile and approved APK")
        if not {"adb", "emulator", "avdmanager"} <= android_profile.executables.keys():
            raise ValueError("Android profile requires adb, emulator and avdmanager")
        apk = _source(android_apk.absolute().parent, android_apk.name, limit=256 * 1024 * 1024)
        if not apk.startswith(b"PK\x03\x04"):
            raise ValueError("Android APK must be an already built APK archive")
        android_json = json.dumps(asdict(android_profile))
        selected_profile = android_profile
        config["android"] = {
            "apk_sha256": hashlib.sha256(apk).hexdigest(),
            "profile_sha256": hashlib.sha256(android_json.encode()).hexdigest(),
            "image_package": IMAGE_PACKAGE,
        }
    output = output.absolute()
    with _data_directory(output.parent) as parent:
        os.mkdir(output.name, mode=0o700, dir_fd=parent)
    if apk is not None and android_json is not None:
        (output / "client.apk").write_bytes(apk)
        (output / "android-profile.json").write_text(android_json)
        del apk
    for component, selected in inputs.items():
        for relative, content in selected.items():
            destination = output / component / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
    package = Path(__file__).parent
    (output / "gramlab").mkdir()
    for source in (*package.glob("*.py"), package / "py.typed"):
        (output / "gramlab" / source.name).write_bytes(source.read_bytes())
    sdk = output / "scenario" / "gramlab"
    sdk.mkdir()
    for name in ("__init__.py", "scenario.py", "py.typed"):
        (sdk / name).write_bytes((package / name).read_bytes())
    profile_json = json.dumps(asdict(profile))
    (output / "profile.json").write_text(profile_json)
    (output / "run-input.json").write_text(json.dumps(config, indent=2))
    started = time.monotonic()
    observation: dict[str, Any] = {"failure": "supervisor_failed", "processes": {}}
    try:
        result = Sandbox(selected_profile).supervise(
            [profile.python, "-m", "gramlab._run"],
            data=output,
            timeout=config["timeout"] + 15,
            kvm=config["mode"] == "headless-android",
        )
        if result.returncode == 0:
            observation = json.loads((output / "observation.json").read_text())
    except subprocess.TimeoutExpired:
        observation["failure"] = "supervisor_timeout"
    except (OSError, RuntimeError):
        observation["failure"] = "supervisor_startup_failed"
    failure = observation["failure"]
    outcome: Literal["passed", "failed", "incomplete"] = "failed" if failure else "passed"
    evidence: dict[str, Any] = {
        "schema": 1,
        "outcome": outcome,
        "mode": config["mode"],
        "failure": failure,
        "processes": observation["processes"],
        "captures": observation.get("captures", []),
        "android": observation.get("android", {}),
        "sources": config["sources"],
        "configuration": {key: value for key, value in config.items() if key != "sources"},
        "profile_sha256": hashlib.sha256(profile_json.encode()).hexdigest(),
    }
    run_id = "uninitialized"
    if (output / "world" / "world.sqlite3").is_file():
        with World.open(output / "world") as world:
            run_id = world.world_id
            evidence["world"] = world.snapshot()
            evidence["histories"] = {
                str(chat["id"]): world.history(chat["id"]) for chat in evidence["world"]["chats"]
            }
            evidence["events"] = world.events()
    else:
        outcome = "incomplete"
        evidence["outcome"] = outcome
    evidence["run_id"] = run_id
    evidence["elapsed_ms"] = (time.monotonic() - started) * 1000
    evidence = _Redactor(()).clean(evidence)
    (output / "result.json").write_text(json.dumps(evidence, ensure_ascii=True, indent=2))
    write_report(
        output / "report.html",
        Report(
            run_id=run_id,
            title="Consumer scenario run",
            mode=cast(Literal["simulation-only", "headless-android"], config["mode"]),
            outcome=outcome,
            seed=config["seed"],
            profile={
                "Python": profile.python,
                "Runtime profile SHA-256": evidence["profile_sha256"],
                "Manifest schema": "1",
            },
            summary="Scenario completed successfully."
            if not failure
            else f"Run failed: {failure}.",
            evidence=_report_sections(evidence),
            screenshots=[
                Screenshot(
                    caption=f"Chat {capture['chat_id']} · {capture['label']}",
                    png=(output / "captures" / (capture["label"] + ".png")).read_bytes(),
                )
                for capture in evidence["captures"]
                if capture["rendered"]
            ],
            timings={"run": evidence["elapsed_ms"]},
            limitations=(
                "Simulation-only: no Android rendering evidence."
                if config["mode"] == "simulation-only"
                else "Only successful explicit captures provide Android rendering evidence.",
                "Passing reflects the consumer scenario's checks and process outcomes.",
                "Dependencies must already be present in the trusted runtime or selected files.",
                "Large HTML sections show a labeled preview; result.json retains full evidence.",
            ),
        ),
    )
    return outcome
