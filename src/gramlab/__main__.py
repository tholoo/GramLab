"""Public command entry point; consumer code is only executed inside the runtime."""

import argparse
import os
import sys
from pathlib import Path

from gramlab.runner import run
from gramlab.runtime import RuntimeProfile


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
    args = parser.parse_args()
    if args.profile is None:
        parser.error("Enter the provisioned Nix shell or supply --profile")
    try:
        outcome = run(
            args.manifest,
            args.output,
            profile=RuntimeProfile.load(args.profile),
            android_profile=RuntimeProfile.load(args.android_profile)
            if args.android_profile
            else None,
            android_apk=args.android_apk,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"gramlab: cannot prepare run ({type(error).__name__}): {error}", file=sys.stderr)
        return 2
    print(f"{outcome}: {args.output / 'report.html'}")
    return 0 if outcome == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
