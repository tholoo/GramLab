"""Export pinned source and apply GramLab's reviewed client patches, without network access."""

import argparse
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

CLIENT = Path(__file__).resolve().parent


def git(directory: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603 — fixed executable and argument vector
        ["git", "-C", str(directory), *arguments],  # noqa: S607 — provided by the Nix shell
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def export(source: Path, revision: str, destination: Path) -> None:
    if git(source, "rev-parse", "HEAD") != revision:
        raise ValueError(f"Source revision does not match the lock: {source.name}")
    with tempfile.TemporaryDirectory(prefix="gramlab-archive-") as temporary:
        archive = Path(temporary) / "source.tar"
        git(source, "archive", "--format=tar", f"--output={archive}", revision)
        with tarfile.open(archive) as stream:
            # Tracked source only: never copy a developer's ignored settings or credentials.
            stream.extractall(destination, filter="data")


def prepare(upstream: Path, destination: Path) -> None:
    lock = json.loads((CLIENT / "upstream-lock.json").read_text())
    if destination.exists() or destination.is_symlink():
        raise ValueError(
            "Destination must be a new directory; existing builds are never overwritten"
        )
    # Check every input revision before creating output. Submodule archives do not contain .git.
    sources = [(upstream, lock["clientRevision"], Path())]
    sources.extend(
        (upstream / entry["path"], entry["revision"], Path(entry["path"]))
        for entry in lock["submodules"]
    )
    for source, revision, _ in sources:
        if git(source, "rev-parse", "HEAD") != revision:
            raise ValueError(f"Source revision does not match the lock: {source.name}")
    destination.mkdir(parents=True, mode=0o700)
    for source, revision, relative in sources:
        export(source, revision, destination / relative)

    # Upstream carries public distribution templates; none are GramLab credentials.
    for name in ("*.keystore", "*.jks", "google-services.json", "local.properties"):
        for path in destination.rglob(name):
            path.unlink()
    variables = destination / "TMessagesProj/src/main/java/org/telegram/messenger/BuildVars.java"
    body = variables.read_text()
    for field, value in (
        ("APP_ID", "0"),
        ("APP_HASH", '""'),
        ("SAFETYNET_KEY", '""'),
        ("HUAWEI_APP_ID", '""'),
    ):
        body, count = re.subn(
            rf"(public static (?:int|String) {field}\s*=\s*)[^;]+;", rf"\g<1>{value};", body
        )
        if count != 1:
            raise ValueError(f"Expected one upstream credential declaration for {field}")
    variables.write_text(body)

    # A local empty repository prevents git apply from discovering the enclosing GramLab repo.
    git(destination, "init", "--quiet")
    series = (CLIENT / "patches/series").read_text().splitlines()
    for name in series:
        if not name or name.startswith("#"):
            continue
        if Path(name).name != name:
            raise ValueError("Patch series entries must be plain filenames")
        patch = CLIENT / "patches" / name
        git(destination, "apply", "--check", str(patch))
        git(destination, "apply", str(patch))
    shutil.copy2(CLIENT / "upstream-lock.json", destination / "gramlab-source-lock.json")
    shutil.copy2(
        CLIENT / "dependency-verification.xml", destination / "gradle/verification-metadata.xml"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, default=CLIENT / "upstream")
    parser.add_argument("--destination", required=True, type=Path)
    options = parser.parse_args()
    prepare(options.upstream.resolve(), options.destination.absolute())
    print("Pinned source exported and patch queue applied. No application was run.")


if __name__ == "__main__":
    main()
