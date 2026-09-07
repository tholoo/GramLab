"""Observe rich actions through the original-renderer send/edit/restart probe."""

import subprocess
from collections.abc import Callable

from android_guest import main
from android_rich_messages import probe


def action_probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    return probe(
        guest,
        scene_checks={
            "initial": ["Actions / کنش", "Initial anchor / لنگر"],
            "edited": ["ویرایش / Edit", "RTL anchor / لنگر راست"],
        },
    )


if __name__ == "__main__":
    main(action_probe)
