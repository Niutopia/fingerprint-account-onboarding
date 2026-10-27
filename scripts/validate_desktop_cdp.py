#!/usr/bin/env python3
"""Validate that a running fingerprint-browser page is in desktop mode.

This connects to an existing CDP endpoint and never closes the browser.
Exit codes: 0 = desktop checks pass; 2 = mobile/narrow page; 1 = connection/runtime error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

MOBILE_UA = re.compile(r"Mobile|Android|iPhone|iPad|iPod|Windows Phone", re.IGNORECASE)


def cdp_url(value: str) -> str:
    value = value.strip()
    if re.fullmatch(r"\d+", value):
        return f"http://127.0.0.1:{value}"
    if value.startswith("ws://") or value.startswith("wss://") or value.startswith("http://") or value.startswith("https://"):
        return value
    raise ValueError("CDP endpoint must be a websocket/http URL or a numeric port")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ws", required=True, help="Existing CDP websocket/HTTP endpoint or numeric port")
    parser.add_argument("--url-contains", default="", help="Select a page whose URL contains this text")
    parser.add_argument("--min-width", type=int, default=900)
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"Playwright unavailable: {exc}"}), file=sys.stderr)
        return 1

    try:
        endpoint = cdp_url(args.ws)
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(endpoint)
            try:
                pages = [page for context in browser.contexts for page in context.pages]
                if not pages:
                    raise RuntimeError("CDP endpoint has no open pages")
                if args.url_contains:
                    pages = [page for page in pages if args.url_contains in page.url]
                    if not pages:
                        raise RuntimeError(f"no page URL contains {args.url_contains!r}")
                page = pages[-1]
                metrics = page.evaluate(
                    """() => ({
                      url: location.href,
                      title: document.title,
                      userAgent: navigator.userAgent,
                      platform: navigator.platform,
                      maxTouchPoints: navigator.maxTouchPoints || 0,
                      innerWidth: innerWidth,
                      innerHeight: innerHeight,
                      devicePixelRatio: devicePixelRatio,
                      screenWidth: screen.width,
                      screenHeight: screen.height
                    })"""
                )
                mobile_ua = bool(MOBILE_UA.search(metrics["userAgent"]))
                narrow = metrics["innerWidth"] < args.min_width
                ok = not mobile_ua and not narrow
                result = {
                    "ok": ok,
                    "mobile_ua": mobile_ua,
                    "narrow_viewport": narrow,
                    "min_width": args.min_width,
                    "metrics": metrics,
                }
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0 if ok else 2
            finally:
                browser.close()
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
