"""Original, self-contained HTML evidence; never reconstructs the Android chat UI."""

from __future__ import annotations

import hashlib
import html
import json
import math
import os
import re
import struct
import tempfile
import zlib
from base64 import b64encode
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote, quote_plus


@dataclass(frozen=True, kw_only=True)
class Screenshot:
    caption: str
    png: bytes


@dataclass(frozen=True, kw_only=True)
class Finding:
    stage: Literal["observed", "proposed", "applied", "verified"]
    title: str
    detail: str


@dataclass(frozen=True, kw_only=True)
class Report:
    run_id: str
    title: str
    mode: Literal["simulation-only", "headless-android", "interactive-android"]
    outcome: Literal["passed", "failed", "incomplete"]
    seed: int
    profile: Mapping[str, str]
    summary: str = ""
    evidence: Mapping[str, Any] = field(default_factory=dict)
    limitations: Sequence[str] = ()
    screenshots: Sequence[Screenshot] = ()
    findings: Sequence[Finding] = ()
    timings: Mapping[str, float] = field(default_factory=dict)


_STYLE = """
:root{color-scheme:light;
--ink:#182925;
--muted:#52635d;
--line:#d9e2db;
--accent:#176b52}

*{box-sizing:border-box}
body{margin:0;
background:#f3f6f1;
color:var(--ink);
font:16px/1.6 system-ui,sans-serif}

main{max-width:1120px;
margin:auto;
padding:44px 24px 72px}
header{padding:30px 0;
border-bottom:1px solid var(--line)}

.eyebrow{font-size:12px;
font-weight:750;
letter-spacing:.16em;
text-transform:uppercase;
color:var(--accent)}

h1{font-size:clamp(30px,5vw,48px);
line-height:1.14;
letter-spacing:-.04em;
max-width:840px;
margin:18px 0}

h2{font-size:23px;
letter-spacing:-.02em;
margin:0 0 18px}
h3{font-size:16px;
margin:0 0 12px}

p{max-width:840px}
.muted{color:var(--muted)}
.badge{display:inline-block;
padding:4px 12px;
border-radius:6px;

font-size:13px;
font-weight:750;
background:#e2eee5;
color:#17553f}
.failed{background:#fbe5df;
color:#932f22}

.incomplete{background:#fff0cf;
color:#735309}
section{margin-top:32px}
dl{display:grid;
grid-template-columns:repeat(3,minmax(0,1fr));
gap:12px}

dl div,.card,details{background:#fff;
border:1px solid var(--line);
border-radius:10px;
padding:18px}

dt{font-size:12px;
text-transform:uppercase;
letter-spacing:.06em;
color:var(--muted)}
dd{margin:4px 0 0;
overflow-wrap:anywhere}

details{margin:12px 0}
summary{cursor:pointer;
font-weight:650}
pre{font:13px/1.6 ui-monospace,monospace;

white-space:pre-wrap;
overflow-wrap:anywhere;
margin:18px 0 0;
background:#f7f9f6;
padding:16px;
border-radius:6px;
tab-size:2}

li{margin:8px 0}
footer{margin-top:40px;
padding-top:18px;
border-top:1px solid var(--line);
font-size:13px;
color:var(--muted)}

.gallery{display:grid;
grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
gap:18px}

figure{margin:0;
padding:18px;
background:#fff;
border:1px solid var(--line);
border-radius:10px}

figure img{display:block;
max-width:100%;
height:auto;
max-height:560px;
margin:auto;
object-fit:contain}

figcaption{margin-top:18px;
font-size:14px;
font-weight:650}
.findings{display:grid;
grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
gap:12px}

.finding p{margin:12px 0 0}
.stage{font-size:11px;
letter-spacing:.08em;
text-transform:uppercase;
color:var(--muted)}

table{width:100%;
border-collapse:collapse}
th,td{text-align:left;
padding:12px;
border-bottom:1px solid var(--line)}

td:last-child{text-align:right;
font-variant-numeric:tabular-nums;
white-space:nowrap}

@media(max-width:650px){main{padding:20px 16px 40px}
dl{grid-template-columns:1fr}
header{padding-top:12px}
}

@media print{body{background:white}
main{max-width:none;
padding:0}
details{break-inside:avoid}
details>pre{display:block}
}

"""


_SECRET_KEYS = {
    "authorization",
    "proxy_authorization",
    "cookie",
    "set_cookie",
    "x_api_key",
    "api_key",
    "password",
    "passwd",
    "secret",
    "api_hash",
    "token",
    "bot_token",
    "client_token",
    "access_token",
    "refresh_token",
    "capability",
}
_TOKENS = re.compile(
    r"gramlab-client_[A-Za-z0-9_-]+|(?<![0-9])[0-9]{1,20}(?::|%3[aA])"
    r"(?:gramlab_)?[A-Za-z0-9_-]{20,}"
)
_HEADERS = re.compile(
    r"(?im)\b(authorization|proxy-authorization|cookie|set-cookie)(\s*:\s*)[^\r\n]+"
)
_ASSIGNMENTS = re.compile(
    r"(?i)\b(password|passwd|api[_-]hash|(?:access|refresh|bot|client)[_-]token|api[_-]key|capability|secret)"
    r"\b(\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s&;,]+)"
)


