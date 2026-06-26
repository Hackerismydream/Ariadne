#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ariadne_ltb.product_closure import REAL_CLOSED, evaluate_closure_packet  # noqa: E402


REQUIRED_KEYS = {
    "schema_version",
    "status",
    "mode",
    "target_path",
    "workbench_url",
    "execution_evidence_text",
    "recorded_at",
}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_dogfood_result_packet.py <closure-result.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"missing dogfood closure packet: {path}", file=sys.stderr)
        return 1
    packet = json.loads(path.read_text(encoding="utf-8"))
    missing = sorted(REQUIRED_KEYS - set(packet))
    if missing:
        print(f"dogfood closure packet missing keys: {', '.join(missing)}", file=sys.stderr)
        return 1
    closure = evaluate_closure_packet(packet, packet_path=path, validate_target_path=True)
    if closure["status"] != REAL_CLOSED:
        print(
            f"dogfood closure rejected: {closure['status']} ({closure['mode']}): {closure['reason']}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
