"""Regenerate bounded BSL reference data from hash-verified pinned sources, entirely offline."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zlib
from pathlib import Path
from typing import Any

PIN = "bc9c263e2bfee06aaab41e82db51a103376030bc"
SOURCES = {
    "unicode.cpp": "523b23ed0b245ac278b7e295051e4b7a0bbc20c921b7da1f1e401b28ab86d8ee",
    "unicode.h": "8682c267767f0e7bff59b25967638018efd2d75a98dc3aa475d23ac20f7c961e",
    "generate_mime_types_gperf.cpp": (
        "26cafccc6cc22b0920bf83e63ea7a0362cce00d8710977eccf6c0ee9d4005e13"
    ),
    "mime_types.txt": "cf624424122258b7f58815207fcdd79769a1d3397ac2a1cbbe42124553af8244",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def packed(value: Any) -> str:
    return base64.b85encode(
        zlib.compress(json.dumps(value, separators=(",", ":")).encode(), 9)
    ).decode()


def regenerate(source: Path, output: Path, compiler: str) -> None:
    if output.exists() or output.is_symlink():
        raise FileExistsError("Reference output already exists: " + str(output))
    # No network or production-module import. Compile actual pinned source, not Python behavior.
    sources: dict[str, bytes] = {}
    for name, expected in SOURCES.items():
        raw = (source / name).read_bytes()
        if digest(raw) != expected:
            raise ValueError("Pinned source hash mismatch: " + name)
        sources[name] = raw
    filesystem = (source / "filesystem.cpp").read_text()
    # Hash supplied in committed provenance; verify it before extracting the original lambda.
    provenance = json.loads(
        Path("docs/development/tdlib-document-metadata-provenance.json").read_text()
    )
    expected = next(
        item["sha256"] for item in provenance["sources"] if item["path"].endswith("/filesystem.cpp")
    )
    if digest(filesystem.encode()) != expected:
        raise ValueError("Pinned filesystem source hash mismatch")
    lambda_start = filesystem.index("  auto is_ok = []")
    lambda_end = filesystem.index("\n  };", lambda_start) + len("\n  };")
    original_lambda = filesystem[lambda_start:lambda_end]
    unicode = sources["unicode.cpp"].decode()
    unicode = re.sub(r"^#include .*\n", "", unicode, flags=re.MULTILINE)
    enum = re.search(r"enum class UnicodeSimpleCategory[^;]+;", sources["unicode.h"].decode())
    if enum is None:
        raise ValueError("Pinned enum missing")
    prefix = (
        """#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <cstddef>
namespace td {
using uint32 = std::uint32_t; using uint16 = std::uint16_t;
using int32 = std::int32_t; using int16 = std::int16_t;
"""
        + enum[0]
        + """
}
struct FatalLog {
  template<class T> FatalLog &operator<<(const T &) { return *this; }
  ~FatalLog() { std::abort(); }
};
#define LOG(level) FatalLog()
"""
    )
    main = (
        """
int main() {
  using namespace td;
"""
        + original_lambda
        + """
  for (uint32 code = 0; code <= 0x10ffff; ++code) {
    unsigned char kind = is_ok(code) ? 2 : (prepare_search_character(code) == 0 ? 0 : 1);
    std::cout.put(static_cast<char>(kind));
  }
  return std::cout.good() ? 0 : 1;
}
"""
    )
    compiler_path = shutil.which(compiler)
    if compiler_path is None:
        raise ValueError("C++ compiler unavailable")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="document-oracle-", dir=output.parent) as temporary:
        build = Path(temporary)
        unit = build / "unicode-oracle.cpp"
        unit.write_text(prefix + unicode + main)
        executable = build / "unicode-oracle"
        subprocess.run(  # noqa: S603 — hash-verified pinned offline reference
            [compiler_path, "-std=c++17", "-O2", str(unit), "-o", str(executable)], check=True
        )
        raw = subprocess.run([str(executable)], check=True, capture_output=True).stdout  # noqa: S603 — bounded scalar enumeration
        if len(raw) != 0x110000 or not set(raw) <= {0, 1, 2}:
            raise ValueError("Invalid reference character stream")
        boundaries = [
            (index << 2) | kind
            for index, kind in enumerate(raw)
            if index == 0 or kind != raw[index - 1]
        ]
        masked = bytearray(raw)
        masked[0xD800:0xE000] = b"\xff" * 0x800
        masked[ord("/")] = masked[ord("\\")] = 255
        generator = build / "mime-generator"
        subprocess.run(  # noqa: S603 — hash-verified pinned offline reference
            [
                compiler_path,
                "-std=c++17",
                "-O2",
                str(source / "generate_mime_types_gperf.cpp"),
                "-o",
                str(generator),
            ],
            check=True,
        )
        forward, reverse = build / "mime-to-ext.gperf", build / "ext-to-mime.gperf"
        subprocess.run(  # noqa: S603 — hash-verified pinned offline reference
            [str(generator), str(source / "mime_types.txt"), str(forward), str(reverse)], check=True
        )
        generated = reverse.read_text()
        if "%ignore-case\n" not in generated:
            raise ValueError("Expected original ASCII case-insensitive lookup")
        rows = csv.reader(generated.split("%%\n")[1].splitlines(), skipinitialspace=True)
        mime = {extension: mime_type for extension, mime_type in rows}
        if len(mime) != sum(1 for _ in generated.split("%%\n")[1].splitlines()):
            raise ValueError("Duplicate generated extension")
        result = {
            "schema": 1,
            "revision": PIN,
            "license": "BSL-1.0",
            "unicode_kind_sha256": digest(raw),
            "unicode_public_probe_sha256": digest(bytes(masked)),
            "unicode_boundaries": len(boundaries),
            "mime_entries": len(mime),
            "packed_data": packed([boundaries, mime]),
            "mime": mime,
            "unicode_translation_unit_sha256": digest(unit.read_bytes()),
            "extension_gperf_sha256": digest(reverse.read_bytes()),
        }
        with output.open("x", encoding="utf-8") as destination:
            destination.write(json.dumps(result, ensure_ascii=True, indent=2) + "\n")
        print(
            json.dumps(
                {key: value for key, value in result.items() if key not in {"packed_data", "mime"}}
            )
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--compiler", default="c++")
    arguments = parser.parse_args()
    regenerate(arguments.source.resolve(), arguments.output.absolute(), arguments.compiler)
