from __future__ import annotations

import json

from ariadne_ltb.models import (
    Artifact,
    ArtifactType,
    BuildPacket,
    BuildTicket,
    ExecutionResult,
    ReviewReport,
    ReviewVerdict,
    utc_now,
)
from ariadne_ltb.storage import AriadneStore


def generate_next_tickets_artifact(
    store: AriadneStore,
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult,
    review: ReviewReport,
    run_id: str,
) -> Artifact:
    payload = {
        "source_ticket_id": ticket.id,
        "source_ticket_key": ticket.key,
        "review_verdict": review.verdict.value,
        "generated_at": utc_now(),
        "next_tickets": _suggestions(ticket, packet, execution, review),
    }
    return store.write_artifact(
        ticket.id,
        run_id,
        ArtifactType.NEXT_TICKETS,
        "next_tickets.json",
        json.dumps(payload, indent=2) + "\n",
        "Generated next Build Ticket suggestions",
        metadata={"source": "review_memory_loop"},
    )


def _suggestions(
    ticket: BuildTicket,
    packet: BuildPacket,
    execution: ExecutionResult,
    review: ReviewReport,
) -> list[dict]:
    suggestions: list[dict] = []
    if review.verdict in {ReviewVerdict.NEEDS_FIX, ReviewVerdict.BLOCKED}:
        suggestions.append(
            {
                "title": f"Fix {ticket.key} run blockers",
                "reason": "; ".join(review.failed_checks or review.required_fixes or execution.warnings),
                "source": "failed_check",
                "priority": "high",
                "suggested_build_decision": "code_task",
                "acceptance_criteria": [
                    "Blocked or failing execution checks pass.",
                    "Reviewer verdict changes to pass or needs_human_review with explicit rationale.",
                ],
                "affected_modules": packet.affected_modules,
            }
        )
    else:
        suggestions.append(
            {
                "title": "Add retrieval over local memory",
                "reason": (
                    "Memory is written after ticket runs but is not yet indexed or cited by future planning."
                ),
                "source": "memory",
                "priority": "high",
                "suggested_build_decision": "code_task",
                "acceptance_criteria": [
                    "Planner can search prior memory records.",
                    "Search results are cited in Build Packet evidence.",
                ],
                "affected_modules": ["ariadne_ltb/memory.py", "ariadne_ltb/planner.py"],
            }
        )

    if execution.changed_files:
        suggestions.append(
            {
                "title": f"Add regression guard for {packet.build_decision.value} changes",
                "reason": f"Recent run changed {', '.join(execution.changed_files)}.",
                "source": "changed_file",
                "priority": "medium",
                "suggested_build_decision": "code_task",
                "acceptance_criteria": [
                    "Regression test covers the changed behavior.",
                    "Board shows the test result for the ticket run.",
                ],
                "affected_modules": execution.changed_files[:4],
            }
        )

    if review.warnings:
        suggestions.append(
            {
                "title": "Reduce reviewer warnings in ticket runs",
                "reason": "; ".join(review.warnings),
                "source": "review",
                "priority": "medium",
                "suggested_build_decision": "doc_update",
                "acceptance_criteria": [
                    "Warnings are either resolved or documented with explicit rationale.",
                ],
                "affected_modules": ["ariadne_ltb/review.py", "ariadne_ltb/board.py"],
            }
        )

    suggestions.append(
        {
            "title": "Expand Feishu dry-run plan into docs plus tasks",
            "reason": f"{ticket.key} produced a dry-run Feishu plan but real write remains gated.",
            "source": "source_type",
            "priority": "low",
            "suggested_build_decision": "experiment",
            "acceptance_criteria": [
                "Dry-run plan separates document body and task payloads.",
                "Real write path stays gated by FEISHU_ENABLE_WRITE and --confirm-write.",
            ],
            "affected_modules": ["ariadne_ltb/feishu.py", "ariadne_ltb/memory.py"],
        }
    )
    return suggestions[:5]
