#!/usr/bin/env python3
"""Check projected usage per exit IP against a configured capacity limit.

Input JSON (file or stdin):
{
  "limit": 4,
  "usage": {"203.0.113.10": 2},
  "additions": {"203.0.113.10": 1}
}

Exit codes: 0 = all assignments fit; 2 = at least one exceeds capacity; 1 = input error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def non_negative_int(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    number = int(value)
    if number < 0:
        raise ValueError(f"{label} must be non-negative")
    return number


def load_payload(path: str) -> dict:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="-", help="JSON file path, or - for stdin")
    parser.add_argument("--limit", type=int, help="Override the limit from the input JSON")
    args = parser.parse_args()

    try:
        payload = load_payload(args.input)
        limit = args.limit if args.limit is not None else payload.get("limit")
        if limit is None:
            raise ValueError("limit is required in JSON or via --limit")
        limit = non_negative_int(limit, "limit")
        usage = payload.get("usage") or {}
        additions = payload.get("additions") or {}
        if not isinstance(usage, dict) or not isinstance(additions, dict):
            raise ValueError("usage and additions must be objects mapping IP to count")

        ips = sorted(set(usage) | set(additions))
        rows = []
        violations = []
        for ip in ips:
            current = non_negative_int(usage.get(ip, 0), f"usage[{ip!r}]")
            added = non_negative_int(additions.get(ip, 0), f"additions[{ip!r}]")
            projected = current + added
            ok = projected <= limit
            row = {
                "ip": ip,
                "current": current,
                "added": added,
                "projected": projected,
                "limit": limit,
                "ok": ok,
            }
            rows.append(row)
            if not ok:
                violations.append(row)

        print(json.dumps({"ok": not violations, "rows": rows, "violations": violations}, ensure_ascii=False, indent=2))
        return 0 if not violations else 2
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
