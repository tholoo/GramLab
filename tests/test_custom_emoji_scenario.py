"""Register original media through the actual authenticated scenario control."""

import http.client
import io
import json
import random
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from PIL import Image

from gramlab._control import WorldControl
from gramlab.scenario import Scenario, ScenarioError
from gramlab.world import World


def _large_webp() -> bytes:
    # Independent source pixels ensure the complete registration exceeds the old 64 KiB limit.
    source = random.Random(811).randbytes(100 * 100 * 4)
    image = Image.frombytes("RGBA", (100, 100), source)
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", lossless=True, exact=True)
    return buffer.getvalue()


def test_scenario_registers_large_media_and_retries_after_reopen(tmp_path: Path) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    data = _large_webp()
    assert len(data) * 2 * 4 // 3 > 65536
    expected = {
        "custom_emoji_id": "9223372036854775807",
        "fallback": "🙂",
        "free": True,
        "needs_repainting": False,
        "main_asset_id": 1,
        "thumbnail_asset_id": 1,
        "duration_ms": 0,
    }
    for _ in range(2):
        with WorldControl(directory) as control:
            scenario = Scenario(
                control.base_url, capability=control.capability, world_id=control.world_id
            )
            assert (
                scenario.register_custom_emoji(
                    request_id="large-original",
                    custom_emoji_id="9223372036854775807",
                    main=data,
                    thumbnail=data,
                    fallback="🙂",
                )
                == expected
            )
            assert scenario.snapshot() == {
                "schema": 1,
                "seed": 7,
                "now": 100,
                "users": [],
                "chats": [],
            }
            assert scenario.events() == []
            with pytest.raises(ScenarioError) as failure:
                scenario.register_custom_emoji(
                    request_id="large-original", main=data, thumbnail=data, fallback="Different"
                )
            assert (failure.value.code, failure.value.outcome_uncertain) == (
                "invalid_request",
                False,
            )


@pytest.mark.parametrize("operation", ["snapshot", "create_user", "register_custom_emoji"])
def test_dedicated_registration_route_rejects_wrong_operation_or_invalid_bytes(
    tmp_path: Path, operation: str
) -> None:
    directory = tmp_path / "world"
    with World.create(directory, seed=7, now=100):
        pass
    with WorldControl(directory) as control:
        url = urlsplit(control.base_url)
        connection = http.client.HTTPConnection("127.0.0.1", url.port, timeout=3)
        try:
            connection.request(
                "POST",
                "/v1/custom-emoji",
                json.dumps(
                    {
                        "schema": 1,
                        "world_id": control.world_id,
                        "operation": operation,
                        "parameters": {
                            "request_id": "bad",
                            "main": "%%%",
                            "thumbnail": "",
                            "fallback": "🙂",
                        },
                    }
                ),
                {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + control.capability,
                },
            )
            response = connection.getresponse()
            body = json.loads(response.read())
            assert response.status == (400 if operation == "register_custom_emoji" else 404)
            assert body["error"]["code"] == (
                "invalid_request" if operation == "register_custom_emoji" else "unsupported"
            )
        finally:
            connection.close()
    with World.open(directory) as world:
        assert world.events() == []
        assert world.snapshot()["users"] == []
