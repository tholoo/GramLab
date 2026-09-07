"""Verify actual HTTP fault stimuli before using them as native acceptance evidence."""

import http.client
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from probes.media_transfer_server import Fault, MediaTransferServer

PHOTO = Path("tests/assets/rich-media/photo-quadrants-64x48.jpg").read_bytes()
SNAPSHOT = {"schema": 3, "world_id": "fixture", "assets": []}
AUTHORIZATION = {"Authorization": "Bearer synthetic-fixture-capability"}


def connection(server: MediaTransferServer) -> http.client.HTTPConnection:
    return http.client.HTTPConnection("127.0.0.1", urlsplit(server.base_url).port, timeout=5)


@pytest.mark.parametrize("fault", ["complete", "truncate", "corrupt", "redirect", "missing"])
def test_fixture_emits_real_transfer_faults(fault: Fault) -> None:
    with MediaTransferServer(
        snapshot=SNAPSHOT,
        assets={1: ("image/jpeg", PHOTO)},
        capability="synthetic-fixture-capability",
    ) as server:
        planned = server.plan(1, fault)
        client = connection(server)
        try:
            client.request("GET", "/v3/assets/1", headers=AUTHORIZATION)
            response = client.getresponse()
            if fault == "truncate":
                with pytest.raises(http.client.IncompleteRead) as failure:
                    response.read()
                assert failure.value.partial == PHOTO[: len(PHOTO) // 2]
                assert int(response.getheader("Content-Length", "0")) == len(PHOTO)
            elif fault == "missing":
                assert response.status == 404
                assert json.loads(response.read()) == {
                    "schema": 3,
                    "error": {"code": "asset_unavailable", "message": "Asset is unavailable"},
                }
            elif fault == "redirect":
                assert response.status == 302
                assert response.getheader("Location") == "http://192.0.2.1/forbidden-media"
                assert response.read() == b""
            else:
                assert response.status == 200
                assert response.getheader("Content-Type") == "image/jpeg"
                observed = response.read()
                assert len(observed) == len(PHOTO)
                if fault == "complete":
                    assert observed == PHOTO
                else:
                    assert observed != PHOTO
            assert planned.finished.wait(timeout=5)
            assert server.requests() == [{"operation": "asset", "asset_id": 1, "fault": fault}]
        finally:
            client.close()


def test_delayed_old_transfer_finishes_after_snapshot_edit() -> None:
    with MediaTransferServer(
        snapshot=SNAPSHOT,
        assets={1: ("image/jpeg", PHOTO)},
        capability="synthetic-fixture-capability",
    ) as server:
        old = server.plan(1, "gated")

        def download() -> bytes:
            client = connection(server)
            try:
                client.request("GET", "/v3/assets/1", headers=AUTHORIZATION)
                return client.getresponse().read()
            finally:
                client.close()

        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(download)
            try:
                assert old.partial_sent.wait(timeout=5)
                assert not result.done()
                updated = {"schema": 3, "world_id": "fixture", "assets": [{"asset_id": 2}]}
                server.snapshot(updated)
                client = connection(server)
                try:
                    client.request("GET", "/v3/snapshot", headers=AUTHORIZATION)
                    assert json.loads(client.getresponse().read()) == updated
                finally:
                    client.close()
                assert not result.done()
            finally:
                old.release.set()
            assert result.result(timeout=5) == PHOTO
        assert old.finished.wait(timeout=5)


def test_unauthorized_request_does_not_consume_planned_fault() -> None:
    with MediaTransferServer(
        snapshot=SNAPSHOT,
        assets={1: ("image/jpeg", PHOTO)},
        capability="synthetic-fixture-capability",
    ) as server:
        fault = server.plan(1, "missing")
        client = connection(server)
        try:
            client.request("GET", "/v3/assets/1")
            response = client.getresponse()
            assert response.status == 401
            assert json.loads(response.read()) == {
                "schema": 3,
                "error": {"code": "unauthorized", "message": "Client capability required"},
            }
            assert not fault.started.is_set()
            assert server.requests() == [{"operation": "unauthorized"}]
            client.request("GET", "/v3/assets/1", headers=AUTHORIZATION)
            response = client.getresponse()
            assert response.status == 404
            response.read()
            assert fault.finished.wait(timeout=5)
        finally:
            client.close()