class _Redactor:
    def __init__(self, secrets: Sequence[str]) -> None:
        variants: set[str] = set()
        for secret in secrets:
            if not isinstance(secret, str) or not secret:
                raise ValueError("Registered secrets must be nonempty strings")
            variants.update((secret, quote(secret, safe=""), quote_plus(secret, safe="")))
        self.secrets = sorted(variants, key=len, reverse=True)

    def text(self, value: str) -> str:
        for secret in self.secrets:
            value = value.replace(secret, "[REDACTED]")
        value = _TOKENS.sub("[REDACTED]", value)
        value = _HEADERS.sub(lambda match: match[1] + match[2] + "[REDACTED]", value)
        return _ASSIGNMENTS.sub(lambda match: match[1] + match[2] + "[REDACTED]", value)

    def clean(self, value: Any, depth: int = 0) -> Any:
        if depth > 50:
            raise ValueError("Report evidence exceeds the nesting limit")
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, Mapping):
            result = {}
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValueError("Report evidence keys must be strings")
                sensitive = re.sub(r"[\s-]", "_", key.lower()) in _SECRET_KEYS
                label = self.text(key)
                if label in result:
                    raise ValueError("Redaction produces duplicate evidence keys")
                result[label] = "[REDACTED]" if sensitive else self.clean(item, depth + 1)
            return result
        if isinstance(value, (list, tuple)):
            return [self.clean(item, depth + 1) for item in value]
        if value is None or isinstance(value, (bool, int, float)):
            return value
        raise ValueError("Report evidence must contain JSON values")


def _png(value: bytes, redactor: _Redactor) -> None:
    """Validate bounded RGB/RGBA screenshots without changing their pixels or bytes."""
    if (
        not isinstance(value, bytes)
        or len(value) > 8 * 1024 * 1024
        or not value.startswith(b"\x89PNG\r\n\x1a\n")
    ):
        raise ValueError("Screenshot must be a bounded PNG")
    if _TOKENS.search(value.decode("latin1")) or any(
        secret.encode() in value for secret in redactor.secrets
    ):
        raise ValueError("Screenshot contains credential-shaped bytes")
    offset, width, height, channels = 8, 0, 0, 0
    compressed = bytearray()
    ended = False
    while offset + 12 <= len(value):
        size = struct.unpack_from(">I", value, offset)[0]
        kind = value[offset + 4 : offset + 8]
        end = offset + 12 + size
        if end > len(value):
            raise ValueError("Truncated screenshot PNG")
        payload = value[offset + 8 : end - 4]
        if zlib.crc32(kind + payload) != struct.unpack_from(">I", value, end - 4)[0]:
            raise ValueError("Screenshot PNG checksum mismatch")
        if kind == b"IHDR":
            if offset != 8 or size != 13:
                raise ValueError("Invalid screenshot PNG header")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            if (
                not 0 < width * height <= 16_000_000
                or depth != 8
                or color not in (2, 6)
                or any((compression, filtering, interlace))
            ):
                raise ValueError("Screenshot requires bounded non-interlaced 8-bit RGB/RGBA")
            channels = 3 if color == 2 else 4
        elif not channels:
            raise ValueError("Missing screenshot PNG header")
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            if size or end != len(value):
                raise ValueError("Invalid screenshot PNG ending")
            ended = True
            break
        elif (
            kind not in {b"sRGB", b"sBIT", b"gAMA", b"cHRM", b"pHYs"}
            or size
            != {
                b"sRGB": 1,
                b"sBIT": channels,
                b"gAMA": 4,
                b"cHRM": 32,
                b"pHYs": 9,
            }[kind]
        ):
            raise ValueError("Unsupported screenshot PNG metadata")
        offset = end
    if not ended or not compressed:
        raise ValueError("Incomplete screenshot PNG")
    expected = (width * channels + 1) * height
    inflater = zlib.decompressobj()
    try:
        raw = inflater.decompress(compressed, expected + 1)
    except zlib.error:
        raise ValueError("Invalid screenshot PNG compression") from None
    if len(raw) != expected or not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:
        raise ValueError("Screenshot PNG scanline length mismatch")
    if any(raw[index] > 4 for index in range(0, expected, width * channels + 1)):
        raise ValueError("Invalid screenshot PNG filter")


