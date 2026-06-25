from __future__ import annotations

import subprocess
from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
from typing import Protocol

from ariadne_ltb.application.repository_scanner import infer_test_commands, scan_repository
from ariadne_ltb.application.source_repository import (
    GitRepositoryFetcher,
    RepositoryFetcher,
    fetch_record_from_result,
)
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
    def __init__(
        self,
        store: AriadneStore,
        fetcher: SourceFetcher | None = None,
        repository_fetcher: RepositoryFetcher | None = None,
    ) -> None:
        self.store = store
        self.fetcher = fetcher or RequestsSourceFetcher()
        self.repository_fetcher = repository_fetcher or GitRepositoryFetcher()

    def analyze_source(self, source_id: str) -> SourceAnalysisResult:
        source = self.store.load_source_document(source_id)
        try:
            if source.source_type is SourceType.GITHUB_REPO and source.path_or_url.startswith("https://github.com/"):
                return self._analyze_github_repository(source)
            if source.source_type in {SourceType.GITHUB_REPO, SourceType.LOCAL_FOLDER} and (
                source.metadata.get("source_role") == "reference_project"
                or source.source_type is SourceType.GITHUB_REPO
            ):
                return self._analyze_repository_path(source, Path(source.path_or_url).expanduser())
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
        raw_content = self._source_content(source)
        content, quality = _extract_text_and_quality(raw_content, fallback=source.summary or source.title)
        summary = " ".join(content.split())[:800] or source.summary or source.title
        evidence_items = [
            self._save_evidence(
                source,
                artifact_id=None,
                locator=f"{source.path_or_url}#claim-{index}",
                quote_or_summary=claim["quote"],
                claim=claim["claim"],
                confidence=claim["confidence"],
            )
            for index, claim in enumerate(_text_claims(summary, source.path_or_url), start=1)
        ]
        artifact = self._save_artifact(
            source,
            "knowledge_card",
            {
                "title": source.title,
                "summary": summary,
                "source_role": source.metadata.get("source_role", "background_knowledge"),
                "key_claims": [item.claim for item in evidence_items],
                "risks": quality["limitations"],
                "applicability": "Use as project guidance when generating issues.",
                "quality_status": quality["status"],
                "quality_limitations": quality["limitations"],
                "extraction_method": quality["method"],
            },
            [item.id for item in evidence_items],
        )
        for evidence in evidence_items:
            self._link_evidence_to_artifact(evidence, artifact.id)
        status = "blocked" if quality["status"] == "blocked" else "analyzed"
        if status == "blocked":
            self._update_source_metadata(
                source,
                {
                    "analysis_status": "blocked",
                    "analysis_error": "low_quality_extraction",
                    "artifact_ids": [artifact.id],
                    "quality_status": quality["status"],
                    "quality_limitations": quality["limitations"],
                    "claim_count": len(evidence_items),
                },
            )
        else:
            self._mark_analyzed(
                source,
                [artifact.id],
                "unknown",
                {
                    "quality_status": quality["status"],
                    "quality_limitations": quality["limitations"],
                    "claim_count": len(evidence_items),
                },
            )
        return SourceAnalysisResult(source.id, status, [artifact.id], [item.id for item in evidence_items])

    def _analyze_github_repository(self, source: SourceDocument) -> SourceAnalysisResult:
        cache_root = self.store.root / ".ariadne" / "sources" / "git"
        fetch_result = self.repository_fetcher.fetch(source.path_or_url, cache_root)
        self.store.save_source_fetch_record(fetch_record_from_result(source.id, fetch_result))
        if fetch_result.status != "cached" or not fetch_result.cache_path:
            error = fetch_result.error or "repository_fetch_failed"
            self._update_source_metadata(
                source,
                {
                    "analysis_status": "blocked",
                    "analysis_error": error,
                    "snapshot": {
                        "fetched_at": utc_now(),
                        "source_url": fetch_result.source_url,
                    },
                },
            )
            return SourceAnalysisResult(source.id, "blocked", [], [], error)
        return self._analyze_repository_path(
            source,
            Path(fetch_result.cache_path),
            remote_url=fetch_result.source_url,
            commit_sha=fetch_result.commit_sha,
        )

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

    def _analyze_repository_path(
        self,
        source: SourceDocument,
        repo_path: Path,
        *,
        remote_url: str | None = None,
        commit_sha: str | None = None,
    ) -> SourceAnalysisResult:
        scan = scan_repository(repo_path)
        license_text, license_path = _read_license(repo_path)
        license_name, license_risk = _classify_license(license_text)
        resolved_commit = commit_sha or _git_commit(repo_path)
        evidence_items = self._repo_evidence(source, repo_path, scan)
        payload = {
            "repo_summary": scan.summary,
            "identity": {
                "name": repo_path.name if repo_path.exists() else source.title,
                "remote_url": remote_url or source.path_or_url,
                "commit_sha": resolved_commit,
                "primary_language": _primary_language(scan.manifests),
                "package_manager": _package_manager(scan.manifests),
                "frameworks": [],
            },
            "license": {
                "detected": license_name,
                "confidence": "high" if license_name != "unknown" else "low",
                "license_file_path": license_path,
            },
            "license_risk": license_risk,
            "manifests": scan.manifests,
            "entrypoints": scan.entrypoints,
            "repo_map": {
                "top_level": scan.top_level,
                "selected_files": scan.selected_files,
                "core_modules": [item for item in scan.top_level if item not in {"tests", "docs", ".git"}],
                "test_modules": sorted({Path(path).parts[0] for path in scan.test_paths if Path(path).parts}),
            },
            "tests": {
                "paths": scan.test_paths,
                "commands": infer_test_commands(scan.manifests, scan.test_paths),
            },
            "behavior_patterns": _behavior_patterns(scan.summary, scan.entrypoints, scan.test_paths),
            "architecture_insights": scan.architecture_insights,
            "test_strategy": scan.test_strategy,
            "safety_model": scan.safety_model,
            "limitations": scan.limitations,
            "reuse_notes": ["Reuse architecture ideas and task decomposition, not source code."],
            "avoid_notes": ["Do not copy implementation files directly from the reference project."],
            "scan_warnings": scan.warnings,
        }
        artifact = self._save_artifact(source, "repository_understanding", payload, [item.id for item in evidence_items])
        for evidence in evidence_items:
            self._link_evidence_to_artifact(evidence, artifact.id)
        self._mark_analyzed(
            source,
            [artifact.id],
            license_risk,
            {
                "commit_sha": resolved_commit,
                "source_url": remote_url or source.path_or_url,
                "scan_warnings": scan.warnings,
                "quality_status": "usable" if not scan.limitations else "partial",
                "quality_limitations": scan.limitations,
                "claim_count": len(evidence_items),
            },
        )
        return SourceAnalysisResult(source.id, "analyzed", [artifact.id], [item.id for item in evidence_items])

    def _analyze_target_codebase(self, source: SourceDocument) -> SourceAnalysisResult:
        repo_path = Path(source.path_or_url).expanduser()
        scan = scan_repository(repo_path)
        evidence = self._save_evidence(
            source,
            artifact_id=None,
            locator=str(repo_path),
            quote_or_summary=f"Target codebase has {len(scan.top_level)} top-level entries and {len(scan.test_paths)} test files.",
            claim="target codebase snapshot informs issue factory",
        )
        payload = {
                "target_path": str(repo_path),
                "top_level": scan.top_level,
                "test_paths": scan.test_paths,
                "test_commands": infer_test_commands(scan.manifests, scan.test_paths),
                "selected_files": scan.selected_files,
                "architecture_insights": scan.architecture_insights,
                "test_strategy": scan.test_strategy,
                "safety_model": scan.safety_model,
                "limitations": scan.limitations,
                "commit_sha": _git_commit(repo_path),
            }
        artifact = self._save_artifact(
            source,
            "codebase_snapshot",
            payload,
            [evidence.id],
            identity_seed=sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest(),
        )
        self._link_evidence_to_artifact(evidence, artifact.id)
        self._mark_analyzed(
            source,
            [artifact.id],
            "unknown",
            {
                "quality_status": "usable" if not scan.limitations else "partial",
                "quality_limitations": scan.limitations,
                "claim_count": 1,
            },
        )
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
        confidence: float = 0.8,
    ) -> SourceEvidence:
        evidence = SourceEvidence(
            id=stable_id("source_evidence", source.id, locator, quote_or_summary, claim),
            source_document_id=source.id,
            artifact_id=artifact_id,
            locator=locator,
            quote_or_summary=quote_or_summary,
            claim=claim,
            confidence=confidence,
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
        identity_seed: str | None = None,
    ) -> SourceArtifact:
        artifact = SourceArtifact(
            id=stable_id("source_artifact", source.id, artifact_type, source.content_hash, identity_seed or ""),
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
        top_level_quality = {
            key: value
            for key, value in (snapshot_extra or {}).items()
            if key in {"quality_status", "quality_limitations", "claim_count"}
        }
        self._update_source_metadata(
            source,
            {
                "analysis_status": "analyzed",
                "artifact_ids": artifact_ids,
                "license_risk": license_risk,
                "snapshot": snapshot,
            } | top_level_quality,
        )

    def _update_source_metadata(self, source: SourceDocument, metadata: dict[str, object]) -> None:
        self.store.save_source_document(
            source.model_copy(deep=True, update={"metadata": source.metadata | metadata})
        )

    def _repo_evidence(self, source: SourceDocument, repo_path: Path, scan) -> list[SourceEvidence]:  # noqa: ANN001
        locator = "README.md" if (repo_path / "README.md").exists() else str(repo_path)
        evidence: list[SourceEvidence] = [
            self._save_evidence(
                source,
                artifact_id=None,
                locator=locator,
                quote_or_summary=scan.summary[:240],
                claim="repository README explains reusable project intent",
                confidence=0.78,
            )
        ]
        if scan.architecture_insights:
            evidence.append(
                self._save_evidence(
                    source,
                    artifact_id=None,
                    locator="repository architecture scan",
                    quote_or_summary=" ".join(scan.architecture_insights[:2])[:240],
                    claim="repository architecture suggests issue decomposition boundaries",
                    confidence=0.74,
                )
            )
        if scan.test_strategy:
            evidence.append(
                self._save_evidence(
                    source,
                    artifact_id=None,
                    locator="repository test scan",
                    quote_or_summary=" ".join(scan.test_strategy[:2])[:240],
                    claim="repository test strategy informs acceptance criteria",
                    confidence=0.72,
                )
            )
        if scan.safety_model:
            evidence.append(
                self._save_evidence(
                    source,
                    artifact_id=None,
                    locator="repository safety scan",
                    quote_or_summary=" ".join(scan.safety_model[:2])[:240],
                    claim="repository safety signals inform implementation constraints",
                    confidence=0.68,
                )
            )
        return evidence


def _read_first_existing(root: Path, names: list[str]) -> str:
    for name in names:
        path = root / name
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def _extract_text_and_quality(raw: str, *, fallback: str) -> tuple[str, dict[str, object]]:
    stripped = raw.strip()
    if not stripped:
        return fallback, {"status": "partial", "method": "fallback_summary", "limitations": ["source_content_empty"]}
    looks_html = _looks_like_html(stripped)
    if looks_html:
        parser = _VisibleTextParser()
        parser.feed(stripped)
        text = " ".join(parser.parts)
        limitations = []
        if len(text) < 120:
            limitations.append("html_extraction_too_short")
        if text and len(text) < len(stripped) * 0.05:
            limitations.append("html_text_density_low")
        status = "blocked" if not text or "html_extraction_too_short" in limitations else "partial" if limitations else "usable"
        return text or fallback, {"status": status, "method": "html_text_extraction", "limitations": limitations}
    text = " ".join(stripped.split())
    limitations = ["text_extraction_too_short"] if len(text) < 60 else []
    return text or fallback, {
        "status": "partial" if limitations else "usable",
        "method": "plain_text",
        "limitations": limitations,
    }


def _looks_like_html(text: str) -> bool:
    lowered = text[:500].lower()
    return "<!doctype html" in lowered or "<html" in lowered or ("<body" in lowered and "</" in lowered)


def _text_claims(summary: str, locator: str) -> list[dict[str, object]]:
    sentences = [
        item.strip(" -\t")
        for chunk in summary.replace("\n", ". ").split(".")
        for item in [chunk.strip()]
        if len(item.strip()) >= 30
    ]
    if not sentences:
        sentences = [summary[:240] or locator]
    claims: list[dict[str, object]] = []
    for sentence in sentences[:5]:
        claims.append(
            {
                "quote": sentence[:240],
                "claim": _claim_from_sentence(sentence),
                "confidence": 0.72 if len(sentence) < 80 else 0.78,
            }
        )
    return claims


def _claim_from_sentence(sentence: str) -> str:
    lowered = sentence.lower()
    if "test" in lowered:
        return "source describes verification or test expectations"
    if "agent" in lowered or "loop" in lowered or "tool" in lowered:
        return "source describes agent behavior relevant to issue generation"
    if "safety" in lowered or "permission" in lowered or "sandbox" in lowered:
        return "source describes safety constraints for implementation"
    return "source provides project guidance for issue generation"


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


def _primary_language(manifests: list[str]) -> str:
    if "pyproject.toml" in manifests or "requirements.txt" in manifests:
        return "python"
    if "package.json" in manifests:
        return "javascript"
    if "go.mod" in manifests:
        return "go"
    if "Cargo.toml" in manifests:
        return "rust"
    return "unknown"


def _package_manager(manifests: list[str]) -> str:
    if "uv.lock" in manifests:
        return "uv"
    if "pyproject.toml" in manifests:
        return "python"
    if "package.json" in manifests:
        return "npm"
    if "go.mod" in manifests:
        return "go"
    if "Cargo.toml" in manifests:
        return "cargo"
    return "unknown"


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
