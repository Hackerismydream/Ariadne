from __future__ import annotations

from typing import Literal

from pydantic import Field

from ariadne_ltb.models import AriadneModel, utc_now


class ClaimWithEvidence(AriadneModel):
    claim: str
    locator: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_document_id: str | None = None


class ProjectPurpose(AriadneModel):
    project_id: str
    title: str
    one_line: str
    why_this_exists: str = ""
    target_users: list[str] = Field(default_factory=list)
    success_signals: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class SourceInsight(AriadneModel):
    id: str
    project_id: str
    source_document_id: str
    summary: str
    key_claims: list[ClaimWithEvidence] = Field(default_factory=list)
    reusable_patterns: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    revision: int = 1
    last_ingest_cycle: str


class SynthesisTheme(AriadneModel):
    id: str
    project_id: str
    label: str
    contributing_source_ids: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    priority_signal: Literal["high", "medium", "low"] = "medium"
    affected_modules: list[str] = Field(default_factory=list)
    revision: int = 1
    last_updated_cycle: str


class ContradictionRecord(AriadneModel):
    id: str
    project_id: str
    summary: str
    competing_claims: list[ClaimWithEvidence] = Field(default_factory=list)
    status: Literal["open", "deferred", "resolved"] = "open"
    resolution: str | None = None
    affected_theme_ids: list[str] = Field(default_factory=list)


class BlockerLearning(AriadneModel):
    id: str
    project_id: str
    blocker_reason: str
    failure_pattern: str
    mitigation: str
    seen_in_ticket_keys: list[str] = Field(default_factory=list)
    seen_count: int = 1


class OutcomeEntry(AriadneModel):
    ticket_key: str
    ticket_title: str
    status: Literal["done", "blocked", "abandoned"]
    review_verdict: str | None = None
    blocker_reason: str | None = None
    learnings: list[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=utc_now)


class OutcomesLog(AriadneModel):
    project_id: str
    entries: list[OutcomeEntry] = Field(default_factory=list)

