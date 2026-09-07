"""Observe cleaned strings through the existing original-renderer send/edit/restart probe."""

import subprocess
from collections.abc import Callable

from android_guest import main
from android_rich_messages import probe


def cleaning_probe(guest: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    return probe(
        guest,
        scene_checks={
            "initial": ["Clean start", "Amber 42", "ABCD", "فارسی", "print 1", "Value 7"],
            "edited": ["متن پاک", "فارسی", "EFGH", "note 2", "جدول پاک", "عدد ۸"],
        },
    )


if __name__ == "__main__":
    main(cleaning_probe)
