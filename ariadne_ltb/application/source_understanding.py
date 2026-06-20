from __future__ import annotations

from ariadne_ltb.application.dtos import SourceEvidenceItemDTO, SourceInputEventDTO, SourceUnderstandingDTO
from ariadne_ltb.models import SourceArtifact, SourceDocument, SourceEvidence
from ariadne_ltb.storage import AriadneStore


KIND_LABELS = {
    "blog": "博客",
    "paper": "论文",
    "github_repo": "GitHub 仓库",
    "github_readme": "GitHub README",
    "note": "手动笔记",
    "manual_note": "手动笔记",
    "repo_note": "仓库笔记",
    "local_markdown": "本地 Markdown",
    "local_folder": "本地文件夹",
    "target_codebase": "目标代码库",
}

ROLE_LABELS = {
    "reference_project": "参考项目",
    "requirement_source": "需求来源",
    "background_knowledge": "背景知识",
    "design_constraint": "设计约束",
    "implementation_example": "实现样例",
    "target_codebase": "目标代码库",
}

ANALYSIS_LABELS = {
    "pending": "已添加",
    "resolving": "解析中",
    "fetching": "抓取中",
    "analyzing": "分析中",
    "analyzed": "分析完成",
    "partial": "部分完成",
    "blocked": "已阻塞",
    "failed": "分析失败",
}

LICENSE_LABELS = {
    "green": "低风险",
    "yellow": "需确认",
    "red": "高风险",
    "unknown": "未知",
}

ARTIFACT_LABELS = {
    "knowledge_card": "知识摘要",
    "reference_project_profile": "参考项目画像",
    "repository_understanding": "仓库理解",
    "text_understanding": "文本理解",
    "codebase_snapshot": "代码库快照",
    "target_codebase_snapshot": "目标代码库快照",
}


def build_source_understandings(store: AriadneStore) -> list[SourceUnderstandingDTO]:
    previews = store.list_backlog_previews()
    understandings: list[SourceUnderstandingDTO] = []
    for source in store.list_source_documents():
        artifacts = store.list_source_artifacts(source.id)
        evidence = store.list_source_evidence(source.id)
        source_type = source.source_type.value
        source_role = str(source.metadata.get("source_role") or _default_role(source_type))
        analysis_status = str(source.metadata.get("analysis_status") or "pending")
        license_risk = str(source.metadata.get("license_risk") or "unknown")
        understandings.append(
            SourceUnderstandingDTO(
                source_id=source.id,
                display_title=source.title,
                kind_label=KIND_LABELS.get(source_type, source_type),
                role_label=ROLE_LABELS.get(source_role, "背景知识"),
                analysis_label=ANALYSIS_LABELS.get(analysis_status, analysis_status),
                license_risk_label=LICENSE_LABELS.get(license_risk, "未知"),
                what_ariadne_understood=_understood_points(store, source, artifacts),
                evidence_items=[_evidence_item(item) for item in evidence[:5]],
                generated_outputs=[ARTIFACT_LABELS.get(item.artifact_type, item.artifact_type) for item in artifacts],
                risks=_risks(store, artifacts, source),
                impacted_ticket_keys=_impacted_ticket_keys(previews, source, artifacts, evidence),
                next_actions=_next_actions(analysis_status, artifacts, evidence),
            )
        )
    return understandings


def build_source_events(store: AriadneStore) -> list[SourceInputEventDTO]:
    events: list[SourceInputEventDTO] = []
    for source in store.list_source_documents():
        status = str(source.metadata.get("analysis_status") or "pending")
        events.append(
            SourceInputEventDTO(
                id=f"source-event-{source.id}-{status}",
                source_id=source.id,
                event_type=f"source.{status}",
                label=f"{source.title}: {ANALYSIS_LABELS.get(status, status)}",
                created_at=str(source.created_at),
            )
        )
        for record in store.list_source_fetch_records(source.id):
            if record.status == "cached":
                detail = f"已缓存 {record.commit_sha[:8] if record.commit_sha else 'unknown'} · {record.file_count} 个文件"
            elif record.status == "blocked":
                detail = f"仓库抓取阻塞：{record.error or 'unknown'}"
            else:
                detail = "已关联本地仓库"
            events.append(
                SourceInputEventDTO(
                    id=f"source-fetch-{record.id}",
                    source_id=source.id,
                    event_type=f"source.fetch.{record.status}",
                    label=f"{source.title}: {detail}",
                    created_at=str(record.created_at),
                )
            )
    return sorted(events, key=lambda item: item.created_at, reverse=True)[:20]


