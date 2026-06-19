from __future__ import annotations

import subprocess
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from ariadne_ltb.models import SourceArtifact, SourceDocument, SourceEvidence, SourceType, stable_id, utc_now
from ariadne_ltb.storage import AriadneStore


@dataclass(frozen=True)
class SourceAnalysisResult:
    source_id: str
    status: str
    artifact_ids: list[str]
    evidence_ids: list[str]
    error: str | None = None


class SourceFetcher(Protocol):
    def fetch(self, url: str) -> str: ...


class RequestsSourceFetcher:
    def fetch(self, url: str) -> str:
        from urllib.request import urlopen

        with urlopen(url, timeout=10) as response:  # noqa: S310 - user-provided local product source.
            return response.read().decode("utf-8", errors="replace")


class SourceAnalysisService:
    def __init__(self, store: AriadneStore, fetcher: SourceFetcher | None = None) -> None:
        self.store = store
        self.fetcher = fetcher or RequestsSourceFetcher()

    def analyze_source(self, source_id: str) -> SourceAnalysisResult:
        source = self.store.load_source_document(source_id)
        try:
            if source.source_type in {SourceType.GITHUB_REPO, SourceType.LOCAL_FOLDER} and (
                source.metadata.get("source_role") == "reference_project"
                or source.source_type is SourceType.GITHUB_REPO
            ):
                return self._analyze_reference_project(source)
            if source.source_type is SourceType.TARGET_CODEBASE:
                return self._analyze_target_codebase(source)
            return self._analyze_text_source(source)
        except Exception as exc:  # pragma: no cover - defensive product status path
            self._update_source_metadata(
                source,
                {"analysis_status": "blocked", "analysis_error": f"{type(exc).__name__}:{exc}"},
            )
            return SourceAnalysisResult(source.id, "blocked", [], [], str(exc))

    def _analyze_text_source(self, source: SourceDocument) -> SourceAnalysisResult:
        content = self._source_content(source)
        summary = " ".join(content.split())[:800] or source.summary or source.title
        evidence = self._save_evidence(
            source,
            artifact_id=None,
            locator=source.path_or_url,
            quote_or_summary=summary[:240],
            claim="text source provides project guidance",
        )
        artifact = self._save_artifact(
            source,
            "knowledge_card",
            {
                "title": source.title,
                "summary": summary,
                "source_role": source.metadata.get("source_role", "background_knowledge"),
                "key_claims": [evidence.claim],
                "risks": [],
                "applicability": "Use as project guidance when generating issues.",
            },
            [evidence.id],
        )
        self._link_evidence_to_artifact(evidence, artifact.id)
        self._mark_analyzed(source, [artifact.id], "unknown")
        return SourceAnalysisResult(source.id, "analyzed", [artifact.id], [evidence.id])

    def _analyze_reference_project(self, source: SourceDocument) -> SourceAnalysisResult:
        repo_path = Path(source.path_or_url).expanduser()
        readme_text = _read_first_existing(repo_path, ["README.md", "readme.md", "README.rst"])
        license_text, license_path = _read_license(repo_path)
        license_name, license_risk = _classify_license(license_text)
        top_level = _top_level(repo_path)
        test_paths = _test_paths(repo_path)
        entrypoints = _entrypoints(repo_path)
        commit_sha = _git_commit(repo_path)
        summary = _summary_from_readme(readme_text, source.title)
        patterns = _behavior_patterns(readme_text, entrypoints, test_paths)
        evidence = self._save_evidence(
            source,
            artifact_id=None,
            locator="README.md",
            quote_or_summary=summary[:240],
            claim="reference project exposes transferable coding-agent structure",
        )
        payload = {
            "repo_summary": summary,
            "identity": {
                "name": repo_path.name if repo_path.exists() else source.title,
                "commit_sha": commit_sha,
                "primary_language": "python" if (repo_path / "pyproject.toml").exists() else "unknown",
                "package_manager": "python" if (repo_path / "pyproject.toml").exists() else "unknown",
                "frameworks": [],
            },
            "license": {
                "detected": license_name,
                "confidence": "high" if license_name != "unknown" else "low",
                "license_file_path": license_path,
            },
            "license_risk": license_risk,
            "entrypoints": entrypoints,
            "repo_map": {
                "top_level": top_level,
                "core_modules": [item for item in top_level if item not in {"tests", "docs", ".git"}],
                "test_modules": sorted({Path(path).parts[0] for path in test_paths if Path(path).parts}),
            },
            "tests": {
                "paths": test_paths,
                "commands": ["python3.11 -m pytest"] if test_paths else [],
            },
            "behavior_patterns": patterns,
            "reuse_notes": ["Reuse architecture ideas and task decomposition, not source code."],
            "avoid_notes": ["Do not copy implementation files directly from the reference project."],
        }
        artifact = self._save_artifact(source, "reference_project_profile", payload, [evidence.id])
        self._link_evidence_to_artifact(evidence, artifact.id)
        self._mark_analyzed(source, [artifact.id], license_risk, {"commit_sha": commit_sha})
        return SourceAnalysisResult(source.id, "analyzed", [artifact.id], [evidence.id])

    def _analyze_target_codebase(self, source: SourceDocument) -> SourceAnalysisResult:
        repo_path = Path(source.path_or_url).expanduser()
        top_level = _top_level(repo_path)
        test_paths = _test_paths(repo_path)
        evidence = self._save_evidence(
            source,
            artifact_id=None,
            locator=str(repo_path),
            quote_or_summary=f"Target codebase has {len(top_level)} top-level entries.",
            claim="target codebase snapshot informs issue factory",
        )
        artifact = self._save_artifact(
            source,
            "codebase_snapshot",
            {
                "target_path": str(repo_path),
                "top_level": top_level,
                "test_paths": test_paths,
                "test_commands": ["python3.11 -m pytest"] if test_paths else [],
                "commit_sha": _git_commit(repo_path),
            },
            [evidence.id],
        )
        self._link_evidence_to_artifact(evidence, artifact.id)
        self._mark_analyzed(source, [artifact.id], "unknown")
        return SourceAnalysisResult(source.id, "analyzed", [artifact.id], [evidence.id])

    def _source_content(self, source: SourceDocument) -> str:
        content = str(source.metadata.get("content") or "")
        if content:
            return content
        if source.path_or_url.startswith("http://") or source.path_or_url.startswith("https://"):
            return self.fetcher.fetch(source.path_or_url)
        path = Path(source.path_or_url.replace("file://", "")).expanduser()
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")
        return source.summary

    def _save_evidence(
        self,
        source: SourceDocument,
        *,
        artifact_id: str | None,
        locator: str,
        quote_or_summary: str,
        claim: str,
    ) -> SourceEvidence:
        evidence = SourceEvidence(
            id=stable_id("source_evidence", source.id, locator, quote_or_summary, claim),
            source_document_id=source.id,
            artifact_id=artifact_id,
            locator=locator,
            quote_or_summary=quote_or_summary,
            claim=claim,
            confidence=0.8,
            content_hash=sha256(f"{locator}\n{quote_or_summary}\n{claim}".encode("utf-8")).hexdigest(),
        )
        self.store.save_source_evidence(evidence)
        return evidence

    def _save_artifact(
        self,
        source: SourceDocument,
        artifact_type: str,
        payload: dict[str, object],
        evidence_ids: list[str],
    ) -> SourceArtifact:
        artifact = SourceArtifact(
            id=stable_id("source_artifact", source.id, artifact_type, source.content_hash),
            source_document_id=source.id,
            artifact_type=artifact_type,  # type: ignore[arg-type]
            payload_hash="",
            payload_path="",
            evidence_ids=evidence_ids,
        )
        return self.store.save_source_artifact(artifact, payload)

    def _link_evidence_to_artifact(self, evidence: SourceEvidence, artifact_id: str) -> None:
        linked = evidence.model_copy(update={"artifact_id": artifact_id})
        self.store.save_source_evidence(linked)

    def _mark_analyzed(
        self,
        source: SourceDocument,
        artifact_ids: list[str],
        license_risk: str,
        snapshot_extra: dict[str, object] | None = None,
    ) -> None:
        snapshot = {
            "fetched_at": utc_now(),
            "content_hash": source.content_hash,
        } | (snapshot_extra or {})
        self._update_source_metadata(
            source,
            {
                "analysis_status": "analyzed",
                "artifact_ids": artifact_ids,
                "license_risk": license_risk,
                "snapshot": snapshot,
            },
        )

    def _update_source_metadata(self, source: SourceDocument, metadata: dict[str, object]) -> None:
        self.store.save_source_document(
            source.model_copy(deep=True, update={"metadata": source.metadata | metadata})
        )


