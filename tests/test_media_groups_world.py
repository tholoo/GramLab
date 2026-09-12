from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from gramlab.documents import DocumentUpload
from gramlab.world import World

PHOTO = Path(__file__).parent / "assets" / "rich-media" / "photo-square-16x16.png"


def setup_world(path: Path) -> tuple[World, dict[str, Any], dict[str, Any], dict[str, Any]]:
    world = World.create(path, seed=112, now=1_700_000_000)
    user = world.create_user(first_name="Ada")
    bot = world.create_user(first_name="Albums", is_bot=True)
    chat = world.open_private_chat(user_id=user["id"], bot_id=bot["id"])
    return world, user, bot, chat


def state(world: World) -> list[str]:
    return list(world._connection.iterdump())


def photos(*names: str) -> list[dict[str, Any]]:
    return [{"type": "photo", "media": f"attach://{name}"} for name in names]


def test_send_media_group_publishes_ordered_atomic_photo_album_and_reopens(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "world"
    world, user, bot, chat = setup_world(directory)
    data = PHOTO.read_bytes()
    messages = world.send_media_group(
        chat_id=chat["id"],
        sender_id=bot["id"],
        media=[
            {
                "type": "photo",
                "media": "attach://same",
                "caption": "A 🙂",
                "caption_entities": [{"type": "bold", "offset": 0, "length": 1}],
                "show_caption_above_media": False,
            },
            {"type": "photo", "media": "attach://same", "caption": "second"},
        ],
        uploads={"same": data},
    )
    expected = [
        {
            "id": 1,
            "chat_id": 1,
            "sender_id": 2,
            "date": 1_700_000_000,
            "text": "",
            "media_group_id": "1",
            "photo": {"asset_id": 1},
            "caption": "A 🙂",
            "caption_entities": [{"type": "bold", "offset": 0, "length": 1}],
        },
        {
            "id": 2,
            "chat_id": 1,
            "sender_id": 2,
            "date": 1_700_000_000,
            "text": "",
            "media_group_id": "1",
            "photo": {"asset_id": 1},
            "caption": "second",
        },
    ]
    assert messages == expected
    assert world.history(chat["id"]) == expected
    assert [
        event["data"] for event in world.events() if event["type"] == "message.created"
    ] == expected
    assert world._connection.execute("SELECT * FROM media_group_counter").fetchall() == [(1, 1)]
    assert world._connection.execute("SELECT * FROM media_groups").fetchall() == [
        (1, 1, "photo", 2)
    ]
    assert world._connection.execute(
        "SELECT * FROM media_group_members ORDER BY ordinal"
    ).fetchall() == [(1, 0, 1, 1), (1, 1, 1, 2)]
    assert world.client_snapshot(user["id"], version=6)["messages"] == expected
    with pytest.raises(ValueError, match="bridge v6"):
        world.client_snapshot(user["id"], version=5)
    world.__exit__(None, None, None)
    with World.open(directory) as reopened:
        assert reopened.history(chat["id"]) == expected
        assert reopened.client_snapshot(user["id"], version=6)["messages"] == expected


def test_document_album_repeats_upload_and_reuse_with_world_wide_group_ids(
    tmp_path: Path,
) -> None:
    world, user, bot, chat = setup_world(tmp_path / "world")
    other = world.create_user(first_name="Lin")
    other_chat = world.open_private_chat(user_id=other["id"], bot_id=bot["id"])
    upload = DocumentUpload(b"GIF89a still an ordinary album document", "animated.gif")
    first = world.send_media_group(
        chat_id=chat["id"],
        sender_id=bot["id"],
        media=[
            {
                "type": "document",
                "media": "attach://same",
                "disable_content_type_detection": False,
            },
            {
                "type": "document",
                "media": "attach://same",
                "disable_content_type_detection": True,
                "caption": "copy",
            },
        ],
        uploads={"same": upload},
    )
    file_id = world.document_file(bot["id"], "1")["file_id"]
    second = world.send_media_group(
        chat_id=other_chat["id"],
        sender_id=bot["id"],
        media=[
            {"type": "document", "media": file_id},
            {"type": "document", "media": file_id},
        ],
    )
    assert [message["document"] for message in first + second] == [{"document_id": "1"}] * 4
    assert [first[0]["media_group_id"], second[0]["media_group_id"]] == ["1", "2"]
    assert world.granted_document(user["id"], "1")[1] == upload.data
    assert world.granted_document(other["id"], "1")[1] == upload.data
    world.__exit__(None, None, None)


@pytest.mark.parametrize(
    "media,uploads,message",
    [
        ([], {}, "2 to 10"),
        (photos("one"), {"one": PHOTO.read_bytes()}, "2 to 10"),
        (
            photos(*[f"p{i}" for i in range(11)]),
            {f"p{i}": PHOTO.read_bytes() for i in range(11)},
            "2 to 10",
        ),
        (
            [
                {"type": "photo", "media": "attach://p"},
                {"type": "document", "media": "attach://d"},
            ],
            {"p": PHOTO.read_bytes(), "d": PHOTO.read_bytes()},
            "mixed",
        ),
        (photos("missing", "missing"), {}, "exactly match"),
        (
            photos("one", "one"),
            {"one": PHOTO.read_bytes(), "unused": PHOTO.read_bytes()},
            "exactly match",
        ),
        (
            [
                {"type": "photo", "media": "attach://p", "show_caption_above_media": True},
                {"type": "photo", "media": "attach://p"},
            ],
            {"p": PHOTO.read_bytes()},
            "captions above",
        ),
        (
            [
                {"type": "photo", "media": "attach://p", "parse_mode": "HTML"},
                {"type": "photo", "media": "attach://p"},
            ],
            {"p": PHOTO.read_bytes()},
            "parameters",
        ),
    ],
)
def test_rejected_group_preserves_complete_state_and_next_ids(
    tmp_path: Path,
    media: list[dict[str, Any]],
    uploads: dict[str, bytes],
    message: str,
) -> None:
    world, _user, bot, chat = setup_world(tmp_path / "world")
    before = state(world)
    with pytest.raises((TypeError, ValueError), match=message):
        world.send_media_group(
            chat_id=chat["id"], sender_id=bot["id"], media=media, uploads=uploads
        )
    assert state(world) == before
    sent = world.send_media_group(
        chat_id=chat["id"],
        sender_id=bot["id"],
        media=photos("ok", "ok"),
        uploads={"ok": PHOTO.read_bytes()},
    )
    assert ([entry["id"] for entry in sent], sent[0]["media_group_id"]) == ([1, 2], "1")
    world.__exit__(None, None, None)


def test_late_member_failure_rolls_back_every_row_and_retry_is_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world, _user, bot, chat = setup_world(tmp_path / "world")
    before = state(world)
    original = world._publish_media_group_member
    calls = 0

    def fail_second(**keywords: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected late publication failure")
        return original(**keywords)

    with monkeypatch.context() as patch:
        patch.setattr(world, "_publish_media_group_member", fail_second)
        with pytest.raises(RuntimeError, match="late publication"):
            world.send_media_group(
                chat_id=chat["id"],
                sender_id=bot["id"],
                media=photos("one", "two"),
                uploads={"one": PHOTO.read_bytes(), "two": PHOTO.read_bytes()},
            )
    assert state(world) == before
    retried = world.send_media_group(
        chat_id=chat["id"],
        sender_id=bot["id"],
        media=photos("same", "same"),
        uploads={"same": PHOTO.read_bytes()},
    )
    assert ([message["id"] for message in retried], retried[0]["media_group_id"]) == (
        [1, 2],
        "1",
    )
    world.__exit__(None, None, None)


def test_album_reuse_rejects_cross_kind_and_foreign_bot_identities_atomically(
    tmp_path: Path,
) -> None:
    world, _user, bot, chat = setup_world(tmp_path / "world")
    other_user = world.create_user(first_name="Lin")
    other_bot = world.create_user(first_name="Other", is_bot=True)
    other_chat = world.open_private_chat(user_id=other_user["id"], bot_id=other_bot["id"])
    photo = world.send_photo(
        chat_id=chat["id"],
        sender_id=bot["id"],
        photo={"type": "photo", "media": "attach://photo"},
        uploads={"photo": PHOTO.read_bytes()},
    )
    document = world.send_document(
        chat_id=chat["id"],
        sender_id=bot["id"],
        document={"media": "attach://document"},
        uploads={"document": DocumentUpload(b"document", "document.bin")},
    )
    foreign = world.send_photo(
        chat_id=other_chat["id"],
        sender_id=other_bot["id"],
        photo={"type": "photo", "media": "attach://foreign"},
        uploads={"foreign": PHOTO.read_bytes()},
    )
    photo_file = world.photo_size(bot["id"], photo["photo"]["asset_id"])["file_id"]
    document_file = world.document_file(bot["id"], document["document"]["document_id"])["file_id"]
    foreign_file = world.photo_size(other_bot["id"], foreign["photo"]["asset_id"])["file_id"]
    for item_kind, file_id, expected in (
        ("photo", document_file, "Photo file identifier"),
        ("document", photo_file, "Document file identifier"),
        ("photo", foreign_file, "Photo file identifier"),
    ):
        before = state(world)
        with pytest.raises(ValueError, match=expected):
            world.send_media_group(
                chat_id=chat["id"],
                sender_id=bot["id"],
                media=[
                    {"type": item_kind, "media": file_id},
                    {"type": item_kind, "media": file_id},
                ],
            )
        assert state(world) == before
    world.__exit__(None, None, None)


def test_group_id_exhaustion_and_grouped_edits_preserve_complete_state(tmp_path: Path) -> None:
    world, _user, bot, chat = setup_world(tmp_path / "world")
    group = world.send_media_group(
        chat_id=chat["id"],
        sender_id=bot["id"],
        media=photos("same", "same"),
        uploads={"same": PHOTO.read_bytes()},
    )
    operations: tuple[Callable[[], dict[str, Any]], ...] = (
        lambda: world.edit_caption(
            chat_id=chat["id"], message_id=group[0]["id"], bot_id=bot["id"], caption="new"
        ),
        lambda: world.edit_media(
            chat_id=chat["id"],
            message_id=group[1]["id"],
            bot_id=bot["id"],
            media={"type": "photo", "media": "attach://new"},
            uploads={"new": PHOTO.read_bytes()},
        ),
    )
    for operation in operations:
        before = state(world)
        with pytest.raises(ValueError, match="editing grouped media"):
            operation()
        assert state(world) == before
    with world._connection:
        world._connection.execute("UPDATE media_group_counter SET last_id=?", (2**63 - 2,))
    maximum = world.send_media_group(
        chat_id=chat["id"],
        sender_id=bot["id"],
        media=photos("maximum", "maximum"),
        uploads={"maximum": PHOTO.read_bytes()},
    )
    assert maximum[0]["media_group_id"] == str(2**63 - 1)
    before = state(world)
    with pytest.raises(ValueError, match="space is exhausted"):
        world.send_media_group(
            chat_id=chat["id"],
            sender_id=bot["id"],
            media=photos("next", "next"),
            uploads={"next": PHOTO.read_bytes()},
        )
    assert state(world) == before
    world.__exit__(None, None, None)


def test_concurrent_album_sends_allocate_distinct_monotonic_groups(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    world, _user, bot, chat = setup_world(directory)
    seeded = world.send_photo(
        chat_id=chat["id"],
        sender_id=bot["id"],
        photo={"type": "photo", "media": "attach://p"},
        uploads={"p": PHOTO.read_bytes()},
    )
    file_id = world.photo_size(bot["id"], seeded["photo"]["asset_id"])["file_id"]
    world.__exit__(None, None, None)

    def publish(_index: int) -> tuple[int, str]:
        with World.open(directory) as opened:
            group = opened.send_media_group(
                chat_id=chat["id"],
                sender_id=bot["id"],
                media=[
                    {"type": "photo", "media": file_id},
                    {"type": "photo", "media": file_id},
                ],
            )
            return group[0]["id"], group[0]["media_group_id"]

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = sorted(workers.map(publish, range(2)))
    assert results == [(2, "1"), (4, "2")]


def test_logical_album_limit_counts_each_repeated_occurrence(tmp_path: Path) -> None:
    world, _user, bot, chat = setup_world(tmp_path / "world")
    maximum = DocumentUpload(b"x" * 50_000_000, "maximum.bin")
    exact = world.send_media_group(
        chat_id=chat["id"],
        sender_id=bot["id"],
        media=[
            {"type": "document", "media": "attach://maximum"},
            {"type": "document", "media": "attach://maximum"},
        ],
        uploads={"maximum": maximum},
    )
    assert len(exact) == 2
    physical_exact = world.send_media_group(
        chat_id=chat["id"],
        sender_id=bot["id"],
        media=[
            {"type": "document", "media": "attach://first"},
            {"type": "document", "media": "attach://second"},
        ],
        uploads={"first": maximum, "second": maximum},
    )
    assert len(physical_exact) == 2
    before_physical_rejection = state(world)
    with pytest.raises(ValueError, match="Uploaded file data"):
        world.send_media_group(
            chat_id=chat["id"],
            sender_id=bot["id"],
            media=[
                {"type": "document", "media": "attach://first"},
                {"type": "document", "media": "attach://second"},
                {"type": "document", "media": "attach://one"},
            ],
            uploads={
                "first": maximum,
                "second": maximum,
                "one": DocumentUpload(b"1", "one.bin"),
            },
        )
    assert state(world) == before_physical_rejection
    file_id = world.document_file(bot["id"], "1")["file_id"]
    before = state(world)
    with pytest.raises(ValueError, match="logical limit"):
        world.send_media_group(
            chat_id=chat["id"],
            sender_id=bot["id"],
            media=[
                {"type": "document", "media": file_id},
                {"type": "document", "media": file_id},
                {"type": "document", "media": "attach://one"},
            ],
            uploads={"one": DocumentUpload(b"1", "one.bin")},
        )
    assert state(world) == before
    world.__exit__(None, None, None)