def _default_role(source_type: str) -> str:
    if source_type == "github_repo":
        return "reference_project"
    if source_type == "target_codebase":
        return "target_codebase"
    return "background_knowledge"


def _evidence_item(evidence: SourceEvidence) -> SourceEvidenceItemDTO:
    confidence = "高" if evidence.confidence >= 0.75 else "中" if evidence.confidence >= 0.45 else "低"
    return SourceEvidenceItemDTO(
        locator=evidence.locator,
        summary=evidence.quote_or_summary,
        claim=evidence.claim,
        confidence_label=confidence,
    )


def _understood_points(store: AriadneStore, source: SourceDocument, artifacts: list[SourceArtifact]) -> list[str]:
    if not artifacts:
        return ["Ariadne 已保存这个输入，等待分析。"]
    points: list[str] = []
    for artifact in artifacts:
        payload = store.load_source_artifact_payload(artifact.id)
        if artifact.artifact_type in {"reference_project_profile", "repository_understanding"}:
            points.append(f"这是一个参考项目：{payload.get('repo_summary') or source.summary or source.title}")
            identity = payload.get("identity") or {}
            if isinstance(identity, dict) and identity.get("commit_sha"):
                points.append(f"已缓存 commit {str(identity['commit_sha'])[:8]}。")
            manifests = [str(item) for item in payload.get("manifests", [])]
            tests = payload.get("tests") or {}
            test_paths = [str(item) for item in tests.get("paths", [])] if isinstance(tests, dict) else []
            if manifests or test_paths:
                parts = []
                if manifests:
                    parts.append(f"manifest: {', '.join(manifests[:3])}")
                if test_paths:
                    parts.append(f"tests: {len(test_paths)}")
                points.append("已读取 README / " + " / ".join(parts))
            patterns = [str(item) for item in payload.get("behavior_patterns", [])[:3]]
            if patterns:
                points.append(f"可参考模式：{'; '.join(patterns)}")
            avoid_notes = [str(item) for item in payload.get("avoid_notes", [])[:2]]
            if avoid_notes:
                points.append(f"避免事项：{'; '.join(avoid_notes)}")
        elif artifact.artifact_type == "codebase_snapshot":
            top_level = payload.get("top_level") or []
            points.append(f"这是目标代码库快照，包含 {len(top_level)} 个顶层入口。")
            test_commands = [str(item) for item in payload.get("test_commands", [])]
            if test_commands:
                points.append(f"识别到测试命令：{', '.join(test_commands)}")
        else:
            points.append(str(payload.get("summary") or source.summary or source.title))
    return points[:5]


def _risks(store: AriadneStore, artifacts: list[SourceArtifact], source: SourceDocument) -> list[str]:
    risks: list[str] = []
    license_risk = str(source.metadata.get("license_risk") or "unknown")
    if license_risk in {"yellow", "red", "unknown"}:
        risks.append("许可证或复用边界需要确认。")
    for artifact in artifacts:
        payload = store.load_source_artifact_payload(artifact.id)
        risks.extend(str(item) for item in payload.get("avoid_notes", [])[:2])
    return risks[:4]


def _impacted_ticket_keys(
    previews: object,
    source: SourceDocument,
    artifacts: list[SourceArtifact],
    evidence: list[SourceEvidence],
) -> list[str]:
    source_ids = {source.id}
    artifact_ids = {artifact.id for artifact in artifacts}
    evidence_ids = {item.id for item in evidence}
    keys: list[str] = []
    for preview in previews:  # type: ignore[union-attr]
        for operation in preview.operations:
            metadata = operation.metadata
            if source_ids & set(metadata.get("source_document_ids", [])):
                keys.append(operation.ticket_key or "NEW")
            elif artifact_ids & set(metadata.get("source_artifact_ids", [])):
                keys.append(operation.ticket_key or "NEW")
            elif evidence_ids & set(metadata.get("evidence_refs", [])):
                keys.append(operation.ticket_key or "NEW")
    return sorted(set(keys))[:8]


def _next_actions(analysis_status: str, artifacts: list[SourceArtifact], evidence: list[SourceEvidence]) -> list[str]:
    if analysis_status == "pending":
        return ["添加并分析", "等待生成结构化理解"]
    if analysis_status in {"blocked", "failed"}:
        return ["查看阻塞原因", "重新分析"]
    if artifacts and evidence:
        return ["查看任务建议", "应用任务变更"]
    return ["重新分析", "补充摘要"]
