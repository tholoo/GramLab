"""Manual fixture generation ONLY with the untouched, pinned schema-7 package on PYTHONPATH."""

import argparse
import hashlib
import io
import json
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

from PIL import Image

import gramlab.world
from gramlab.world import World

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))
from test_media_storage_migration import observe  # noqa: E402

BASE = "c901ce2010a1fa79d3fd8b0f9f5ebb68df728a82"
WORLD_SHA256 = "39a1174c612e7fc928e90bb675bc0562ac88ac9732f1c0652c46e79f7325ff38"


def main() -> None:
    source = Path(gramlab.world.__file__)
    if hashlib.sha256(source.read_bytes()).hexdigest() != WORLD_SHA256:
        raise SystemExit("Fixture generation requires the untouched assignment-base World")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new directory for generated fixture files")
    output = parser.parse_args().output
    output.mkdir()
    with tempfile.TemporaryDirectory(prefix="gramlab-media-v7-") as temporary:
        directory = Path(temporary) / "world"
        with World.create(directory, seed=96, now=1700000000) as world:
            world.create_user(first_name="Ada")  # 1
            world.create_user(first_name="Media", is_bot=True)  # 2
            world.create_user(first_name="Photo recipient")  # 3
            world.create_user(first_name="Stranger")  # 4
            world.create_user(first_name="Other bot", is_bot=True)  # 5
            world.open_private_chat(user_id=1, bot_id=2)
            world.open_private_chat(user_id=3, bot_id=2)
            world.open_private_chat(user_id=4, bot_id=5)
            token = world.issue_bot_token(2)
            client_token = world.issue_client_token(1)
            images = []
            for color in ((20, 40, 60), (70, 80, 90)):
                buffer = io.BytesIO()
                Image.new("RGB", (3, 2), color).save(buffer, "PNG")
                images.append(buffer.getvalue())
            photo = world.send_rich_message(
                chat_id=1,
                sender_id=2,
                uploads={"p": images[0]},
                rich_message={
                    "skip_entity_detection": True,
                    "blocks": [
                        {
                            "type": "photo",
                            "photo": {"type": "photo", "media": "attach://p"},
                            "caption": {"text": "A 🖼"},
                        }
                    ],
                },
                reply_markup={"inline_keyboard": [[{"text": "Tap", "callback_data": "tap"}]]},
            )
            file = world.photo_size(2, photo["rich_message"]["blocks"][0]["asset_id"])
            for chat in (1, 2):
                world.send_photo(
                    chat_id=chat, sender_id=2, photo={"type": "photo", "media": file["file_id"]}
                )
            callback = world.create_callback(
                user_id=1, chat_id=1, message_id=1, data="tap", request_id="photo", version=3
            )
            world.answer_callback(bot_id=2, callback_id=callback["id"], text="Recorded")
            world.edit_message(
                chat_id=1,
                message_id=1,
                bot_id=2,
                uploads={"p": images[1]},
                rich_message={
                    "skip_entity_detection": True,
                    "blocks": [
                        {"type": "photo", "photo": {"type": "photo", "media": "attach://p"}}
                    ],
                },
            )
            assets = ROOT / "tests" / "assets" / "custom-emoji"
            main = (assets / "emoji-static.webp").read_bytes()
            thumb = (assets / "emoji-thumbnail.webp").read_bytes()
            for emoji_id in (41, 42):
                world.register_custom_emoji(
                    request_id=f"emoji-{emoji_id}",
                    main=main,
                    thumbnail=thumb,
                    fallback="🙂",
                    custom_emoji_id=emoji_id,
                )
            world.custom_emoji_stickers(2, ["41", "42"])
            world.send_message(
                chat_id=1,
                sender_id=2,
                text="🙂🙂",
                entities=[
                    {"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": "41"},
                    {"type": "custom_emoji", "offset": 2, "length": 2, "custom_emoji_id": "42"},
                ],
            )
            world.create_callback(
                user_id=1, chat_id=1, message_id=3, data="tap", request_id="emoji", version=4
            )
            world.edit_message(chat_id=1, message_id=3, bot_id=2, text="Edited to plain")
            world.send_message(chat_id=1, sender_id=1, text="User reply")
            world.send_message(chat_id=3, sender_id=5, text="Isolated")
            identities = {
                "bot_token": token,
                "client_token": client_token,
                "photo_sha256": file["file_unique_id"],
                "file_ids": [world.photo_size(2, asset)["file_id"] for asset in range(1, 5)],
            }
            expected = observe(world, identities)
        with closing(sqlite3.connect(directory / "world.sqlite3")) as connection, connection:
            if connection.execute("PRAGMA user_version").fetchone() != (7,):
                raise SystemExit("Expected a genuine schema-7 source database")
            sql = "\n".join(connection.iterdump()) + "\nPRAGMA user_version=7;\n"
        (output / "world.sql").write_text(sql)
        for name, value in (("identities", identities), ("expected", expected)):
            (output / f"{name}.json").write_text(
                json.dumps(value, indent=2, ensure_ascii=False) + "\n"
            )


if __name__ == "__main__":
    main()
