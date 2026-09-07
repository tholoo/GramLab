"""Public regression coverage for custom-emoji catalog and grant isolation."""

import http.client
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

from gramlab.client_bridge import ClientBridge
from gramlab.world import World

ASSETS = Path(__file__).parent / "assets" / "custom-emoji"
STATIC = (ASSETS / "emoji-static.webp").read_bytes()
ANIMATED = (ASSETS / "emoji-animated.webm").read_bytes()
THUMBNAIL = (ASSETS / "emoji-thumbnail.webp").read_bytes()


def post_documents(base_url: str, capability: str, identifiers: Any) -> tuple[int, dict[str, Any]]:
    raw = json.dumps({"custom_emoji_ids": identifiers}).encode()
    connection = http.client.HTTPConnection("127.0.0.1", urlsplit(base_url).port, timeout=5)
    try:
        connection.request(
            "POST",
            "/v4/custom-emoji-documents",
            raw,
            {
                "Authorization": "Bearer " + capability,
                "Content-Length": str(len(raw)),
                "Content-Type": "application/json",
            },
        )
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def register(
    world: World,
    request_id: str,
    *,
    main: bytes = STATIC,
    fallback: str = "🙂",
    custom_emoji_id: int | str | None = None,
) -> dict[str, Any]:
    return world.register_custom_emoji(
        request_id=request_id,
        main=main,
        thumbnail=THUMBNAIL,
        fallback=fallback,
        custom_emoji_id=custom_emoji_id,
    )


def test_document_http_rejects_non_string_ids_before_grant_lookup(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=11, now=20) as world:
        user = world.create_user(first_name="Ada")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
        capability = world.issue_client_token(user["id"])
        register(world, "seven", custom_emoji_id=7)
        register(world, "eight", custom_emoji_id=8)
        world.send_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            text="🙂",
            entities=[{"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": 7}],
        )
        world_id = world.world_id

    with ClientBridge(directory) as bridge:
        for identifiers, message in (
            ([7], "custom_emoji_ids must contain decimal strings"),
            ([True], "custom_emoji_ids must contain decimal strings"),
            (["7", 8], "custom_emoji_ids must contain decimal strings"),
            (["07"], "Custom emoji ID must be a canonical positive signed 64-bit integer"),
            (["0"], "Custom emoji ID must be a canonical positive signed 64-bit integer"),
            (["-1"], "Custom emoji ID must be a canonical positive signed 64-bit integer"),
            (
                ["9223372036854775808"],
                "Custom emoji ID must be a canonical positive signed 64-bit integer",
            ),
        ):
            assert post_documents(bridge.base_url, capability, identifiers) == (
                400,
                {
                    "schema": 4,
                    "error": {"code": "invalid_request", "message": message},
                },
            )

        unavailable = {
            "schema": 4,
            "error": {
                "code": "document_unavailable",
                "message": "Document is unavailable",
            },
        }
        for identifiers in (["99"], ["8"], ["7", "8"]):
            assert post_documents(bridge.base_url, capability, identifiers) == (404, unavailable)
        status, granted = post_documents(bridge.base_url, capability, ["7"])
        assert status == 200
        assert granted["schema"] == 4
        assert granted["world_id"] == world_id
        assert granted["user_id"] == user["id"]
        assert [row["custom_emoji_id"] for row in granted["custom_emoji"]] == ["7"]
        assert [row["asset_id"] for row in granted["assets"]] == [1, 2]


@pytest.mark.parametrize("conflict", ["request", "identifier"])
def test_registration_conflicts_roll_back_allocators_and_assets(
    tmp_path: Path, conflict: str
) -> None:
    with World.create(tmp_path / conflict, seed=12, now=20) as world:
        if conflict == "request":
            first = register(world, "same")
            assert (
                first["custom_emoji_id"],
                first["main_asset_id"],
                first["thumbnail_asset_id"],
            ) == (
                "1",
                1,
                2,
            )
            with pytest.raises(
                ValueError, match="Request ID already identifies another custom emoji registration"
            ):
                register(world, "same", main=ANIMATED, fallback="🎬")
            expected_id = "2"
        else:
            first = register(world, "first", custom_emoji_id=7)
            assert (
                first["custom_emoji_id"],
                first["main_asset_id"],
                first["thumbnail_asset_id"],
            ) == (
                "7",
                1,
                2,
            )
            with pytest.raises(
                ValueError, match="Custom emoji ID already identifies another registration"
            ):
                register(world, "conflict", main=ANIMATED, fallback="🎬", custom_emoji_id=7)
            expected_id = "1"

        allocated = register(world, "allocated", main=ANIMATED, fallback="🎬")
        assert (
            allocated["custom_emoji_id"],
            allocated["main_asset_id"],
            allocated["thumbnail_asset_id"],
        ) == (expected_id, 3, 2)


def test_chosen_low_id_is_skipped_and_identical_assets_are_reused(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=13, now=20) as world:
        first = register(world, "chosen", custom_emoji_id=1)
        second = register(world, "allocated", fallback="⭐")
        assert (
            first["custom_emoji_id"],
            second["custom_emoji_id"],
            first["main_asset_id"],
            second["main_asset_id"],
            first["thumbnail_asset_id"],
            second["thumbnail_asset_id"],
        ) == ("1", "2", 1, 1, 2, 2)


