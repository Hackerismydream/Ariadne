from __future__ import annotations

import subprocess

from ariadne_ltb.models import BuildTicket, ProjectResource, TicketAssignment, stable_id
from ariadne_ltb.storage import AriadneStore


def prepare_assignment_for_claim(
    store: AriadneStore,
    assignment: TicketAssignment,
    ticket: BuildTicket | None = None,
    *,
    route_decision_id: str | None = None,
    handoff_packet_id: str | None = None,
    permission_profile_id: str | None = None,
    authorization_id: str | None = None,
) -> TicketAssignment:
    resolved_ticket = ticket or store.load_ticket(assignment.ticket_id)
    ready = assignment.mark_ready_to_claim(
        readiness_metadata(
            store,
            assignment,
            resolved_ticket,
            route_decision_id=route_decision_id,
            handoff_packet_id=handoff_packet_id,
            permission_profile_id=permission_profile_id,
            authorization_id=authorization_id,
        )
    )
    store.save_assignment(ready)
    return ready


def readiness_metadata(
    store: AriadneStore,
    assignment: TicketAssignment,
    ticket: BuildTicket,
    *,
    route_decision_id: str | None = None,
    handoff_packet_id: str | None = None,
    permission_profile_id: str | None = None,
    authorization_id: str | None = None,
) -> dict[str, str]:
    target_project_id = assignment.metadata.get("target_project_id") or ticket.metadata.get("target_project_id")
    target_repo_path = assignment.metadata.get("target_repo_path") or ""
    if target_project_id and not target_repo_path:
        target_repo_path = _target_project_path(store, str(target_project_id))
    expected_git_head = _git_head(str(target_repo_path)) if target_repo_path else "unknown"
    auth_key = "runtime_authorization_id" if authorization_id else "confirmation_id"
    auth_value = authorization_id or assignment.metadata.get("confirmation_id") or stable_id("confirmation", assignment.id)
    return {
        "target_project_id": str(target_project_id or ""),
        "route_decision_id": str(
            route_decision_id or assignment.metadata.get("route_decision_id") or stable_id("route", assignment.id)
        ),
        "handoff_packet_id": str(
            handoff_packet_id or assignment.metadata.get("handoff_packet_id") or stable_id("handoff", assignment.id)
        ),
        "permission_profile_id": str(
            permission_profile_id
            or assignment.metadata.get("permission_profile_id")
            or "local_workbench_default"
        ),
        auth_key: str(auth_value),
        "handoff_hash": str(assignment.metadata.get("handoff_hash") or stable_id("handoff_hash", assignment.id)),
        "target_repo_path": str(target_repo_path),
        "expected_git_head": expected_git_head,
    }


def ensure_assignment_target_resource(
    store: AriadneStore,
    target_repo_path: str,
    *,
    target_project_id: str = "ariadne-local",
    label: str | None = None,
) -> None:
    resources = store.load_project_resources()
    resource = ProjectResource.local_directory(target_project_id, target_repo_path, label=label)
    by_id = {existing.id: existing for existing in resources}
    by_id[resource.id] = resource
    store.save_project_resources(sorted(by_id.values(), key=lambda item: item.label or item.id))


def _git_head(target_repo_path: str) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=target_repo_path,
            check=True,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def _target_project_path(store: AriadneStore, target_project_id: str) -> str:
    for resource in store.load_project_resources():
        if resource.id == target_project_id:
            return str(resource.resource_ref.get("local_path") or "")
    return ""
