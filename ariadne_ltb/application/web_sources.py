from __future__ import annotations

from hashlib import sha256

from ariadne_ltb.application.dtos import CreateSourceInput
from ariadne_ltb.models import SourceDocument, SourceType, stable_id, utc_now
from ariadne_ltb.storage import AriadneStore


class WebSourceService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def find_duplicate(self, path_or_url: str) -> SourceDocument | None:
        incoming_ref = normalized_source_ref(path_or_url)
        for existing in self.store.list_source_documents():
            if normalized_source_ref(existing.path_or_url) == incoming_ref:
                return existing
        return None

    def create(self, payload: CreateSourceInput) -> SourceDocument:
        now = utc_now()
        content = payload.content.strip()
        summary = payload.summary.strip() or _summarize(payload.title, content)
        evidence = [item.strip() for item in payload.evidence_snippets if item.strip()]
        if not evidence and content:
            evidence = _evidence_from_content(content)
        source = SourceDocument(
            id=stable_id("source", payload.path_or_url, payload.title, sha256(content.encode("utf-8")).hexdigest()),
            source_type=_source_type(payload.source_type),
            title=payload.title.strip(),
            path_or_url=payload.path_or_url.strip(),
            content_hash=sha256((payload.path_or_url + "\n" + content).encode("utf-8")).hexdigest(),
            summary=summary,
            created_at=now,
            metadata={
                "entrypoint": "web_workbench",
                "content": content,
                "evidence_snippets": evidence,
                "source_role": payload.source_role,
                "analysis_status": "pending",
                "artifact_ids": [],
                "license_risk": "unknown",
                "snapshot": {
                    "content_hash": sha256((payload.path_or_url + "\n" + content).encode("utf-8")).hexdigest(),
                    "fetched_at": now,
                },
            },
        )
        self.store.save_source_document(source)
        return source


def normalized_source_ref(value: str) -> str:
    stripped = value.strip()
    lowered = stripped.lower()
    if lowered.startswith("https://github.com/") or lowered.startswith("http://github.com/"):
        normalized = lowered.removeprefix("http://").removeprefix("https://")
        return f"https://{normalized.removesuffix('/').removesuffix('.git')}"
    return stripped.removesuffix("/")


def _source_type(value: str) -> SourceType:
    if value in {"github_readme", "github_repo"}:
        return SourceType.GITHUB_REPO
    if value in {"manual_note", "repo_note", "note"}:
        return SourceType.NOTE
    if value == "local_markdown":
        return SourceType.LOCAL_MARKDOWN
    if value == "local_folder":
        return SourceType.LOCAL_FOLDER
    if value == "target_codebase":
        return SourceType.TARGET_CODEBASE
    return SourceType(value)


def _summarize(title: str, content: str) -> str:
    if content:
        first = " ".join(content.split())[:500]
        return first or title
    return f"Workbench source: {title}"


def _evidence_from_content(content: str) -> list[str]:
    snippets: list[str] = []
    for paragraph in content.split("\n\n"):
        normalized = " ".join(paragraph.split())
        if len(normalized) >= 24:
            snippets.append(normalized[:240])
        if len(snippets) == 3:
            break
    return snippets