def test_concurrent_same_and_conflicting_registrations_reopen_and_retry(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=14, now=20):
        pass

    same_barrier = threading.Barrier(2)

    def same_registration(_index: int) -> dict[str, Any]:
        with World.open(directory) as world:
            same_barrier.wait()
            return register(world, "same", custom_emoji_id=5)

    with ThreadPoolExecutor(max_workers=2) as executor:
        same = list(executor.map(same_registration, range(2)))
    expected = {
        "custom_emoji_id": "5",
        "fallback": "🙂",
        "free": True,
        "needs_repainting": False,
        "main_asset_id": 1,
        "thumbnail_asset_id": 2,
        "duration_ms": 0,
    }
    assert same == [expected, expected]

    conflict_barrier = threading.Barrier(2)

    def conflicting_registration(fallback: str) -> tuple[str, str]:
        with World.open(directory) as world:
            conflict_barrier.wait()
            try:
                descriptor = register(
                    world,
                    "conflict",
                    fallback=fallback,
                    custom_emoji_id=6,
                )
            except ValueError as error:
                return "error", str(error)
            return "ok", descriptor["fallback"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(conflicting_registration, ("A", "B")))
    assert sorted(status for status, _ in outcomes) == ["error", "ok"]
    winner = next(value for status, value in outcomes if status == "ok")
    loser = "B" if winner == "A" else "A"
    assert next(value for status, value in outcomes if status == "error") == (
        "Request ID already identifies another custom emoji registration"
    )

    with World.open(directory) as reopened:
        assert register(reopened, "same", custom_emoji_id="5") == same[0]
        assert (
            register(reopened, "conflict", fallback=winner, custom_emoji_id="6")["fallback"]
            == winner
        )
        with pytest.raises(
            ValueError, match="Request ID already identifies another custom emoji registration"
        ):
            register(reopened, "conflict", fallback=loser, custom_emoji_id="6")


def test_edits_retain_old_and_new_grants_without_disclosing_to_another_persona(
    tmp_path: Path,
) -> None:
    with World.create(tmp_path / "world", seed=15, now=20) as world:
        first_user = world.create_user(first_name="Ada")
        second_user = world.create_user(first_name="Bea")
        bot = world.create_user(first_name="Bot", is_bot=True)
        chat = world.open_private_chat(user_id=first_user["id"], bot_id=bot["id"])
        register(world, "first", custom_emoji_id=1)
        register(world, "second", fallback="⭐", custom_emoji_id=2)
        message = world.send_message(
            chat_id=chat["id"],
            sender_id=bot["id"],
            text="🙂",
            entities=[{"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": 1}],
        )
        world.edit_message(
            chat_id=chat["id"],
            message_id=message["id"],
            bot_id=bot["id"],
            text="⭐",
            entities=[{"type": "custom_emoji", "offset": 0, "length": 1, "custom_emoji_id": 2}],
        )
        documents, assets = world.granted_custom_emoji(first_user["id"], ["2", "1"])
        assert [row["custom_emoji_id"] for row in documents] == ["1", "2"]
        assert [row["asset_id"] for row in assets] == [1, 2]
        with pytest.raises(LookupError, match="Document is unavailable"):
            world.granted_custom_emoji(second_user["id"], ["1"])


def test_bot_persona_and_world_file_capabilities_remain_isolated(tmp_path: Path) -> None:
    first_directory = tmp_path / "first"
    second_directory = tmp_path / "second"
    with World.create(first_directory, seed=16, now=20) as first:
        first_user = first.create_user(first_name="Ada")
        second_user = first.create_user(first_name="Bea")
        first_bot = first.create_user(first_name="One", is_bot=True)
        second_bot = first.create_user(first_name="Two", is_bot=True)
        first_chat = first.open_private_chat(user_id=first_user["id"], bot_id=first_bot["id"])
        first.open_private_chat(user_id=second_user["id"], bot_id=second_bot["id"])
        register(first, "seven", custom_emoji_id=7)
        first_sticker = first.custom_emoji_stickers(first_bot["id"], ["7"])[0]
        second_sticker = first.custom_emoji_stickers(second_bot["id"], ["7"])[0]
        assert first_sticker["file_id"] != second_sticker["file_id"]
        assert first_sticker["thumbnail"]["file_id"] != second_sticker["thumbnail"]["file_id"]
        assert first_sticker["file_unique_id"] == second_sticker["file_unique_id"]
        assert first.bot_file(first_bot["id"], first_sticker["file_id"])[1] == STATIC
        assert first.bot_file(second_bot["id"], second_sticker["file_id"])[1] == STATIC
        with pytest.raises(ValueError, match="File is unavailable"):
            first.bot_file(second_bot["id"], first_sticker["file_id"])
        with pytest.raises(ValueError, match="File is unavailable"):
            first.bot_file(first_bot["id"], second_sticker["file_id"])
        first.send_message(
            chat_id=first_chat["id"],
            sender_id=first_bot["id"],
            text="🙂",
            entities=[{"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": 7}],
        )
        assert first.granted_custom_emoji(first_user["id"], ["7"])[0][0]["custom_emoji_id"] == "7"
        with pytest.raises(LookupError, match="Document is unavailable"):
            first.granted_custom_emoji(second_user["id"], ["7"])

        with World.create(second_directory, seed=17, now=20) as second:
            other_user = second.create_user(first_name="Cia")
            other_bot = second.create_user(first_name="Other", is_bot=True)
            second.open_private_chat(user_id=other_user["id"], bot_id=other_bot["id"])
            register(second, "seven", custom_emoji_id=7)
            other_sticker = second.custom_emoji_stickers(other_bot["id"], ["7"])[0]
            with pytest.raises(ValueError, match="File is unavailable"):
                second.bot_file(other_bot["id"], first_sticker["file_id"])
            with pytest.raises(LookupError, match="Document is unavailable"):
                second.granted_custom_emoji(other_user["id"], ["7"])
        with pytest.raises(ValueError, match="File is unavailable"):
            first.bot_file(first_bot["id"], other_sticker["file_id"])
