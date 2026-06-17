from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ariadne_ltb.models import FailureReason

SENSITIVE_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".npmrc",
    ".pypirc",
    "id_rsa",
    "id_ed25519",
}
SENSITIVE_PATH_PARTS = {"secrets", ".secrets", ".ssh"}
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")),
    ("openai_key", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ("deepseek_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("generic_secret_assignment", re.compile(r"(?i)(api[_-]?key|secret|token|password)\\s*=\\s*['\\\"]?[^\\s'\\\"]{8,}")),
)
SKIP_DIRS = {".git", ".ariadne", ".venv", "node_modules", "__pycache__", ".pytest_cache"}
MAX_FILE_BYTES = 128_000


@dataclass(frozen=True)
class SecretFinding:
    kind: str
    path: str
    line: int | None = None
    redacted: str = "[REDACTED]"


@dataclass(frozen=True)
class SecretScanResult:
    scanned_root: str
    findings: list[SecretFinding]

    @property
    def ok(self) -> bool:
        return not self.findings

    def safe_summary(self) -> dict:
        return {
            "scanned_root": self.scanned_root,
            "ok": self.ok,
            "finding_count": len(self.findings),
            "findings": [finding.__dict__ for finding in self.findings],
        }


@dataclass(frozen=True)
class SecretSafetyValidation:
    valid: bool
    reason: str = ""
    failure_reason: FailureReason | None = None
    findings: list[SecretFinding] | None = None


def scan_for_secrets(root: str | Path) -> SecretScanResult:
    root_path = Path(root).resolve()
    findings: list[SecretFinding] = []
    if not root_path.exists():
        return SecretScanResult(str(root_path), findings)
    for path in _iter_candidate_files(root_path):
        rel = str(path.relative_to(root_path))
        if _is_sensitive_path(path, root_path):
            findings.append(SecretFinding(kind="sensitive_path", path=rel))
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for kind, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(SecretFinding(kind=kind, path=rel, line=line_number))
                    break
    return SecretScanResult(str(root_path), findings)


def validate_secret_safety(root: str | Path, command: str = "", allowed_paths: list[str] | None = None) -> SecretSafetyValidation:
    command_hit = _command_references_sensitive_path(command)
    if command_hit:
        return SecretSafetyValidation(
            False,
            f"command references sensitive path `{command_hit}`; value redacted",
            FailureReason.SCOPE_VIOLATION,
            [],
        )
    allowed_hit = _allowed_paths_include_sensitive_path(allowed_paths or [])
    if allowed_hit:
        return SecretSafetyValidation(
            False,
            f"allowed paths include sensitive path `{allowed_hit}`; value redacted",
            FailureReason.SCOPE_VIOLATION,
            [],
        )
    scan = scan_for_secrets(root)
    if scan.findings:
        paths = ", ".join(sorted({finding.path for finding in scan.findings})[:5])
        return SecretSafetyValidation(
            False,
            f"secret safety blocked: sensitive material detected at path(s): {paths}; values redacted",
            FailureReason.SCOPE_VIOLATION,
            scan.findings,
        )
    return SecretSafetyValidation(True)


def secret_status_lines(root: str | Path) -> list[str]:
    scan = scan_for_secrets(root)
    lines = [
        f"secret scan root: {scan.scanned_root}",
        f"secret scan: {'ok' if scan.ok else 'blocked'}",
        f"secret findings: {len(scan.findings)}",
    ]
    for finding in scan.findings[:10]:
        location = f":{finding.line}" if finding.line else ""
        lines.append(f"- {finding.kind}: `{finding.path}{location}` value=[REDACTED]")
    return lines


def _iter_candidate_files(root: Path):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def _is_sensitive_path(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    return path.name in SENSITIVE_FILE_NAMES or any(part in SENSITIVE_PATH_PARTS for part in rel_parts)


def _command_references_sensitive_path(command: str) -> str | None:
    lowered = command.lower()
    candidates = [*SENSITIVE_FILE_NAMES, *SENSITIVE_PATH_PARTS]
    return next((candidate for candidate in candidates if candidate and candidate.lower() in lowered), None)


def _allowed_paths_include_sensitive_path(allowed_paths: list[str]) -> str | None:
    for path in allowed_paths:
        lowered = path.lower()
        if Path(path).name in SENSITIVE_FILE_NAMES:
            return path
        if any(part in lowered.split("/") for part in SENSITIVE_PATH_PARTS):
            return path
    return None
