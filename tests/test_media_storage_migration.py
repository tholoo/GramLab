"""Schema-7 compatibility observations are retained from the unmodified assignment base."""

import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from gramlab.world import World

FIXTURE = Path(__file__).parent / "fixtures" / "media_storage_v7"


def observe(world: World, identities: dict[str, Any]) -> dict[str, Any]:
    """Record complete public results, including denial text and downloaded bytes."""
    result: dict[str, Any] = {
        "snapshot": world.snapshot(),
        "events": world.events(),
        "histories": [world.history(chat) for chat in (1, 2, 3)],
        "updates": [world.poll_updates(bot) for bot in (2, 5)],
        "clients": [world.client_snapshot(user, version=4) for user in (1, 3, 4)],
        "changes": [world.client_changes(user, after=0, version=4) for user in (1, 3, 4)],
        "v3_client": world.client_snapshot(3, version=3),
        "v3_changes": world.client_changes(3, after=0, version=3),
        "emoji": [world.custom_emoji_descriptor(emoji) for emoji in (41, 42)],
        "stickers": world.custom_emoji_stickers(2, ["41", "42"]),
        "authentication": [
            world.authenticate_bot(identities["bot_token"]),
            world.authenticate_client(identities["client_token"]),
        ],
    }
    callbacks = []
    for user, chat, message, request, version in ((1, 1, 1, "photo", 3), (1, 1, 3, "emoji", 4)):
        callback = world.create_callback(
            user_id=user,
            chat_id=chat,
            message_id=message,
            data="tap",
            request_id=request,
            version=version,
        )
        callbacks.append(
            {
                "callback": callback,
                "dependencies": world.callback_dependencies(user, callback, version=version),
                "stored": world.get_callback(user_id=user, callback_id=callback["id"]),
            }
        )
    result["callbacks"] = callbacks
    result["files"] = [
        [info, data.hex()]
        for file_id in identities["file_ids"]
        for info, data in [world.bot_file(2, file_id)]
    ]
    grants: list[Any] = []
    for user in (1, 3, 4):
        for asset in range(1, 5):
            try:
                info, data = world.granted_asset(user, asset)
                grants.append([user, asset, info, data.hex()])
            except ValueError as error:
                grants.append([user, asset, str(error)])
    result["grants"] = grants
    denials = []
    for file_id in [*identities["file_ids"], identities["photo_sha256"]]:
        try:
            world.bot_file(5, file_id)
        except ValueError as error:
            denials.append(str(error))
        else:
            raise AssertionError("Other bot acquired a file without authorization")
    result["other_bot_denials"] = denials
    for user in (1, 3, 4):
        try:
            result[f"emoji_grants_{user}"] = world.granted_custom_emoji(user, ["41", "42"])
        except LookupError as error:
            result[f"emoji_grants_{user}"] = str(error)
    # Convert public tuple returns to the JSON representation retained by the old implementation.
    return dict(json.loads(json.dumps(result)))


def legacy_world(tmp_path: Path) -> Path:
    directory = tmp_path / "world"
    directory.mkdir(mode=0o700)
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection, connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript((FIXTURE / "world.sql").read_text())
        assert connection.execute("PRAGMA user_version").fetchone() == (7,)
    return directory


def assert_legacy_outputs(directory: Path) -> None:
    expected = json.loads((FIXTURE / "expected.json").read_text())
    identities = json.loads((FIXTURE / "identities.json").read_text())
    with World.open(directory) as world:
        assert observe(world, identities) == expected


def test_populated_v7_preserves_public_contract_and_reopen(tmp_path: Path) -> None:
    directory = legacy_world(tmp_path)
    assert_legacy_outputs(directory)
    assert_legacy_outputs(directory)
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection, connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (10,)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert [row[1] for row in connection.execute("PRAGMA table_info(assets)")] == [
            "id",
            "sha256",
            "mime_type",
            "extension",
            "width",
            "height",
        ]
        assert connection.execute("SELECT count(*) FROM media_blobs").fetchone() == (4,)


