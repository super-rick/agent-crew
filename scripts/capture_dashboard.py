#!/usr/bin/env python3
"""Capture dashboard screenshots for README using Playwright."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = ROOT / "screenshots"
PORT = 8507


def main() -> None:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    # Start Streamlit
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(ROOT / "dashboard" / "app.py"),
            "--server.port",
            str(PORT),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
            "--logger.level",
            "error",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(ROOT),
    )

    url = f"http://localhost:{PORT}"
    try:
        # Wait for dashboard
        import urllib.error
        import urllib.request

        for _ in range(30):
            try:
                urllib.request.urlopen(url, timeout=2)
                break
            except (urllib.error.URLError, OSError):
                time.sleep(1)
        else:
            raise RuntimeError("Dashboard startup timeout")

        time.sleep(3)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(4000)

            for label, filename in [
                ("📈 总览", "dashboard-overview.png"),
                ("📊 发布分析", "dashboard-publishing.png"),
                ("🤖 AI 分析", "dashboard-analytics.png"),
                ("⚙️ 系统状态", "dashboard-system.png"),
            ]:
                print(f"  {label}...")
                # Use label click for Streamlit radio
                btn = page.locator(f"label:has-text('{label}')")
                if btn.count() > 0:
                    btn.first.click()
                    page.wait_for_timeout(5000)
                page.screenshot(path=str(SCREENSHOTS_DIR / filename), full_page=True)

            browser.close()

        print(f"\nDone: {SCREENSHOTS_DIR}/")
        for f in sorted(SCREENSHOTS_DIR.glob("*.png")):
            print(f"  {f.name} ({f.stat().st_size:,} bytes)")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
