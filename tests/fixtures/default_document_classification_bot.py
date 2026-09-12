"""Real contained bot exercising default ordinary and specialized document uploads."""

import http.client
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def upload(data: bytes, filename: str) -> dict[str, Any]:
    boundary = "gramlab-default-document-boundary"
    delimiter = f"--{boundary}\r\n".encode()
    payload = b"".join(
        (
            delimiter,
            b'Content-Disposition: form-data; name="chat_id"\r\n\r\n1\r\n',
            delimiter,
            f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'.encode(),
            b"Content-Type: application/octet-stream\r\n\r\n",
            data,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        )
    )
    endpoint = urlsplit(os.environ["GRAMLAB_BOT_API"])
    connection = http.client.HTTPConnection("127.0.0.1", endpoint.port, timeout=10)
    try:
        connection.request(
            "POST",
            f"/bot{os.environ['GRAMLAB_BOT_TOKEN']}/sendDocument",
            payload,
            {"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        response = connection.getresponse()
        return {"status": response.status, "body": json.loads(response.read())}
    finally:
        connection.close()


result = {
    "ordinary": upload(Path("ordinary.txt").read_bytes(), "ordinary.txt"),
    "specialized": upload(Path("specialized.gif").read_bytes(), "specialized.gif"),
}
print(json.dumps(result, ensure_ascii=True), flush=True)