def database_state(directory: Path) -> tuple[int, list[str]]:
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection, connection:
        return connection.execute("PRAGMA user_version").fetchone()[0], list(connection.iterdump())


def schema(connection: sqlite3.Connection) -> dict[str, Any]:
    tables = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ]
    return {
        table: {
            "columns": connection.execute(f"PRAGMA table_info({table})").fetchall(),
            "foreign_keys": connection.execute(f"PRAGMA foreign_key_list({table})").fetchall(),
            "indexes": connection.execute(f"PRAGMA index_list({table})").fetchall(),
        }
        for table in tables
    }


def test_migration_retains_every_row_byte_and_foreign_key(tmp_path: Path) -> None:
    directory = legacy_world(tmp_path)
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection, connection:
        assets = connection.execute("SELECT * FROM assets ORDER BY id").fetchall()
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name != 'assets' ORDER BY name"
            )
        ]
        retained = {
            table: connection.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608
            for table in tables
        }
    with World.open(directory) as world:
        with closing(sqlite3.connect(directory / "world.sqlite3")) as connection, connection:
            assert connection.execute("SELECT * FROM assets ORDER BY id").fetchall() == [
                row[:-1] for row in assets
            ]
            assert connection.execute(
                "SELECT sha256, body FROM media_blobs ORDER BY sha256"
            ).fetchall() == sorted((row[1], row[-1]) for row in assets)
            for table, rows in retained.items():
                assert connection.execute(f"SELECT * FROM {table}").fetchall() == rows  # noqa: S608
            migrated_schema = schema(connection)
        assert world._connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
        with pytest.raises(sqlite3.IntegrityError):
            with world._connection:
                world._connection.execute(
                    "INSERT INTO assets VALUES (999, 'missing', 'image/png', 'png', 1, 1)"
                )
        with pytest.raises(sqlite3.IntegrityError):
            with world._connection:
                world._connection.execute("DELETE FROM assets WHERE id=1")
    with World.create(tmp_path / "fresh", seed=1, now=1) as fresh:
        assert schema(fresh._connection) == migrated_schema


@pytest.mark.parametrize(
    "statement",
    [
        "CREATE TABLE media_blobs",
        "INSERT INTO media_blobs",
        "DROP TABLE assets",
        "ALTER TABLE",
        "PRAGMA foreign_key_check",
        "PRAGMA user_version=8",
    ],
)
def test_interrupted_migration_rolls_back_everything_and_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, statement: str
) -> None:
    directory = legacy_world(tmp_path)
    before = database_state(directory)
    real_connect = sqlite3.connect

    class Interrupted(BaseException):
        pass

    class InterruptingConnection(sqlite3.Connection):
        def execute(self, sql: str, parameters: Any = ()) -> sqlite3.Cursor:
            result = super().execute(sql, parameters)
            if sql.startswith(statement):
                raise Interrupted(statement)
            return result

    def connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        return real_connect(*args, **kwargs, factory=InterruptingConnection)

    with monkeypatch.context() as patch:
        patch.setattr(sqlite3, "connect", connect)
        with pytest.raises(Interrupted):
            World.open(directory)
    assert database_state(directory) == before
    assert_legacy_outputs(directory)
    assert database_state(directory)[0] == 10


def test_concurrent_openers_recheck_version_after_writer_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = legacy_world(tmp_path)
    ready = threading.Barrier(2)
    real_connect = sqlite3.connect
    began: list[int] = []
    copied: list[int] = []

    class ScheduledConnection(sqlite3.Connection):
        migrating = False

        def execute(self, sql: str, parameters: Any = ()) -> sqlite3.Cursor:
            if sql == "BEGIN IMMEDIATE" and not self.migrating:
                self.migrating = True
                began.append(threading.get_ident())
                ready.wait(timeout=10)
            if sql.startswith("INSERT INTO media_blobs"):
                copied.append(threading.get_ident())
            return super().execute(sql, parameters)

    def connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        return real_connect(*args, **kwargs, factory=ScheduledConnection)

    def opener() -> dict[str, Any]:
        with World.open(directory) as world:
            return world.client_snapshot(1, version=4)

    with monkeypatch.context() as patch:
        patch.setattr(sqlite3, "connect", connect)
        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(opener) for _ in range(2)]
            results = [future.result(timeout=15) for future in futures]
    expected = json.loads((FIXTURE / "expected.json").read_text())["clients"][0]
    assert results == [expected, expected]
    assert len(set(began)) == 2
    assert len(copied) == 1
    assert_legacy_outputs(directory)


