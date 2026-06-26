from __future__ import annotations

import subprocess
from hashlib import sha256
from pathlib import Path

from ariadne_ltb.application.source_analysis import SourceAnalysisService
from ariadne_ltb.models import SourceDocument, SourceType, stable_id
from ariadne_ltb.storage import AriadneStore


class DisabledRepositoryFetcher:
    def fetch(self, url: str, cache_root: Path, timeout_seconds: int = 30):
        from ariadne_ltb.application.source_repository import SourceFetchResult

        return SourceFetchResult(
            status="blocked",
            source_url=url,
            cache_path=None,
            commit_sha=None,
            default_branch=None,
            fetched_ref=None,
            file_count=0,
            warnings=[],
            error="repository_fetcher_disabled_for_test",
        )


class LocalMirrorFetcher:
    def __init__(self, mirror: Path) -> None:
        self.mirror = mirror

    def fetch(self, url: str, cache_root: Path, timeout_seconds: int = 30):
        from ariadne_ltb.application.source_repository import SourceFetchResult

        checkout = cache_root / "github.com" / "acme" / "mini-agent" / "checkout"
        checkout.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth=1", str(self.mirror), str(checkout)],
            check=True,
            capture_output=True,
        )
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=checkout,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
        return SourceFetchResult(
            status="cached",
            source_url=url,
            cache_path=str(checkout),
            commit_sha=commit,
            default_branch="main",
            fetched_ref="main",
            file_count=0,
            warnings=[],
        )


def test_github_url_does_not_become_analyzed_when_fetch_is_blocked(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    source = SourceDocument(
        id=stable_id("source", "https://github.com/acme/missing", "missing"),
        source_type=SourceType.GITHUB_REPO,
        title="acme/missing",
        path_or_url="https://github.com/acme/missing",
        content_hash=sha256(b"missing").hexdigest(),
        summary="Reference repository.",
        metadata={"source_role": "reference_project"},
    )
    store.save_source_document(source)

    result = SourceAnalysisService(
        store,
        repository_fetcher=DisabledRepositoryFetcher(),
    ).analyze_source(source.id)
    reloaded = store.load_source_document(source.id)
    fetch_records = store.list_source_fetch_records(source.id)

    assert result.status == "blocked"
    assert reloaded.metadata["analysis_status"] == "blocked"
    assert reloaded.metadata["analysis_error"] == "repository_fetcher_disabled_for_test"
    assert fetch_records
    assert fetch_records[-1].status == "blocked"
    assert store.list_source_artifacts(source.id) == []


def test_github_url_fetch_creates_repository_understanding_artifact(tmp_path: Path) -> None:
    source_repo = tmp_path / "source-repo"
    source_repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=source_repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=source_repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=source_repo, check=True)
    (source_repo / "README.md").write_text(
        "# Mini Agent\n\nAgent loop with actions, observations, tests, and review.\n",
        encoding="utf-8",
    )
    (source_repo / "pyproject.toml").write_text("[project]\nname='mini-agent'\n", encoding="utf-8")
    (source_repo / "mini_agent.py").write_text("def main():\n    return 'ok'\n", encoding="utf-8")
    (source_repo / "tests").mkdir()
    (source_repo / "tests" / "test_agent.py").write_text(
        "def test_agent():\n    assert True\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=source_repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=source_repo, check=True, capture_output=True)

    store = AriadneStore(tmp_path / "store")
    source = SourceDocument(
        id=stable_id("source", "https://github.com/acme/mini-agent", "mini-agent"),
        source_type=SourceType.GITHUB_REPO,
        title="acme/mini-agent",
        path_or_url="https://github.com/acme/mini-agent",
        content_hash=sha256(b"mini-agent").hexdigest(),
        summary="Reference repository.",
        metadata={"source_role": "reference_project"},
    )
    store.save_source_document(source)

    result = SourceAnalysisService(store, repository_fetcher=LocalMirrorFetcher(source_repo)).analyze_source(source.id)
    reloaded = store.load_source_document(source.id)
    artifacts = store.list_source_artifacts(source.id)
    payload = store.load_source_artifact_payload(artifacts[0].id)

    assert result.status == "analyzed"
    assert reloaded.metadata["analysis_status"] == "analyzed"
    assert reloaded.metadata["snapshot"]["commit_sha"]
    assert artifacts[0].artifact_type == "repository_understanding"
    assert payload["identity"]["remote_url"] == "https://github.com/acme/mini-agent"
    assert payload["repo_structure"]["test_files"] == ["tests/test_agent.py"]
    assert payload["reusable_patterns"]
    assert payload["risks"]
    assert payload["tests"]["paths"] == ["tests/test_agent.py"]
    assert "pyproject.toml" in payload["manifests"]
