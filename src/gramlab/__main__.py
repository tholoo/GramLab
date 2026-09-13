"""Public command entry point; consumer code is only executed inside the runtime."""

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile


def _bot_profiles(bindings: Sequence[str]) -> dict[str, RuntimeProfile]:
    selected: dict[str, Path] = {}
    for binding in bindings:
        if binding.count("=") != 1:
            raise ValueError("Bot profiles must use ALIAS=PROFILE")
        alias, value = binding.split("=", 1)
        if not alias or not value:
            raise ValueError("Bot profiles must use ALIAS=PROFILE")
        if alias in selected:
            raise ValueError(f"Bot runtime profile is repeated for {alias}")
        selected[alias] = Path(value)
    return {alias: RuntimeProfile.load(path) for alias, path in selected.items()}


def main() -> int:
    parser = argparse.ArgumentParser(prog="gramlab")
    commands = parser.add_subparsers(dest="command", required=True)
    execute = commands.add_parser("run", help="Run a declared scenario and bots offline")
    execute.add_argument("manifest", type=Path)
    execute.add_argument("--output", type=Path, required=True, help="Fresh run directory")
    execute.add_argument("--profile", type=Path, default=os.environ.get("GRAMLAB_RUNTIME_PROFILE"))
    execute.add_argument(
        "--android-profile", type=Path, default=os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    )
    execute.add_argument("--android-apk", type=Path, default=os.environ.get("GRAMLAB_ANDROID_APK"))
    execute.add_argument("--android-theme", choices=("light", "dark"), default="light")
    execute.add_argument("--bridge-version", type=int, choices=(3, 4, 5, 6), default=3)
    execute.add_argument(
        "--bot-profile",
        action="append",
        default=[],
        metavar="ALIAS=PROFILE",
        help="Trusted provisioned runtime profile for one declared bot (repeatable)",
    )
    args = parser.parse_args()
    if args.profile is None:
        parser.error("Enter the provisioned Nix shell or supply --profile")
    try:
        profile = RuntimeProfile.load(args.profile)
        android_profile = (
            RuntimeProfile.load(args.android_profile) if args.android_profile else None
        )
        bot_profiles = _bot_profiles(args.bot_profile)
        if bot_profiles:
            outcome = run(
                args.manifest,
                args.output,
                profile=profile,
                android_profile=android_profile,
                android_apk=args.android_apk,
                android_theme=args.android_theme,
                bridge_version=args.bridge_version,
                bot_profiles=bot_profiles,
            )
        else:
            outcome = run(
                args.manifest,
                args.output,
                profile=profile,
                android_profile=android_profile,
                android_apk=args.android_apk,
                android_theme=args.android_theme,
                bridge_version=args.bridge_version,
            )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"gramlab: cannot prepare run ({type(error).__name__}): {error}", file=sys.stderr)
        return 2
    print(f"{outcome}: {args.output / 'report.html'}")
    return 0 if outcome == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
