"""Retain verified native composer evidence through the existing report writer."""

import hashlib
import json
from pathlib import Path

from gramlab.reports import Finding, Report, Screenshot, write_report
from gramlab.world import World


def write_composer_report(directory: Path, *, destination: Path | None = None) -> Path:
    """Call after the native composer's semantic and replica assertions pass."""
    guest = json.loads((directory / "guest.json").read_text())
    observed = guest["extra_probe"]
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    with World.open(directory / "world") as world:
        state = world.snapshot()
        events = world.events()
        world_id = world.world_id
    with (directory / "client.apk").open("rb") as apk:
        apk_hash = hashlib.file_digest(apk, "sha256").hexdigest()
    return write_report(
        destination if destination is not None else directory / "report.html",
        Report(
            run_id="composer-" + world_id,
            title="Native composer and interrupted send recovery",
            mode="headless-android",
            outcome="passed",
            seed=state["seed"],
            profile={
                "Renderer": "Telegram Android " + toolchain["client"]["version"],
                "Client revision": toolchain["client"]["revision"],
                "APK SHA-256": apk_hash,
                "Guest": f"AOSP API {guest['api']} / {guest['abi']} / image revision 2",
                "Display": "320 x 640 / 160 dpi / swangle",
                "World": world_id,
            },
            summary="The original Android composer sends Persian, combining characters, emoji "
            "and multiline text to a real local bot. A committed send whose response is withheld "
            "survives a client restart and receives one bot reply.",
            screenshots=[
                Screenshot(caption=caption, png=(directory / f"{phase}.png").read_bytes())
                for phase, caption in (
                    ("before-compose", "Before input — original Android composer"),
                    ("after-compose", "Equal Unicode text sent twice — two distinct messages"),
                    ("after-composer-restart", "Cold restart — retained messages and replies"),
                    ("after-lost-response-restart", "Lost response — accepted message recovered"),
                    ("after-lost-response-reply", "Recovery completed — real bot reply"),
                )
            ],
            findings=[
                Finding(
                    stage="observed",
                    title="The baseline Send request was unsupported",
                    detail="Actual native Send reached the old adapter and failed with 501.",
                ),
                Finding(
                    stage="applied",
                    title="Durable correlation and original client completion",
                    detail="The world commits a scoped receipt and message position. The GPL "
                    "adapter returns native acknowledgments and reconciles retained pending "
                    "messages through the original client storage and completion paths.",
                ),
                Finding(
                    stage="verified",
                    title="A response lost after commit does not duplicate the send",
                    detail="The client is stopped while the accepted response is withheld. "
                    "Its actual database retains a correlated negative pending ID. Restart "
                    "recovers one positive message, no pending duplicate and matching cursors. "
                    "The bot sees one pending update and produces one reply.",
                ),
            ],
            evidence={
                "Composer and recovery observations": observed,
                "Final world state": state,
                "Ordered world events": events,
                "Guest isolation observations": {
                    name: guest[name]
                    for name in (
                        "api",
                        "abi",
                        "accounts",
                        "network",
                        "host_interfaces",
                        "emulator_filesystem",
                    )
                },
            },
            limitations=[
                "Synthetic local evidence; no real account or Telegram DC connection.",
                "This focused case does not establish the full Android regression gate.",
                "The original client marks loaded outgoing bot messages as Seen in memory. "
                "The extra checkmark after restart is not a simulated peer read receipt.",
                "Broader composer transformations and interactive input remain unfinished; "
                "the separate scenario example covers bounded Start Bot and typed input.",
                "Ack-before-storage interruption, live gap recovery and broader formatting "
                "input boundaries require further tests.",
                "Media, replies, alternate senders, scheduling and unsupported request flags "
                "are not modeled by this text-send boundary.",
            ],
        ),
    )
