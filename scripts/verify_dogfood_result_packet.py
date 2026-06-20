#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


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
    if packet["status"] != "REAL_CLOSED":
        print(f"dogfood status is not REAL_CLOSED: {packet['status']}", file=sys.stderr)
        return 1
    if packet["mode"] != "real":
        print(f"dogfood mode is not real: {packet['mode']}", file=sys.stderr)
        return 1
    evidence = str(packet["execution_evidence_text"]).lower()
    forbidden = ["fake-codex", "dry-run", "dry_run", "门禁关闭", "已阻塞"]
    found = [item for item in forbidden if item in evidence]
    if found:
        print(f"dogfood evidence contains non-closure markers: {', '.join(found)}", file=sys.stderr)
        return 1
    target_path = Path(str(packet["target_path"])).expanduser()
    if not target_path.exists():
        print(f"target project path does not exist: {target_path}", file=sys.stderr)
        return 1
    if not (target_path / ".git").exists():
        print(f"target project is not a git repo: {target_path}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
