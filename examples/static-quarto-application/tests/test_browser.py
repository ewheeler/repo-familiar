import socket
import subprocess
import time
from contextlib import closing
from urllib.request import urlopen

import pytest
from playwright.sync_api import sync_playwright


def _free_port() -> int:
    with closing(socket.socket()) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.browser
def test_tutorial_browser_flow() -> None:
    port = _free_port()
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "static_quarto_application.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ]
    )
    try:
        for _ in range(300):
            if process.poll() is not None:
                raise AssertionError("FastAPI exited before becoming ready")
            try:
                with urlopen(f"http://127.0.0.1:{port}/health", timeout=0.2):
                    break
            except OSError:
                time.sleep(0.1)
        else:
            raise AssertionError("FastAPI did not become ready")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.goto(f"http://127.0.0.1:{port}/")
            page.select_option("#category", "beta")
            page.fill("#minimum-value", "10")
            page.get_by_role("button", name="Analyze").click()
            page.get_by_test_id("total").wait_for()
            assert page.get_by_test_id("count").inner_text() == "2"
            assert page.get_by_test_id("total").inner_text() == "36"
            assert page.get_by_test_id("average").inner_text() == "18"
            provenance = page.locator("details code").text_content()
            assert provenance is not None
            assert len(provenance) == 64
            browser.close()
    finally:
        process.terminate()
        process.wait(timeout=5)
