#!/usr/bin/env python3
"""Generate one or more identities with MockAddress.com.

Examples:
  python generate_mockaddress.py --country jp --subdivision 北海道 --count 5
  python generate_mockaddress.py --url https://mockaddress.com/us-address/ --count 2

The script uses MockAddress' current result DOM (`#address-result [data-field]`)
and prints JSON to stdout. It does not save cookies or reuse a browser profile.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_COUNTRY_URL = "https://mockaddress.com/{country}-address/"
GENERATE_NAMES = ("生成地址", "Generate Address", "Generate address", "Generate")


def fail(message: str) -> int:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False), file=sys.stderr)
    return 1


def choose_option_by_text(page, subdivision: str) -> bool:
    result = page.evaluate(
        """(wanted) => {
          const norm = (s) => String(s || '').replace(/\\s+/g, ' ').trim().toLocaleLowerCase();
          const target = norm(wanted);
          const selects = [...document.querySelectorAll('select')].filter((el) => {
            const style = getComputedStyle(el);
            return style.display !== 'none' && style.visibility !== 'hidden' && !el.disabled;
          });
          for (const select of selects) {
            const options = [...select.options].filter((o) => o.value !== '');
            if (options.length < 2) continue;
            let match = options.find((o) => norm(o.value) === target || norm(o.textContent) === target);
            if (!match) match = options.find((o) => norm(o.textContent).includes(target));
            if (!match) continue;
            select.value = match.value;
            select.dispatchEvent(new Event('input', { bubbles: true }));
            select.dispatchEvent(new Event('change', { bubbles: true }));
            return {selectId: select.id || null, value: match.value, label: (match.textContent || '').trim()};
          }
          return null;
        }""",
        subdivision,
    )
    return bool(result)


def click_generate(page) -> None:
    for name in GENERATE_NAMES:
        button = page.get_by_role("button", name=name, exact=True)
        if button.count() and button.first.is_visible():
            button.first.click()
            return
    raise RuntimeError("MockAddress generate button not found")


def result_signature(page) -> str:
    return page.evaluate(
        """() => {
          const root = document.querySelector('#address-result');
          if (!root) return '';
          return [...root.querySelectorAll('[data-field]')]
            .map((el) => `${el.dataset.field}=${el.dataset.copy || ''}`)
            .join('\\n');
        }"""
    )


def parse_result(page) -> dict[str, str]:
    items = page.locator("#address-result [data-field]").evaluate_all(
        """els => els.map(el => ({
          field: el.dataset.field || '',
          value: el.dataset.copy || (el.innerText || '').trim().split('\\n').pop() || ''
        }))"""
    )
    out: dict[str, str] = {}
    for item in items:
        if item.get("field"):
            out[str(item["field"])] = str(item.get("value", "")).strip()
    return out


def identity_key(identity: dict[str, str]) -> tuple[str, ...]:
    return tuple(
        identity.get(field, "")
        for field in ("lastName", "firstName", "zip", "street", "city", "state", "phone")
    )


def wait_for_new_result(page, previous: str, timeout: float) -> str:
    deadline = time.monotonic() + timeout
    current = ""
    while time.monotonic() < deadline:
        page.wait_for_timeout(300)
        current = result_signature(page)
        if current and current != previous and page.locator("#address-result [data-field]").count() >= 5:
            return current
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    region = parser.add_mutually_exclusive_group(required=True)
    region.add_argument("--country", help="MockAddress country slug, e.g. jp, usa, uk, hk")
    region.add_argument("--url", help="Explicit MockAddress country-page URL")
    parser.add_argument("--subdivision", default="", help="Optional state/prefecture filter, matched against option text")
    parser.add_argument("--count", type=int, default=1, help="Number of fresh identities to generate (1-20)")
    parser.add_argument("--output", help="Optional JSON output path")
    parser.add_argument("--timeout", type=float, default=25.0, help="Seconds to wait for each result")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds to wait before each subsequent generation")
    parser.add_argument("--channel", default="chrome", help="Playwright Chromium channel (default: chrome)")
    parser.add_argument("--headed", action="store_true", help="Show the helper browser")
    args = parser.parse_args()

    if not 1 <= args.count <= 20:
        return fail("--count must be between 1 and 20")
    url = args.url or DEFAULT_COUNTRY_URL.format(country=re.sub(r"[^a-zA-Z0-9_-]", "", args.country))

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return fail(f"Playwright unavailable: {exc}")

    identities: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    try:
        with sync_playwright() as pw:
            launch = {"headless": not args.headed}
            if args.channel:
                launch["channel"] = args.channel
            try:
                browser = pw.chromium.launch(**launch)
            except Exception as exc:
                return fail(f"Could not launch helper browser: {exc}")
            try:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                page.wait_for_timeout(1500)
                if args.subdivision:
                    selected = choose_option_by_text(page, args.subdivision)
                    if not selected:
                        return fail(f"Subdivision not found in selectable options: {args.subdivision}")
                    page.wait_for_timeout(800)

                previous = result_signature(page)
                attempts = 0
                while len(identities) < args.count:
                    attempts += 1
                    if attempts > args.count * 4:
                        return fail("Could not obtain enough unique MockAddress identities")
                    if identities and args.interval > 0:
                        page.wait_for_timeout(int(args.interval * 1000))
                    if args.subdivision:
                        choose_option_by_text(page, args.subdivision)
                    click_generate(page)
                    current = wait_for_new_result(page, previous, args.timeout)
                    if not current:
                        # A second click after a short settle handles debounce on the generator.
                        page.wait_for_timeout(1500)
                        click_generate(page)
                        current = wait_for_new_result(page, previous, args.timeout)
                    if not current:
                        return fail(f"No new address result appeared on attempt {attempts}")
                    page.wait_for_timeout(350)
                    parsed = parse_result(page)
                    if not parsed:
                        return fail(f"Could not parse address result on attempt {attempts}")
                    key = identity_key(parsed)
                    previous = current
                    if key in seen:
                        continue
                    seen.add(key)
                    identities.append(parsed)

                payload = {
                    "ok": True,
                    "source": "https://mockaddress.com/",
                    "url": url,
                    "country": args.country or None,
                    "subdivision": args.subdivision or None,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "identities": identities,
                }
                text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
                if args.output:
                    path = Path(args.output)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(text, encoding="utf-8")
                print(text, end="")
                return 0
            finally:
                browser.close()
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
