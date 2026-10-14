#!/usr/bin/env python3
"""Download a file through Chromium/Playwright, optionally by clicking DOM controls."""

from __future__ import annotations

import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

OUT_DIR = Path("downloads")
MAX_SCRIPT_BYTES = 2 * 1024 * 1024


def require_http_url(value: str, label: str) -> str:
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"{label} must be a valid http:// or https:// URL")
    return value


def load_script(script_url: str) -> str:
    script_url = require_http_url(script_url, "SCRIPT_URL")
    if urlparse(script_url).scheme != "https":
        raise ValueError("SCRIPT_URL must use HTTPS")
    request = urllib.request.Request(
        script_url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; Chromium-DOM-Downloader/1.0)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read(MAX_SCRIPT_BYTES + 1)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not fetch SCRIPT_URL: {exc}") from exc
    if len(data) > MAX_SCRIPT_BYTES:
        raise RuntimeError("Script is larger than the 2 MiB safety limit")
    try:
        source = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise RuntimeError("SCRIPT_URL did not return UTF-8 JavaScript") from exc
    if not source.strip():
        raise RuntimeError("SCRIPT_URL returned an empty script")
    print(f"Loaded optional init script ({len(data):,} bytes)")
    return source


def safe_filename(name: str) -> str:
    name = name.replace("\\", "/").split("/")[-1]
    name = re.sub(r"[\x00-\x1f<>:\"/\\|?*]", "_", name).strip(" .")
    return name[:180] or "download.bin"


def main() -> int:
    url = require_http_url(os.environ.get("DOWNLOAD_URL", ""), "DOWNLOAD_URL")
    prepare_selector = os.environ.get("PREPARE_SELECTOR", "").strip()
    download_selector = os.environ.get("DOWNLOAD_SELECTOR", "").strip()
    script_url = os.environ.get("SCRIPT_URL", "").strip()
    try:
        timeout_seconds = int(float(os.environ.get("TIMEOUT_SECONDS", "180")))
    except ValueError:
        raise ValueError("TIMEOUT_SECONDS must be a number")
    timeout_seconds = max(30, min(900, timeout_seconds))
    timeout_ms = timeout_seconds * 1000

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Keep each run clean so a stale file cannot make a failed run look successful.
    for old_file in OUT_DIR.iterdir():
        if old_file.is_file():
            old_file.unlink()

    init_script = load_script(script_url) if script_url else None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        context.set_default_timeout(timeout_ms)
        if init_script:
            context.add_init_script(script=init_script)
        page = context.new_page()
        page.on("console", lambda msg: print(f"[browser console:{msg.type}] {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda exc: print(f"[browser page error] {exc}"))

        try:
            if download_selector:
                print(f"Opening page: {url}")
                response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                print(f"Page title: {page.title()}")
                print(f"Final URL: {page.url}")
                if response is not None:
                    print(f"HTTP status: {response.status}")
                if prepare_selector:
                    print(f"Clicking prepare selector: {prepare_selector}")
                    page.locator(prepare_selector).first.click(timeout=timeout_ms)
                print(f"Clicking download selector: {download_selector}")
                with page.expect_download(timeout=timeout_ms) as info:
                    page.locator(download_selector).first.click(timeout=timeout_ms)
                download = info.value
            else:
                # Direct-download mode: trigger the browser's normal download handling.
                print(f"Starting direct browser download: {url}")
                page.goto("about:blank")
                with page.expect_download(timeout=timeout_ms) as info:
                    page.evaluate(
                        """url => {
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = '';
                            a.rel = 'noopener';
                            document.body.appendChild(a);
                            a.click();
                            a.remove();
                        }""",
                        url,
                    )
                download = info.value

            failure = download.failure()
            if failure:
                raise RuntimeError(f"Browser download failed: {failure}")
            filename = safe_filename(download.suggested_filename)
            destination = OUT_DIR / filename
            download.save_as(str(destination))
            if not destination.is_file() or destination.stat().st_size == 0:
                raise RuntimeError("Playwright reported a download, but the saved file is missing or empty")
            print(f"Saved: {destination} ({destination.stat().st_size:,} bytes)")
            return 0
        except PlaywrightTimeoutError as exc:
            page.screenshot(path="downloads/failure.png", full_page=True) if page.url.startswith(("http://", "https://")) else None
            raise RuntimeError(
                "Timed out waiting for the page, selector, or browser download. "
                "Check the URL and CSS selectors; for DOM mode, make sure the final click starts a real browser download."
            ) from exc
        except PlaywrightError as exc:
            raise RuntimeError(f"Playwright failed: {exc}") from exc
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"::error::{exc}", file=sys.stderr)
        sys.exit(1)
