import hashlib
import sqlite3
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from gramlab.world import World

PHOTO = Path(__file__).parent / "assets" / "rich-media" / "photo-square-16x16.png"
FIXTURE = Path(__file__).parent / "fixtures" / "album_storage_v9" / "world.sql"
FIXTURE_SHA256 = "9e97879c99c9d875257f08a4a6adc1acbc3f1b2b428d64d53d10286b87cd1fe9"


def populated_v9(path: Path) -> Path:
    directory = path / "world"
    directory.mkdir(mode=0o700)
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection, connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript(FIXTURE.read_text())
        assert connection.execute("PRAGMA user_version").fetchone() == (9,)
    return directory


def database_state(directory: Path) -> tuple[int, list[str]]:
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection:
        return int(connection.execute("PRAGMA user_version").fetchone()[0]), list(
            connection.iterdump()
        )


def legacy_rows(directory: Path) -> dict[str, list[tuple[Any, ...]]]:
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {table: connection.execute(f"SELECT * FROM {table}").fetchall() for table in tables}  # noqa: S608


def test_populated_v9_fixture_is_pinned_and_contains_no_capabilities() -> None:
    body = FIXTURE.read_bytes()
    assert hashlib.sha256(body).hexdigest() == FIXTURE_SHA256
    assert b'bot_tokens" VALUES' not in body
    assert b'client_tokens" VALUES' not in body


def test_populated_v9_migrates_atomically_under_concurrent_openers_and_reopens(
    tmp_path: Path,
) -> None:
    directory = populated_v9(tmp_path)
    before = legacy_rows(directory)

    def open_world(_index: int) -> int:
        with World.open(directory):
            pass
        with closing(sqlite3.connect(directory / "world.sqlite3")) as connection:
            return int(connection.execute("PRAGMA user_version").fetchone()[0])

    with ThreadPoolExecutor(max_workers=2) as workers:
        assert list(workers.map(open_world, range(2))) == [10, 10]
    assert legacy_rows(directory) | {} == before | {
        "media_group_counter": [(1, 0)],
        "media_group_members": [],
        "media_groups": [],
    }
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA user_version").fetchone() == (10,)
    with World.open(directory) as reopened:
        result = reopened.send_media_group(
            chat_id=1,
            sender_id=2,
            media=[
                {"type": "photo", "media": "attach://same"},
                {"type": "photo", "media": "attach://same"},
            ],
            uploads={"same": PHOTO.read_bytes()},
        )
        assert ([message["id"] for message in result], result[0]["media_group_id"]) == (
            [3, 4],
            "1",
        )


@pytest.mark.parametrize(
    "statement",
    [
        "CREATE TABLE media_group_counter",
        "INSERT INTO media_group_counter",
        "CREATE TABLE media_groups",
        "CREATE TABLE media_group_members",
        "PRAGMA foreign_key_check",
        "PRAGMA user_version=10",
    ],
)
def test_interrupted_v9_migration_rolls_back_and_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, statement: str
) -> None:
    directory = populated_v9(tmp_path)
    before = database_state(directory)
    real_connect: Callable[..., sqlite3.Connection] = sqlite3.connect

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
    with World.open(directory):
        pass
    assert database_state(directory)[0] == 10


def test_fresh_schema_has_exact_album_constraints(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=10, now=10):
        pass
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        assert connection.execute("PRAGMA user_version").fetchone() == (10,)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT * FROM media_group_counter").fetchall() == [(1, 0)]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE media_group_counter SET last_id=-1")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO media_groups VALUES (1, 999, 'photo', 2)")
