"""Quoted code uses original Android rendering and the existing lifecycle observer."""

import subprocess
from collections.abc import Callable

from android_guest import main
from android_rich_messages import probe
from quoted_code_round_trip import run


def quoted_probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    return probe(
        guest,
        scene_checks={
            "initial": ["Show quoted code", "Code", "alpha()", "Pre", "print(1)"],
            "edited": ["Show quoted code", "کد", "beta()", "Pre edited", "print(2)"],
        },
        run_scenario=run,
    )


if __name__ == "__main__":
    main(quoted_probe)
