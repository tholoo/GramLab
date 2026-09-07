"""Reuse the real-bot lifecycle and retain complete rich-link World evidence."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rich_round_trip import run as run_message

from gramlab.world import World


def run(
    show: Callable[[dict[str, Any]], str] | None = None,
    observe: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result = run_message(show, observe, request_text="Show linked content")
    with World.open(Path("world")) as world:
        result["events"] = world.events()
        result["snapshot"] = world.client_snapshot(1, version=2)
    return result


if __name__ == "__main__":
    print(json.dumps(run()))
