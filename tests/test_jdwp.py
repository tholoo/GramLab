"""A real JVM proves that the debugger stops only the selected storage method."""

import os
import re
import selectors
import subprocess
from pathlib import Path

import pytest
from probes.jdwp import Debugger

pytestmark = pytest.mark.android  # The pinned JDK belongs to the Android toolchain.


def test_breakpoint_holds_real_storage_while_other_threads_run(tmp_path: Path):
    jdk = os.environ.get("JAVA_HOME")
    if jdk is None:
        pytest.skip("Requires the provisioned JDK")
    subprocess.run(  # noqa: S603 — provisioned JDK and repository-owned fixture.
        [
            str(Path(jdk) / "bin/javac"),
            "-g",
            "-d",
            str(tmp_path),
            "tests/fixtures/StorageFaultTarget.java",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    destination = tmp_path / "stored.txt"
    process = subprocess.Popen(  # noqa: S603 — same pinned JDK and compiled owned fixture.
        [
            str(Path(jdk) / "bin/java"),
            "-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=127.0.0.1:0",
            "-cp",
            str(tmp_path),
            "StorageFaultTarget",
            str(destination),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    debugger = None
    try:
        assert process.stdout is not None and process.stdin is not None

        def line():
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                assert selector.select(10), "JVM fixture produced no output"
            return process.stdout.readline().decode().strip()

        listening = line()
        port = re.fullmatch(r"Listening for transport dt_socket at address: (\d+)", listening)
        assert port, listening
        assert line() == "ready"
        debugger = Debugger(int(port[1]))
        with pytest.raises(ValueError, match="unique method"):
            debugger.breakpoint("LStorageFaultTarget;", "absent", "(I)V")
        debugger.breakpoint("LStorageFaultTarget;", "persist", "(I)V")
        process.stdin.write(b"send\n")
        stopped = debugger.wait_breakpoint(arguments=["id"], timeout=10)
        assert stopped["thread_name"] == "storageQueue_0"
        assert stopped["suspend_policy"] == "event_thread"
        assert stopped["arguments"] == {"id": 42}
        assert not destination.exists()
        process.stdin.write(b"ping\n")
        assert line() == "alive"  # Main thread remains runnable while storage is suspended.
        assert not destination.exists()
        debugger.resume()
        assert line() == "stored"
        assert destination.read_text() == "42"
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        if debugger is not None:
            debugger.close()
