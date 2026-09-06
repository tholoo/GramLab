"""Retain verified native composer evidence through the existing report writer."""

import hashlib
import json
from pathlib import Path

from gramlab.reports import Finding, Report, Screenshot, write_report
from gramlab.world import World


def write_live_gap_report(directory: Path, *, destination: Path | None = None) -> Path:
    """Call after the live difference, bot delivery and stored replica assertions pass."""
    guest = json.loads((directory / "guest.json").read_text())
    observed = guest["extra_probe"]
    toolchain = json.loads(Path("clients/android/toolchain.json").read_text())
    with (directory / "client.apk").open("rb") as apk:
        apk_hash = hashlib.file_digest(apk, "sha256").hexdigest()
    with World.open(directory / "world") as world:
        world_id = world.world_id
        state = world.snapshot()
        events = world.events()
    return write_report(
        destination if destination is not None else directory / "report.html",
        Report(
            run_id="live-gap-" + world_id,
            title="Missing messages recovered while Android stays open",
            mode="headless-android",
            outcome="passed",
            seed=state["seed"],
            profile={
                "Renderer": "Telegram Android " + toolchain["client"]["version"],
                "Client revision": toolchain["client"]["revision"],
                "APK SHA-256": apk_hash,
                "Guest": f"AOSP API {guest['api']} / {guest['abi']} / image revision 2",
                "Display": "320 x 640 / 160 dpi / swangle",
                "Fault": "Ordinary polling held until native difference recovery is visible",
                "Clock": f"{observed['clock_step']} seconds between action phases"
                if observed.get("clock_step")
                else "All messages share one world second",
                "Synthetic backlog": str(observed.get("backlog", 0)),
                "World": world_id,
            },
            summary="Incoming delivery is held while a virtual user acts and a real bot replies. "
            "An actual composer send then exposes the missing message positions. The original "
            "client requests a difference and renders the missing messages without restarting. "
            "A further composer send succeeds, and the real bot replies once to each send.",
            screenshots=[
                Screenshot(caption=caption, png=(directory / f"{phase}.png").read_bytes())
                for phase, caption in (
                    ("gap-before", "Before the gap — original Android conversation"),
                    (
                        "gap-withheld",
                        "Delivery held — the virtual message and bot reply are absent",
                    ),
                    (
                        "gap-recovered",
                        "Native difference — missing messages recovered, polling still held",
                    ),
                    ("gap-replied", "Still the same process — another send and real bot replies"),
                )
            ],
            findings=[
                Finding(
                    stage="observed",
                    title="A first gap remained queued indefinitely",
                    detail="The baseline APK completed its send but never requested a difference "
                    "while polling was held. A separate second-send diagnostic recovered from "
                    "the unchanged old cursor, isolating the missing periodic controller callback.",
                ),
                Finding(
                    stage="applied",
                    title="Restore the original periodic callback",
                    detail="The offline adapter now schedules ConnectionsManager.onUpdate on "
                    "the normal stage queue independently of HTTP polling. The native controller "
                    "and renderer are unchanged; the original one-send regression passes.",
                ),
                Finding(
                    stage="verified",
                    title="Recovery precedes release of ordinary polling",
                    detail=f"The {len(observed['differences'])} native difference page(s) start "
                    f"after position 1 and recover through position {observed['position'] - 3}. "
                    "Requests, responses and contiguous positions match. Original UI captures "
                    "show recovery while the polling gate remains closed.",
                ),
                Finding(
                    stage="verified",
                    title="No restart, lost message or duplicate reply",
                    detail="The process identity and single initialization remain unchanged. "
                    f"The final database has exactly {observed['position']} positive message IDs, "
                    "no pending correlation and matching seq/pts cursors. The real bot receives "
                    "each of the three user messages once and acknowledges its update queue.",
                ),
            ],
            evidence={
                "Live recovery observations": observed,
                "Final world state": state,
                "Ordered world events": events,
                "Controlled HTTP exchanges": json.loads((directory / "gap-http.json").read_text()),
            },
            limitations=[
                "Synthetic local evidence with no real account or Telegram DC connection.",
                "The initial polling cursor remains held at 1. Difference pages use the pinned "
                "client's first-sync limit and then advance their cursor. This controlled fixture "
                "does not establish arbitrary fault schedules or concurrent personas.",
                "Controlled polling holds can cause intentional read timeouts. This test does "
                "not measure normal input latency or resolve earlier intermittent failures.",
                "The backlog and virtual user action are explicitly synthetic. Only the two "
                "composer sends are actual Android input; three replies come from the real bot.",
                "World time advances between action phases. Recovered older messages appear "
                "above the newer acknowledged send, matching their dates and IDs. The final "
                "two bot replies share a timestamp and retain their arrival order."
                if observed.get("clock_step")
                else "All messages share one world second. The original ChatActivity inserts "
                "equal-date arrivals after already displayed messages, so the recovered older "
                "messages appear below the acknowledged send. Stored IDs remain correctly ordered.",
                "This focused result does not establish the complete Android regression gate.",
            ],
        ),
    )


def write_composer_report(directory: Path, *, destination: Path | None = None) -> Path:
    """Call after the native composer's semantic and replica assertions pass."""
    guest = json.loads((directory / "guest.json").read_text())
    observed = guest["extra_probe"]
    before_storage = observed["loss"].get("boundary") == "before_storage"
    interruption = (
        "The client is stopped after acknowledgment, with its storage thread suspended before "
        "the original message ID remap."
        if before_storage
        else "The client is stopped while its accepted send response is withheld."
    )
    screenshots = [
        ("before-compose", "Before input — original Android composer"),
        ("after-compose", "Equal Unicode text sent twice — two distinct messages"),
        ("after-composer-restart", "Cold restart — retained messages and replies"),
    ]
    if before_storage:
        screenshots.append(
            ("after-ack-before-storage", "Acknowledged — original storage thread held before remap")
        )
    screenshots.extend(
        [
            ("after-lost-response-restart", "Interrupted send — accepted message recovered"),
            ("after-lost-response-reply", "Recovery completed — real bot reply"),
        ]
    )
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
                "Interruption": "After acknowledgment, before storage"
                if before_storage
                else "Committed response withheld",
            },
            summary="The original Android composer sends Persian, combining characters, emoji "
            "and multiline text to a real local bot. "
            + interruption
            + " Restart recovers the accepted message and receives one bot reply.",
            screenshots=[
                Screenshot(caption=caption, png=(directory / f"{phase}.png").read_bytes())
                for phase, caption in screenshots
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
                    title="The interrupted committed send recovers without duplication",
                    detail=interruption
                    + " Its actual database retains a correlated negative pending ID. Restart "
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
                "Additional interruption points, live gap recovery and broader formatting "
                "input boundaries require further tests. Controlled faults alter execution timing.",
                "Media, replies, alternate senders, scheduling and unsupported request flags "
                "are not modeled by this text-send boundary.",
            ],
        ),
    )
