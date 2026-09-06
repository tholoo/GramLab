"""Attach actual recovery evidence to the original HTML report boundary."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from gramlab.reports import Finding, Report, Screenshot, write_report
from gramlab.world import World


def write_recovery_report(
    directory: Path,
    observed: dict[str, Any],
    *,
    mode: Literal["simulation-only", "headless-android"],
    destination: Path | None = None,
) -> Path:
    with World.open(directory / "world") as world:
        state = world.snapshot()
        journal = world.events()
        world_id = world.world_id
    screenshots = []
    timings = {}
    digest = hashlib.sha256()
    for source in sorted((directory / "gramlab").rglob("*.py")):
        digest.update(str(source.relative_to(directory / "gramlab")).encode() + b"\x00")
        digest.update(source.read_bytes())
    profile = {"World": world_id, "Core source SHA-256": digest.hexdigest(), "Renderer": "not run"}
    guest_evidence = {}
    if mode == "headless-android":
        toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
        guest = json.loads((directory / "guest.json").read_text())
        guest_evidence = {
            name: guest[name]
            for name in ("api", "abi", "network", "host_interfaces", "emulator_filesystem")
        }
        guest_evidence["accounts"] = observed["client"]["accounts"]
        with (directory / "client.apk").open("rb") as apk:
            apk_hash = hashlib.file_digest(apk, "sha256").hexdigest()
        profile.update(
            {
                "Renderer": "Telegram Android " + toolchain["client"]["version"],
                "Client revision": toolchain["client"]["revision"],
                "APK SHA-256": apk_hash,
                "Guest": f"AOSP API {guest['api']} / {guest['abi']} / image revision 2",
                "Display": "320 x 640 / 160 dpi / swangle",
            }
        )
        for phase, caption in [
            ("before", "Before shutdown — original reply and inline button"),
            ("recovered", "After downtime — corrected reply and removed button"),
            ("repeated", "Second cold restart — no duplicate messages"),
        ]:
            screenshots.append(
                Screenshot(caption=caption, png=(directory / f"{phase}.png").read_bytes())
            )
            launch = observed["client"]["launches"][phase]
            match = re.search(r"^TotalTime: ([0-9]+)$", launch, re.MULTILINE)
            if match is not None:
                timings[f"{phase}: ActivityManager cold launch"] = float(match[1])
    return write_report(
        destination if destination is not None else directory / "report.html",
        Report(
            run_id="recovery-" + world_id,
            title="Older reply recovery",
            mode=mode,
            outcome="passed",
            seed=state["seed"],
            profile=profile,
            summary="A real bot edits an older reply and sends a newer one. "
            "This report retains the verified semantic result and any captured Android evidence.",
            screenshots=screenshots,
            timings=timings,
            findings=[
                Finding(
                    stage="observed",
                    title="The baseline retained stale text and a button",
                    detail="The six-patch client refreshed only the newest cached reply. "
                    "The baseline failure is documented in android-history-recovery.md.",
                ),
                Finding(
                    stage="applied",
                    title="Reconcile the complete startup history",
                    detail="Patch seven uses upstream history storage before opening the chat, "
                    "while retaining the application database and renderer.",
                ),
                Finding(
                    stage="verified",
                    title="The scenario's exact semantic checks passed",
                    detail="The real bot responses, four-message final history and empty pending "
                    "queue match the expected result. Android runs also check two cold restarts.",
                ),
            ],
            evidence={
                "Bot responses before downtime": observed["before"],
                "Bot edit and new reply during downtime": observed["after"],
                "Final message history": observed["history"],
                "Pending bot updates": observed["pending"],
                "World state": state,
                "Ordered world events": journal,
                **({"Guest isolation observations": guest_evidence} if guest_evidence else {}),
            },
            limitations=[
                "Local synthetic evidence; no real accounts or Telegram DCs.",
                "Simulation-only execution supplies no Android rendering evidence.",
                "ActivityManager timings cover app launch; guest boot, bot latency and "
                "renderer throughput are not measured here.",
                "Deletion, multi-dialog and interrupted replica-write recovery remain unverified.",
                "Per-component port restrictions, resource quotas, media and Mini App isolation "
                "remain unfinished.",
            ],
        ),
    )