def _validate(report: Report, redactor: _Redactor) -> None:
    if report.mode not in {"simulation-only", "headless-android", "interactive-android"}:
        raise ValueError("Unknown report execution mode")
    if report.outcome not in {"passed", "failed", "incomplete"}:
        raise ValueError("Unknown report outcome")
    if type(report.seed) is not int:
        raise ValueError("Report seed must be an integer")
    if not report.run_id or not report.title:
        raise ValueError("Report requires run identity and title")
    if any(
        not isinstance(name, str) or not isinstance(value, str)
        for name, value in report.profile.items()
    ):
        raise ValueError("Profile labels and values must be text")
    if any(name.lower() in {"run", "mode", "seed"} for name in report.profile):
        raise ValueError("Profile cannot override run metadata")
    if any(
        type(value) not in (int, float) or not math.isfinite(value) or value < 0
        for value in report.timings.values()
    ):
        raise ValueError("Report timings must be finite nonnegative milliseconds")
    if any(
        item.stage not in {"observed", "proposed", "applied", "verified"}
        for item in report.findings
    ):
        raise ValueError("Unknown finding stage")
    if len(report.screenshots) > 8:
        raise ValueError("Report exceeds the screenshot limit")
    for item in report.screenshots:
        _png(item.png, redactor)


def write_report(destination: Path, report: Report, *, secrets: Sequence[str] = ()) -> Path:
    """Write a new local report, refusing to replace an existing artifact."""
    redactor = _Redactor(secrets)
    _validate(report, redactor)

    def escape(value: str) -> str:
        return html.escape(redactor.text(value), quote=True)

    style_hash = b64encode(hashlib.sha256(_STYLE.encode()).digest()).decode()
    policy = (
        "default-src 'none'; base-uri 'none'; form-action 'none'; "
        f"style-src 'sha256-{style_hash}'; img-src data:"
    )
    metadata = {
        "Run": report.run_id,
        "Mode": report.mode,
        "Seed": str(report.seed),
        **redactor.clean(report.profile),
    }
    facts = "".join(
        f"<div><dt>{escape(name)}</dt><dd dir='auto'>{escape(value)}</dd></div>"
        for name, value in metadata.items()
    )
    evidence = "".join(
        f"<details{' open' if index == 0 else ''}><summary>{escape(name)}</summary><pre dir='auto'>"
        + html.escape(
            json.dumps(redactor.clean(value), ensure_ascii=False, indent=2, allow_nan=False),
            quote=True,
        )
        + "</pre></details>"
        for index, (name, value) in enumerate(report.evidence.items())
    )
    limitations = "".join(f"<li dir='auto'>{escape(value)}</li>" for value in report.limitations)
    screenshots = "".join(
        f'<figure><img alt="{escape(item.caption)}" src="data:image/png;base64,'
        + b64encode(item.png).decode()
        + f'"><figcaption dir="auto">{escape(item.caption)}</figcaption></figure>'
        for item in report.screenshots
    )
    gallery = (
        f'<section><h2>Android evidence</h2><div class="gallery">{screenshots}</div></section>'
        if screenshots
        else ""
    )
    findings = "".join(
        f'<article class="card finding"><div class="stage">{escape(item.stage)}</div>'
        f'<h3 dir="auto">{escape(item.title)}</h3><p dir="auto">{escape(item.detail)}</p></article>'
        for item in report.findings
    )
    findings_section = (
        f'<section><h2>Findings and changes</h2><div class="findings">{findings}</div></section>'
        if findings
        else ""
    )
    timings = "".join(
        f"<tr><th scope='row'>{escape(name)}</th><td>{value:,.1f} ms</td></tr>"
        for name, value in report.timings.items()
    )
    timing_section = (
        '<section><h2>Recorded timings</h2><div class="card"><table>'
        f"<tbody>{timings}</tbody></table></div></section>"
        if timings
        else ""
    )
    source = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{escape(policy)}">
<title>{escape(report.title)} · GramLab</title><style>{_STYLE}</style></head>
<body><main><header><div class="eyebrow">GramLab / Run evidence</div>
<h1 dir="auto">{escape(report.title)}</h1>
<span class="badge {escape(report.outcome)}">{escape(report.outcome)}</span>
<p dir="auto">{escape(report.summary)}</p>
<p class="muted">Synthetic conversation · local execution</p></header>
<section aria-label="Run profile"><dl>{facts}</dl></section>
{gallery}{findings_section}{timing_section}
<section><h2>Recorded evidence</h2>{evidence}</section>
<section><h2>Limits of this result</h2><div class="card"><ul>{limitations}</ul></div></section>
<footer>GramLab evidence report · No external resources or scripts<br>
Reported outcomes are supplied by the scenario.</footer>
</main></body></html>"""
    payload = source.encode("utf-8", errors="strict")
    if len(payload) > 16 * 1024 * 1024:
        raise ValueError("Report exceeds the artifact size limit")
    descriptor, temporary = tempfile.mkstemp(prefix=".gramlab-report-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
    finally:
        Path(temporary).unlink()
    return destination
