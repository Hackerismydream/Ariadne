from __future__ import annotations

from pathlib import Path

from ariadne_ltb.board import export_board
from ariadne_ltb.doctor import integration_doctor_snapshot, product_readiness_snapshot
from ariadne_ltb.git_utils import git_head, is_git_repo, run_git
from ariadne_ltb.models import ReleaseEvidencePacket, ReviewReport, stable_id
from ariadne_ltb.runtime import collect_runtime_capabilities
from ariadne_ltb.secret_safety import scan_for_secrets
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.store_doctor import check_store_invariants
from ariadne_ltb.workdir_policy import list_workdirs


def generate_release_evidence_packet(store: AriadneStore) -> tuple[ReleaseEvidencePacket, Path]:
    board_path = export_board(store)
    invariant_report = check_store_invariants(store)
    integration_doctor_snapshot(store, store.root)
    secret_scan = scan_for_secrets(store.root)
    workdirs = list_workdirs(store)
    reviews = store.list_review_reports()
    capabilities = store.load_runtime_capabilities() or collect_runtime_capabilities()
    packet = ReleaseEvidencePacket(
        id=stable_id("release_evidence", store.root, len(store.list_tickets()), len(reviews)),
        root_path=str(store.root),
        git_head=git_head(store.root),
        git_branch=_git_branch(store.root),
        ticket_count=len(store.list_tickets()),
        assignment_count=len(store.list_assignments()),
        open_assignment_count=len(store.list_open_assignments()),
        execution_result_count=len(store.list_execution_results()),
        review_report_count=len(reviews),
        memory_record_count=len(store.list_memory_records()),
        inbox_item_count=len(store.list_inbox_items()),
        workdir_count=len(workdirs),
        active_workdir_count=sum(1 for item in workdirs if item.active and item.exists),
        dirty_workdir_count=sum(1 for item in workdirs if item.dirty),
        board_path=str(board_path),
        store_invariant_report_path=str(store.doctor_dir / "store_invariants.json"),
        store_invariants_ok=invariant_report.ok,
        store_invariant_errors=invariant_report.error_count,
        store_invariant_warnings=invariant_report.warning_count,
        secret_scan_ok=secret_scan.ok,
        secret_finding_count=len(secret_scan.findings),
        runtime_capabilities=capabilities,
        latest_review_verdicts=_latest_review_verdicts(reviews),
        evidence_refs={
            "board": str(board_path),
            "store_invariants": str(store.doctor_dir / "store_invariants.json"),
            "integration_doctor": str(store.doctor_dir / "integrations.json"),
            "runtime_capabilities": str(store.runtimes_dir / "capability_snapshot.json"),
            "inbox": str(store.inbox_items_path),
            "backend_smoke_evidence": str(store.backend_smoke_evidence_dir),
            "feishu_integrations": str(store.feishu_integrations_dir),
            "github_integrations": str(store.github_integrations_dir),
            "landing_gate_reports": str(store.artifact_index_dir),
            "product_readiness": str(store.doctor_dir / "product_readiness.json"),
            "release_packet": str(store.release_evidence_packet_path),
        },
    )
    path = store.save_release_evidence_packet(packet)
    product_readiness = product_readiness_snapshot(store, store.root)
    packet = packet.model_copy(
        deep=True,
        update={
            "product_readiness_status": product_readiness["overall_status"],
            "production_acceptance_status": product_readiness["production_acceptance_status"],
            "run_gate_status": product_readiness["run_gate_status"],
            "product_readiness_checks": {
                check["name"]: check["status"] for check in product_readiness["checks"]
            },
            "readiness_next_actions": product_readiness["next_actions"],
            "readiness_blockers": product_readiness["blocking_checks"],
            "evidence_packet_stale": product_readiness["release_evidence_packet"]["stale"],
            "evidence_packet_stale_reasons": product_readiness["release_evidence_packet"][
                "stale_reasons"
            ],
            "real_success_evidence": product_readiness["real_success_evidence"],
            "real_failure_evidence": product_readiness["real_failure_evidence"],
            "local_success_evidence": product_readiness["local_success_evidence"],
            "local_failure_evidence": product_readiness["local_failure_evidence"],
        },
    )
    path = store.save_release_evidence_packet(packet)
    return packet, path


def _git_branch(repo: Path) -> str | None:
    if not is_git_repo(repo):
        return None
    result = run_git(repo, "branch", "--show-current")
    branch = result.stdout.strip()
    return branch or None


def _latest_review_verdicts(reviews: list[ReviewReport]) -> dict[str, str]:
    by_ticket: dict[str, ReviewReport] = {}
    for review in sorted(reviews, key=lambda item: item.created_at):
        by_ticket[review.ticket_id] = review
    return {ticket_id: review.verdict.value for ticket_id, review in by_ticket.items()}
