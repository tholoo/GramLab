"""Observe the original rich-link renderer without opening any destination."""

import subprocess
from collections.abc import Callable

from android_guest import main
from android_rich_messages import probe
from rich_links_round_trip import run


def link_probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    return probe(
        guest,
        scene_checks={
            "initial": ["Show linked content", "Linked text", "Guide", "Email team", "Call team"],
            "edited": [
                "Show linked content",
                "Links updated",
                "New guide",
                "New email",
                "New phone",
            ],
        },
        run_scenario=run,
    )


if __name__ == "__main__":
    main(link_probe)
