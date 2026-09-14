"""Public command entry point; consumer code is only executed inside the runtime."""

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from gramlab.playground import request as playground_request
from gramlab.playground_web import BrowserPlayground
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
    playground = commands.add_parser(
        "playground", help="Keep a seeded scenario and its bots available for interaction"
    )
    playground_commands = playground.add_subparsers(dest="playground_command", required=True)
    start = playground_commands.add_parser("start", help="Start one foreground playground owner")
    start.add_argument("manifest", type=Path)
    start.add_argument("--output", type=Path, required=True, help="Fresh playground directory")
    start.add_argument("--profile", type=Path, default=os.environ.get("GRAMLAB_RUNTIME_PROFILE"))
    start.add_argument(
        "--android-profile", type=Path, default=os.environ.get("GRAMLAB_ANDROID_RUNTIME_PROFILE")
    )
    start.add_argument("--android-apk", type=Path, default=os.environ.get("GRAMLAB_ANDROID_APK"))
    start.add_argument("--android-theme", choices=("light", "dark"), default="light")
    start.add_argument("--bridge-version", type=int, choices=(3, 4, 5, 6), default=3)
    start.add_argument("--bot-profile", action="append", default=[], metavar="ALIAS=PROFILE")
    start.add_argument("--web", action="store_true", help="Open a clickable loopback chat client")
    start.add_argument(
        "--no-open", action="store_true", help="Print the web client URL without opening a browser"
    )
    for operation in ("status", "reset", "stop"):
        command = playground_commands.add_parser(operation)
        command.add_argument("--output", type=Path, required=True)
    add_bot = playground_commands.add_parser(
        "add-bot", help="Simulate a group creator adding one configured bot"
    )
    add_bot.add_argument("--output", type=Path, required=True)
    add_bot.add_argument("--group", required=True)
    add_bot.add_argument("--bot", required=True)
    add_bot.add_argument("--actor", required=True)
    send = playground_commands.add_parser("send", help="Send text as one synthetic participant")
    send.add_argument("--output", type=Path, required=True)
    send.add_argument("--chat-id", type=int, required=True)
    send.add_argument("--actor-id", type=int, required=True)
    send.add_argument("--text", required=True)
    tap = playground_commands.add_parser("tap", help="Press a visible rich button by label")
    tap.add_argument("--output", type=Path, required=True)
    tap.add_argument("--chat-id", type=int, required=True)
    tap.add_argument("--actor-id", type=int, required=True)
    tap.add_argument("--label", required=True)
    capture = playground_commands.add_parser(
        "capture", help="Retain semantic and optional Android evidence for one chat"
    )
    capture.add_argument("--output", type=Path, required=True)
    capture.add_argument("--chat-id", type=int, required=True)
    capture.add_argument("--actor-id", type=int, required=True)
    capture.add_argument("--label", required=True)
    capture.add_argument("--contains", action="append", default=[])
    args = parser.parse_args()
    if (
        args.command == "playground"
        and args.playground_command == "start"
        and args.no_open
        and not args.web
    ):
        parser.error("--no-open requires --web")
    if args.command == "playground" and args.playground_command != "start":
        if args.playground_command == "add-bot":
            operation = "add_bot"
            parameters = {"group": args.group, "bot": args.bot, "actor": args.actor}
        elif args.playground_command == "send":
            operation = "send"
            parameters = {
                "chat_id": args.chat_id,
                "actor_id": args.actor_id,
                "text": args.text,
            }
        elif args.playground_command == "tap":
            operation = "tap"
            parameters = {
                "chat_id": args.chat_id,
                "actor_id": args.actor_id,
                "label": args.label,
            }
        elif args.playground_command == "capture":
            operation = "capture"
            parameters = {
                "chat_id": args.chat_id,
                "actor_id": args.actor_id,
                "label": args.label,
                "contains": args.contains,
            }
        else:
            operation = args.playground_command
            parameters = {}
        try:
            result = playground_request(args.output, operation, parameters)
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
            print(
                f"gramlab: cannot control playground ({type(error).__name__}): {error}",
                file=sys.stderr,
            )
            return 2
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0
    if args.profile is None:
        parser.error("Enter the provisioned Nix shell or supply --profile")
    try:
        profile = RuntimeProfile.load(args.profile)
        android_profile = (
            RuntimeProfile.load(args.android_profile) if args.android_profile else None
        )
        bot_profiles = _bot_profiles(args.bot_profile)
        if args.command == "playground":
            browser = (
                BrowserPlayground(args.output, opener=(lambda _url: True))
                if args.web and args.no_open
                else BrowserPlayground(args.output)
                if args.web
                else None
            )
            try:
                if browser is not None:
                    print(f"Playground UI: {browser.start()}", flush=True)
                outcome = run(
                    args.manifest,
                    args.output,
                    profile=profile,
                    android_profile=android_profile,
                    android_apk=args.android_apk,
                    android_theme=args.android_theme,
                    bridge_version=args.bridge_version,
                    bot_profiles=bot_profiles,
                    playground=True,
                )
            finally:
                if browser is not None:
                    browser.close()
        elif bot_profiles:
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
