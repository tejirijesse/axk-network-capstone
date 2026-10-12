#!/usr/bin/env python3
"""Run the standalone server and integration tests in an isolated environment."""

import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PORT = 8765
BASE_URL = f"http://127.0.0.1:{PORT}"


def wait_until_ready(process, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("The local server stopped before becoming ready")
        try:
            with urllib.request.urlopen(f"{BASE_URL}/trade", timeout=0.5) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"The local server did not become ready at {BASE_URL}")


def main():
    with tempfile.TemporaryDirectory(prefix="axk-local-test-") as temp_dir:
        environment = os.environ.copy()
        environment["PORT"] = str(PORT)
        environment["AXK_DB_PATH"] = str(Path(temp_dir) / "axk-test.db")
        environment["AXK_BASE_URL"] = BASE_URL

        log_path = Path(temp_dir) / "server.log"
        with log_path.open("w+") as server_log:
            server = subprocess.Popen(
                [sys.executable, str(ROOT / "scripts" / "server.py")],
                cwd=ROOT,
                env=environment,
                stdout=server_log,
                stderr=subprocess.STDOUT,
            )
            try:
                wait_until_ready(server)
                return subprocess.call(
                    [sys.executable, str(ROOT / "scripts" / "test_trade.py")],
                    cwd=ROOT,
                    env=environment,
                )
            except Exception:
                server_log.flush()
                server_log.seek(0)
                print(server_log.read(), file=sys.stderr)
                raise
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == "__main__":
    raise SystemExit(main())
