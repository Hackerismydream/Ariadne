from __future__ import annotations

import json
from pathlib import Path

from ariadne_ltb.models import (
    BuildPacket,
    BuildTicket,
    ExecutionResult,
    FeishuWritePlan,
    MemoryRecord,
    ReviewReport,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


def write_memory_record(
    store: AriadneStore,
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult,
    review: ReviewReport,
) -> tuple[MemoryRecord, Path]:
    memory = MemoryRecord(
        id=stable_id("memory", ticket.id, review.id),
        ticket_id=ticket.id,
        title=f"{ticket.key} - {ticket.title}",
        decision_log_entry=(
            f"{ticket.key}: executed `{execution.backend_name}` for {packet.build_decision.value}; "
            f"review verdict `{review.verdict.value}`."
        ),
        build_summary=(
            f"Backend {execution.backend_name} changed {', '.join(execution.changed_files) or 'no files'} "
            f"with exit code {execution.exit_code} and test exit code {execution.test_exit_code}."
        ),
        review_summary=f"Passed {len(review.passed_checks)} checks; failed {len(review.failed_checks)} checks.",
        source_refs=[ticket.source_ref],
        artifact_refs=ticket.artifact_ids,
        next_actions=[
            "Review generated target project diff.",
            "Convert remaining experiment/doc tickets into future Build Tickets.",
            "Keep real Feishu writes disabled until credentials and confirmation are present.",
        ],
    )
    store.save_memory_record(memory)
    memory_dir = store.memory_dir
    (memory_dir / "build_packets" / f"{packet.id}.json").write_text(
        packet.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    review_md = memory_dir / "reviews" / f"{ticket.id}.md"
    review_md.write_text(
        f"# Review - {ticket.key}\n\nVerdict: `{review.verdict.value}`\n\n"
        f"## Passed\n\n{_bullets(review.passed_checks)}\n\n"
        f"## Failed\n\n{_bullets(review.failed_checks)}\n",
        encoding="utf-8",
    )
    decision_log = memory_dir / "decision_log.md"
    with decision_log.open("a", encoding="utf-8") as handle:
        handle.write(f"- {memory.created_at} {memory.decision_log_entry}\n")
    weekly = memory_dir / "weekly_summary.md"
    weekly.write_text(
        "# Ariadne Weekly Summary\n\n"
        f"- Completed: {ticket.key} with review verdict `{review.verdict.value}`.\n"
        f"- Changed files: {', '.join(execution.changed_files)}\n",
        encoding="utf-8",
    )
    ticket_md = memory_dir / "tickets" / f"{ticket.id}.md"
    ticket_md.write_text(
        f"# {memory.title}\n\n"
        f"## Decision\n\n{memory.decision_log_entry}\n\n"
        f"## Build Summary\n\n{memory.build_summary}\n\n"
        f"## Next Actions\n\n{_bullets(memory.next_actions)}\n",
        encoding="utf-8",
    )
    return memory, ticket_md


def generate_feishu_plan(
    store: AriadneStore,
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult,
    review: ReviewReport,
) -> tuple[FeishuWritePlan, Path]:
    plan = FeishuWritePlan(
        id=stable_id("feishu", ticket.id, review.id),
        ticket_id=ticket.id,
        dry_run=True,
        proposed_docs=[
            {
                "title": f"{ticket.key} Learning-to-Build Result",
                "body_markdown": (
                    f"# {ticket.title}\n\n"
                    f"Review verdict: `{review.verdict.value}`\n\n"
                    f"Changed files: {', '.join(execution.changed_files)}\n\n"
                    f"Decision: {packet.build_decision.value}\n"
                ),
            }
        ],
        proposed_tasks=[
            {"title": "Review Ariadne 1.0 demo board", "priority": "medium", "due": "unscheduled"}
        ],
        decision_log_entry=(
            f"{ticket.key}: Feishu write remains dry-run. Required credentials for real write: "
            "FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_FOLDER_TOKEN, FEISHU_ENABLE_WRITE=1."
        ),
        run_summary=(
            f"Backend {execution.backend_name}; exit {execution.exit_code}; "
            f"tests {execution.test_exit_code}; verdict {review.verdict.value}."
        ),
        next_actions=[
            "Keep this plan as preview unless `--confirm-write` and credentials are provided.",
            "Create follow-up implementation tickets for remaining source inputs.",
        ],
    )
    store.save_feishu_write_plan(plan)
    path = store.feishu_plans_dir / f"{plan.id}.json"
    path.write_text(json.dumps(plan.model_dump(), indent=2) + "\n", encoding="utf-8")
    return plan, path


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- None"