def _read_first_existing(root: Path, names: list[str]) -> str:
    for name in names:
        path = root / name
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def _read_license(root: Path) -> tuple[str, str | None]:
    for name in ["LICENSE", "LICENSE.md", "COPYING"]:
        path = root / name
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8", errors="replace"), name
    return "", None


def _classify_license(text: str) -> tuple[str, str]:
    normalized = text.lower()
    if "agpl" in normalized or "gnu affero" in normalized:
        return "AGPL", "red"
    if "gpl" in normalized or "gnu general public" in normalized:
        return "GPL", "red"
    if "mit license" in normalized:
        return "MIT", "green"
    if "apache license" in normalized:
        return "Apache-2.0", "green"
    if "bsd" in normalized:
        return "BSD", "green"
    return "unknown", "yellow"


def _top_level(root: Path) -> list[str]:
    if not root.exists() or not root.is_dir():
        return []
    return sorted(path.name for path in root.iterdir() if not path.name.startswith("__pycache__"))


def _test_paths(root: Path) -> list[str]:
    if not root.exists() or not root.is_dir():
        return []
    return sorted(
        str(path.relative_to(root))
        for path in root.rglob("test_*.py")
        if ".git" not in path.parts
    )


def _entrypoints(root: Path) -> list[str]:
    pyproject = root / "pyproject.toml"
    entrypoints: list[str] = []
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if "=" in line and ":" in line and not line.strip().startswith("["):
                entrypoints.append(line.strip())
    for name in ["cli.py", "main.py"]:
        for path in root.rglob(name):
            if ".git" not in path.parts:
                entrypoints.append(str(path.relative_to(root)))
    return sorted(dict.fromkeys(entrypoints))


def _git_commit(root: Path) -> str | None:
    if not (root / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _summary_from_readme(readme_text: str, fallback: str) -> str:
    lines = [line.strip("# ").strip() for line in readme_text.splitlines() if line.strip()]
    return " ".join(lines[:3])[:800] or fallback


def _behavior_patterns(readme_text: str, entrypoints: list[str], test_paths: list[str]) -> list[str]:
    patterns: list[str] = []
    text = readme_text.lower()
    if "cli" in text or entrypoints:
        patterns.append("Expose a small CLI as the primary builder interface.")
    if "session" in text or "trace" in text:
        patterns.append("Persist session or trajectory data for review.")
    if "diff" in text or "review" in text:
        patterns.append("Show diffs and review checkpoints before trusting changes.")
    if test_paths:
        patterns.append("Keep an executable test path for every agent iteration.")
    return patterns or ["Extract a minimal project structure before generating implementation tasks."]