def test_future_version_is_rejected_without_changes(tmp_path: Path) -> None:
    directory = legacy_world(tmp_path)
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection, connection:
        connection.execute("PRAGMA user_version=11")
    before = database_state(directory)
    with pytest.raises(ValueError, match="Unsupported world schema"):
        World.open(directory)
    assert database_state(directory) == before


def test_invalid_legacy_foreign_key_aborts_without_partial_migration(tmp_path: Path) -> None:
    directory = legacy_world(tmp_path)
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection, connection:
        connection.execute("INSERT INTO asset_grants VALUES (4, 999)")
    before = database_state(directory)
    with pytest.raises(ValueError, match="foreign keys"):
        World.open(directory)
    assert database_state(directory) == before
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection, connection:
        connection.execute("DELETE FROM asset_grants WHERE asset_id=999")
    assert_legacy_outputs(directory)


def test_existing_bytes_remain_scoped_until_another_bot_publishes(tmp_path: Path) -> None:
    directory = legacy_world(tmp_path)
    identities = json.loads((FIXTURE / "identities.json").read_text())
    with World.open(directory) as world:
        descriptor, data = world.granted_asset(1, 1)
        before = world.snapshot(), world.events()
        with pytest.raises(ValueError, match="unavailable"):
            world.bot_file(2, descriptor["sha256"])
        with pytest.raises(ValueError, match="unavailable"):
            world.granted_asset(4, 1)
        for media in (identities["file_ids"][0], descriptor["sha256"]):
            with pytest.raises(ValueError, match="unavailable"):
                world.send_photo(chat_id=3, sender_id=5, photo={"type": "photo", "media": media})
        assert (world.snapshot(), world.events()) == before
        sent = world.send_photo(
            chat_id=3,
            sender_id=5,
            photo={"type": "photo", "media": "attach://p"},
            uploads={"p": data},
        )
        assert sent["photo"] == {"asset_id": 1}
        assert sent["id"] == 2
        own_id = world.photo_size(5, 1)["file_id"]
        assert own_id != identities["file_ids"][0]
        assert world.bot_file(5, own_id)[1] == data
        assert world.granted_asset(4, 1) == (descriptor, data)
        assert world._connection.execute("SELECT count(*) FROM media_blobs").fetchone() == (4,)
    with World.open(directory) as reopened:
        assert reopened.bot_file(5, own_id)[1] == data
        assert reopened.granted_asset(4, 1) == (descriptor, data)


def test_new_emoji_reuses_immutable_bytes_without_granting_a_persona(tmp_path: Path) -> None:
    directory = legacy_world(tmp_path)
    main = (Path(__file__).parent / "assets" / "custom-emoji" / "emoji-static.webp").read_bytes()
    with World.open(directory) as world:
        descriptor = world.register_custom_emoji(
            request_id="same-main-thumbnail", main=main, thumbnail=main, fallback="🙂"
        )
        assert descriptor["custom_emoji_id"] == "1"
        assert descriptor["main_asset_id"] == descriptor["thumbnail_asset_id"] == 3
        assert world._connection.execute("SELECT count(*) FROM media_blobs").fetchone() == (4,)
        with pytest.raises(LookupError):
            world.granted_custom_emoji(4, ["1"])
        with pytest.raises(ValueError, match="unavailable"):
            world.granted_asset(4, 3)
        world.send_message(
            chat_id=3,
            sender_id=5,
            text="🙂",
            entities=[{"type": "custom_emoji", "offset": 0, "length": 2, "custom_emoji_id": "1"}],
        )
        assert world.granted_custom_emoji(4, ["1"]) == ([descriptor], [world.asset_descriptor(3)])
        assert world.granted_asset(4, 3)[1] == main
