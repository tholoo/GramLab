"""Schema-8 compatibility evidence retained from the untouched assignment base."""

import hashlib
import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from test_media_storage_migration import observe, schema

from gramlab.world import World

FIXTURE = Path(__file__).parent / "fixtures" / "document_storage_v8"
HASHES = {
    "world.sql": "24a0490e97edd8c3ed5105fc6572861d5bad0560e7741a742bdcf9524f9e10e4",
    "expected.json": "f6495167c6ea8dc75fb6335cf35cc8ddf2642b94361b64e6dfc2f6265bc87f48",
    "identities.json": "4864f4c0551a34a43dd4cd1dfdde28b8ec62b11faf8d0c8cd3f10a4b3d69de1e",
}


def legacy_world(tmp_path: Path) -> Path:
    directory = tmp_path / "world"
    directory.mkdir(mode=0o700)
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection, connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript((FIXTURE / "world.sql").read_text())
        assert connection.execute("PRAGMA user_version").fetchone() == (8,)
    return directory


def database_state(directory: Path) -> tuple[int, list[str]]:
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection, connection:
        return connection.execute("PRAGMA user_version").fetchone()[0], list(connection.iterdump())


def assert_legacy_outputs(directory: Path) -> None:
    expected = json.loads((FIXTURE / "expected.json").read_text())
    identities = json.loads((FIXTURE / "identities.json").read_text())
    with World.open(directory) as world:
        assert observe(world, identities) == expected


def test_fixture_hashes_and_base_provenance_are_immutable() -> None:
    for name, digest in HASHES.items():
        assert hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest() == digest
    generator = (FIXTURE / "generate.py").read_text()
    assert 'BASE = "df1e67e6c61ba2b63c8883732863aca2e714d6b6"' in generator
    assert (
        'WORLD_SHA256 = "a57a4b88f05ae25ab93b67f3132f25fd3415a6d45ec206d53efa2f7dc1d2d8f3"'
        in generator
    )


def test_populated_v8_preserves_complete_v4_contract_and_reopen(tmp_path: Path) -> None:
    directory = legacy_world(tmp_path)
    assert_legacy_outputs(directory)
    assert_legacy_outputs(directory)
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection, connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (9,)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        for table in ("documents", "bot_document_files", "document_grants"):
            assert connection.execute(f"SELECT count(*) FROM {table}").fetchone() == (0,)  # noqa: S608


def test_migration_only_adds_empty_typed_tables_and_matches_fresh_schema(tmp_path: Path) -> None:
    directory = legacy_world(tmp_path)
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection, connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        retained = {
            table: connection.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608
            for table in tables
        }
    with World.open(directory):
        pass
    with closing(sqlite3.connect(directory / "world.sqlite3")) as connection, connection:
        for table, rows in retained.items():
            assert connection.execute(f"SELECT * FROM {table}").fetchall() == rows  # noqa: S608
        migrated_schema = schema(connection)
        assert [row[1] for row in connection.execute("PRAGMA table_info(documents)")] == [
            "id",
            "sha256",
            "file_name",
            "mime_type",
            "file_unique_id",
        ]
        assert connection.execute(
            "SELECT sql FROM sqlite_master WHERE name='documents'"
        ).fetchone()[0] == (
            "CREATE TABLE documents (id INTEGER PRIMARY KEY, sha256 TEXT NOT NULL REFERENCES "
            "media_blobs(sha256), file_name TEXT NOT NULL, mime_type TEXT NOT NULL, "
            "file_unique_id TEXT NOT NULL UNIQUE, UNIQUE(sha256, file_name, mime_type))"
        )
        assert connection.execute(
            "SELECT sql FROM sqlite_master WHERE name='bot_document_files'"
        ).fetchone()[0] == (
            "CREATE TABLE bot_document_files (bot_id INTEGER NOT NULL REFERENCES bots(id), "
            "file_id TEXT NOT NULL UNIQUE, document_id INTEGER NOT NULL REFERENCES documents(id), "
            "PRIMARY KEY(bot_id, document_id))"
        )
        assert connection.execute(
            "SELECT sql FROM sqlite_master WHERE name='document_grants'"
        ).fetchone()[0] == (
            "CREATE TABLE document_grants (user_id INTEGER NOT NULL REFERENCES users(id), "
            "document_id INTEGER NOT NULL REFERENCES documents(id), "
            "PRIMARY KEY(user_id, document_id))"
        )
    with World.create(tmp_path / "fresh", seed=1, now=1) as fresh:
        assert schema(fresh._connection) == migrated_schema


@pytest.mark.parametrize(
    "statement",
    [
        "CREATE TABLE documents",
        "CREATE TABLE bot_document_files",
        "CREATE TABLE document_grants",
        "PRAGMA foreign_key_check",
        "PRAGMA user_version=9",
    ],
)
def test_interrupted_migration_rolls_back_and_retries(
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
    assert database_state(directory)[0] == 9


def test_concurrent_openers_serialize_schema8_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = legacy_world(tmp_path)
    ready = threading.Barrier(2)
    real_connect = sqlite3.connect
    began: list[int] = []
    created: list[int] = []

    class ScheduledConnection(sqlite3.Connection):
        migrating = False

        def execute(self, sql: str, parameters: Any = ()) -> sqlite3.Cursor:
            if sql == "BEGIN IMMEDIATE" and not self.migrating:
                self.migrating = True
                began.append(threading.get_ident())
                ready.wait(timeout=10)
            if sql.startswith("CREATE TABLE documents"):
                created.append(threading.get_ident())
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
    assert len(set(began)) == 2 and len(created) == 1
    assert_legacy_outputs(directory)
