from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from ariadne_ltb.board import export_board
from ariadne_ltb.backlog import (
    apply_backlog_preview,
    generate_codebase_observation_preview,
    generate_execution_feedback_preview,
    generate_memory_gap_preview,
    generate_review_feedback_preview,
)
from ariadne_ltb.defaults import PRODUCT_DEFAULT_BACKEND
from ariadne_ltb.execution import backend_for_name
from ariadne_ltb.git_utils import git_branch, git_head, git_status
from ariadne_ltb.handoffs import record_handoff
from ariadne_ltb.journal import runtime_event
from ariadne_ltb.local_safety import DirectoryLock, validate_target_repo_path
from ariadne_ltb.llm import DeepSeekClient
from ariadne_ltb.llm_agents import LLMAgentResult, LLMAgentRole, run_ticket_llm_agent
from ariadne_ltb.llm_backlog import generate_llm_backlog_artifact
from ariadne_ltb.memory import generate_feishu_plan, write_memory_record
from ariadne_ltb.models import (
    AgentRun,
    AgentRunStatus,
    Artifact,
    ArtifactType,
    BuildTicket,
    CommentAuthorType,
    CommentKind,
    DaemonStatus,
    ExecutionContext,
    ExecutionResult,
    FailureReason,
    FeishuWritePlan,
    HandoffPacket,
    HandoffStatus,
    LandingArtifactRef,
    LandingEvidence,
    LandingTestResult,
    MemoryRecord,
    ProjectResource,
    RouteDecision,
    RunMessageType,
    ReviewVerdict,
    TicketStatus,
    WorkerHeartbeat,
    stable_id,
    utc_now,
)
from ariadne_ltb.next_tickets import generate_next_tickets_artifact
from ariadne_ltb.permissions import build_execution_permission_profile, permission_profile_handoff_section
from ariadne_ltb.planner import planner_for_name
from ariadne_ltb.review import review_execution
from ariadne_ltb.runtime import collect_runtime_capabilities
from ariadne_ltb.skills import materialize_build_skills, materialized_skill_handoff_section
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project, target_test_command
from ariadne_ltb.worktrees import WorktreeBlock, prepare_isolated_worktree


@dataclass(frozen=True)
class TicketRunResult:
    ticket_id: str
    ticket_key: str
    backend_name: str
    planner_name: str
    agent_runtime: str
    build_packet_id: str
    handoff_artifact_id: str
    execution_result_id: str
    review_report_id: str
    review_verdict: str
    changed_files: list[str]
    test_exit_code: int | None
    memory_record_id: str
    memory_path: str
    feishu_plan_id: str
    feishu_plan_path: str
    next_tickets_path: str
    backlog_planner_name: str
    backlog_planner_artifact_path: str | None
    llm_agent_artifact_paths: list[str]
    backlog_preview_ids: list[str]
    backlog_update_ids: list[str]
    board_path: str
    board_html_path: str
    orchestrator_result_path: str
    landing_evidence_json_path: str
    landing_evidence_md_path: str
    worktree_path: str | None = None


class TicketRunOrchestrator:
    def __init__(
        self,
        store: AriadneStore,
        runtime_id: str = "local",
        assignment_id: str | None = None,
        actor_name: str = "Ariadne",
    ) -> None:
        self.store = store
        self.runtime_id = runtime_id
        self.assignment_id = assignment_id
        self.actor_name = actor_name

    def run_ticket(
        self,
        ticket_id_or_key: str,
        backend_name: str = PRODUCT_DEFAULT_BACKEND,
        target_repo_path: str | None = None,
        command: str | None = None,
        planner: str = "deterministic",
        agent_runtime: str = "deterministic",
        backlog_planner: str = "deterministic",
        llm_agent_client: DeepSeekClient | None = None,
        backlog_planner_client: DeepSeekClient | None = None,
        use_memory: bool = False,
        confirm_execution: bool = False,
        timeout_seconds: int = 60,
        isolate_worktree: bool = False,
    ) -> TicketRunResult:
        ticket = self.store.resolve_ticket(ticket_id_or_key)
        if ticket.status is TicketStatus.SUPERSEDED:
            msg = f"ticket {ticket.key} is superseded and cannot be run"
            raise RuntimeError(msg)
        if agent_runtime not in {"deterministic", "llm"}:
            msg = f"unknown agent runtime: {agent_runtime}"
            raise ValueError(msg)
        llm_agent_artifact_paths: list[str] = []
        backlog_preview_ids: list[str] = []
        applied_preview_update_ids: list[str] = []
        ticket = ticket.with_status(TicketStatus.PLANNING, "Build Lead")
        self.store.save_ticket(ticket)
        record_handoff(
            self.store,
            ticket,
            self.runtime_id,
            "Build Lead",
            "Planner",
            "Need Build Packet and coding handoff.",
            self.assignment_id,
        )
        if agent_runtime == "llm":
            build_lead_result = run_ticket_llm_agent(
                self.store,
                ticket,
                LLMAgentRole.BUILD_LEAD,
                client=llm_agent_client,
            )
            if build_lead_result.artifact_path:
                llm_agent_artifact_paths.append(build_lead_result.artifact_path)
            ticket = self.store.load_ticket(ticket.id)
            self._progress(
                ticket,
                "llm_build_lead",
                "succeeded" if build_lead_result.succeeded else "blocked",
                (
                    "DeepSeek Build Lead role completed."
                    if build_lead_result.succeeded
                    else f"DeepSeek Build Lead role blocked: {build_lead_result.error}"
                ),
                payload_ref=build_lead_result.artifact_id,
            )
            self._require_llm_role_success(ticket, build_lead_result)

        planner_result = planner_for_name(planner, use_memory=use_memory).plan_ticket(self.store, ticket)
        if not planner_result.succeeded:
            board_path = export_board(self.store)
            msg = planner_result.error or "planner failed"
            raise RuntimeError(f"{planner} planner failed for {ticket.key}: {msg}; board: {board_path}")

        ticket = self.store.load_ticket(ticket.id)
        self._progress(ticket, "planning", "succeeded", "Planner generated Build Packet and handoff.")
        packet = self.store.load_build_packet(planner_result.build_packet_id or ticket.build_packet_id)
        handoff_artifact = self.store.load_artifact(planner_result.handoff_artifact_id)
        handoff_prompt = self.store.read_artifact_text(handoff_artifact)
        assignment_handoff_packet = self._load_assignment_handoff_packet()
        if assignment_handoff_packet is not None:
            handoff_prompt = Path(assignment_handoff_packet.markdown_path).read_text(encoding="utf-8")
        if agent_runtime == "llm":
            knowledge_result = run_ticket_llm_agent(
                self.store,
                self.store.load_ticket(ticket.id),
                LLMAgentRole.KNOWLEDGE,
                client=llm_agent_client,
            )
            if knowledge_result.artifact_path:
                llm_agent_artifact_paths.append(knowledge_result.artifact_path)
            ticket = self.store.load_ticket(ticket.id)
            self._progress(
                ticket,
                "llm_knowledge",
                "succeeded" if knowledge_result.succeeded else "blocked",
                (
                    "DeepSeek Knowledge role completed."
                    if knowledge_result.succeeded
                    else f"DeepSeek Knowledge role blocked: {knowledge_result.error}"
                ),
                payload_ref=knowledge_result.artifact_id,
            )
            self._require_llm_role_success(ticket, knowledge_result)
        record_handoff(
            self.store,
            ticket,
            self.runtime_id,
            "Planner",
            "Execution",
            "Build Packet and coding handoff are ready.",
            self.assignment_id,
            payload_ref=handoff_artifact.id,
        )

        target_repo = (
            Path(assignment_handoff_packet.target_repo_path).resolve()
            if assignment_handoff_packet is not None
            else Path(target_repo_path).resolve() if target_repo_path else ensure_demo_target_project(self.store.root)
        )
        target_validation = validate_target_repo_path(target_repo)
        worktree_block: WorktreeBlock | None = None
        worktree_path: str | None = None
        if isolate_worktree and target_validation.valid:
            isolation = prepare_isolated_worktree(self.store, ticket, target_repo, self.assignment_id)
            if isolation.block:
                worktree_block = isolation.block
            elif isolation.record:
                worktree_metadata = isolation.record.model_dump(mode="json", exclude_none=False)
                worktree_artifact = self.store.write_artifact(
                    ticket.id,
                    "build_lead",
                    ArtifactType.WORKTREE_ISOLATION,
                    "worktree_isolation.json",
                    isolation.record.model_dump_json(indent=2) + "\n",
                    "Local git worktree isolation record",
                    metadata={
                        "worktree_path": isolation.record.worktree_path,
                        "branch_name": isolation.record.branch_name,
                        "base_sha": isolation.record.base_sha,
                    },
                )
                ticket = (
                    self.store.load_ticket(ticket.id)
                    .with_artifacts([worktree_artifact])
                    .append_event(
                        "worktree_isolated",
                        "Build Lead",
                        f"Created isolated worktree `{isolation.record.worktree_path}`.",
                        payload_ref=worktree_artifact.id,
                    )
                    .model_copy(
                        deep=True,
                        update={
                            "metadata": self.store.load_ticket(ticket.id).metadata
                            | {"worktree_isolation": worktree_metadata}
                        },
                    )
                )
                self.store.save_ticket(ticket)
                self._progress(
                    ticket,
                    "worktree",
                    "succeeded",
                    f"Created isolated worktree `{isolation.record.worktree_path}`.",
                    payload_ref=worktree_artifact.id,
                )
                target_repo = Path(isolation.record.worktree_path)
                target_validation = validate_target_repo_path(target_repo)
                worktree_path = isolation.record.worktree_path
        runtime_capability_path = self.store.save_runtime_capabilities(collect_runtime_capabilities())
        resource_label = f"{ticket.key} isolated worktree" if worktree_path else f"{ticket.key} target repository"
        project_resources = [
            ProjectResource.local_directory(
                "ariadne-local",
                target_repo,
                label=resource_label,
            )
        ]
        project_resources_path = self.store.save_project_resources(project_resources)
        skill_bundle_artifact, skill_materializations = materialize_build_skills(
            self.store,
            ticket,
            "build_lead",
            backend_name,
        )
        skill_refs = [item.skill_name for item in skill_materializations if item.included]
        execution_command = command or (packet.tasks[0] if packet.tasks else ticket.title)
        execution_test_command = (
            assignment_handoff_packet.test_command
            if assignment_handoff_packet is not None
            else target_test_command()
        )
        allowed_paths = (
            assignment_handoff_packet.allowed_paths
            if assignment_handoff_packet is not None
            else packet.affected_modules
        )
        permission_profile = build_execution_permission_profile(
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            backend_name=backend_name,
            target_repo_path=str(target_repo),
            allowed_paths=allowed_paths,
            external_execution_enabled=os.environ.get("ARIADNE_ENABLE_EXTERNAL_EXECUTION") == "1",
            confirm_execution=confirm_execution,
            command=execution_command,
            test_command=execution_test_command,
        )
        permission_artifact = self.store.write_artifact(
            ticket.id,
            "build_lead",
            ArtifactType.PERMISSION_PROFILE,
            "execution_permission_profile.json",
            permission_profile.model_dump_json(indent=2) + "\n",
            "Execution permission profile",
            metadata={"permission_profile_id": permission_profile.id},
        )
        if assignment_handoff_packet is None:
            handoff_prompt = _augment_handoff_with_project_resources(
                handoff_prompt,
                project_resources,
                target_repo,
                worktree_path,
            )
            handoff_prompt = (
                handoff_prompt.rstrip()
                + materialized_skill_handoff_section(skill_bundle_artifact, skill_materializations)
                + permission_profile_handoff_section(permission_profile, permission_artifact.path)
            )
            Path(handoff_artifact.path).write_text(handoff_prompt, encoding="utf-8")
        route_decision = RouteDecision(
            id=stable_id("route", ticket.id, backend_name, str(target_repo)),
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            planner_name=planner,
            backend_name=backend_name,
            target_repo_path=str(target_repo),
            build_decision=packet.build_decision,
            reason="Build Lead selected the requested backend for the ticket run.",
            external_execution_enabled=__import__("os").environ.get(
                "ARIADNE_ENABLE_EXTERNAL_EXECUTION"
            )
            == "1",
            confirm_execution=confirm_execution,
            permission_profile_id=permission_profile.id,
            skill_refs=skill_refs,
            resource_refs=[resource.id for resource in project_resources],
        )
        route_artifact = self.store.write_artifact(
            ticket.id,
            "build_lead",
            ArtifactType.ROUTE_DECISION,
            "route_decision.json",
            route_decision.model_dump_json(indent=2) + "\n",
            "Build Lead route decision",
            metadata={
                "runtime_capability_path": str(runtime_capability_path),
                "project_resources_path": str(project_resources_path),
                "permission_profile_path": permission_artifact.path,
                "skill_bundle_path": skill_bundle_artifact.path,
                "provider_skill_dir": skill_materializations[0].provider_skill_dir
                if skill_materializations
                else "",
            },
        )
        resources_artifact = self.store.write_artifact(
            ticket.id,
            "build_lead",
            ArtifactType.PROJECT_RESOURCES,
            "project_resources.json",
            Path(project_resources_path).read_text(encoding="utf-8"),
            "Project resource snapshot",
            metadata={"project_resources_path": str(project_resources_path)},
        )
        runtime_artifact = self.store.write_artifact(
            ticket.id,
            "build_lead",
            ArtifactType.RUNTIME_CAPABILITY,
            "runtime_capability_snapshot.json",
            Path(runtime_capability_path).read_text(encoding="utf-8"),
            "Runtime capability snapshot",
            metadata={"runtime_capability_path": str(runtime_capability_path)},
        )
        ticket = (
            self.store.load_ticket(ticket.id)
            .with_artifacts(
                [
                    skill_bundle_artifact,
                    permission_artifact,
                    route_artifact,
                    resources_artifact,
                    runtime_artifact,
                ]
            )
            .append_event(
                "route_decision",
                "Build Lead",
                f"Selected backend `{backend_name}` for `{target_repo}`.",
                payload_ref=route_artifact.id,
            )
        )
        self.store.save_ticket(ticket)
        self._progress(ticket, "route", "succeeded", f"Build Lead selected `{backend_name}`.")
        execution_run = _start_run(
            self.store,
            ticket,
            "Execution",
            "execution",
            backend_name,
            assignment_id=self.assignment_id,
            runtime_id=self.runtime_id,
        )
        context = ExecutionContext(
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            build_packet_id=packet.id,
            target_repo_path=str(target_repo),
            target_worktree_path=worktree_path,
            handoff_prompt=handoff_prompt,
            handoff_file=(
                assignment_handoff_packet.markdown_path
                if assignment_handoff_packet is not None
                else str(self.store.base / "handoffs" / f"{ticket.key}.md")
            ),
            backend_name=backend_name,
            allowed_paths=allowed_paths,
            command=execution_command,
            test_command=execution_test_command,
            confirm_execution=confirm_execution,
            timeout_seconds=timeout_seconds,
            assignment_id=self.assignment_id,
            run_id=execution_run.id,
            permission_profile_id=permission_profile.id,
            permission_profile_path=permission_artifact.path,
            skill_bundle_path=skill_bundle_artifact.path,
            provider_skill_dir=skill_materializations[0].provider_skill_dir
            if skill_materializations
            else None,
        )
        ticket = self.store.load_ticket(ticket.id).append_event(
            "execution_started",
            "Execution",
            f"{backend_name} execution started.",
            payload_ref=execution_run.id,
        )
        self.store.save_ticket(ticket)
        if worktree_block:
            execution = _blocked_execution(
                context,
                backend_name,
                worktree_block.reason,
                worktree_block.failure_reason,
            )
        elif not target_validation.valid:
            execution = _blocked_execution(context, backend_name, target_validation.reason, FailureReason.INVALID_RESOURCE)
        else:
            lock = DirectoryLock(
                self.store,
                target_repo,
                runtime_id=self.runtime_id,
                ticket_id=ticket.id,
                assignment_id=self.assignment_id,
            )
            try:
                lock.acquire()
            except RuntimeError as exc:
                execution = _blocked_execution(context, backend_name, str(exc), FailureReason.RESOURCE_LOCKED)
            else:
                try:
                    execution = backend_for_name(backend_name).execute(context)
                finally:
                    lock.release()
        execution = execution.model_copy(
            update={
                "target_repo_path": execution.target_repo_path or context.target_repo_path,
                "target_worktree_path": execution.target_worktree_path or context.target_worktree_path,
                "assignment_id": self.assignment_id,
                "run_id": execution_run.id,
            }
        )
        self.store.save_execution_result(execution)
        execution_artifacts = _write_execution_artifacts(self.store, execution_run.id, execution)
        execution = execution.model_copy(
            update={
                "execution_log_artifact_id": execution_artifacts["execution_log"].id,
                "diff_artifact_id": execution_artifacts["git_diff"].id,
            }
        )
        self.store.save_execution_result(execution)
        execution_status = (
            AgentRunStatus.BLOCKED
            if execution.blocked
            else AgentRunStatus.SUCCEEDED
            if execution.exit_code == 0 and (execution.test_exit_code in {0, None})
            else AgentRunStatus.FAILED
        )
        execution_run = _finish_run(
            self.store,
            execution_run,
            execution_status,
            _execution_summary(execution),
            [artifact.id for artifact in execution_artifacts.values()],
            execution.failure_reason,
        )
        ticket = (
            self.store.load_ticket(ticket.id)
            .with_run(execution_run.id)
            .with_artifacts(list(execution_artifacts.values()))
            .append_event(
                "execution_finished",
                "Execution",
                _execution_summary(execution),
                payload_ref=execution.id,
            )
            .with_status(TicketStatus.REVIEWING, "Execution")
        )
        record_handoff(
            self.store,
            ticket,
            self.runtime_id,
            "Execution",
            "Reviewer",
            "Execution produced result, diff, and tests.",
            self.assignment_id,
            payload_ref=execution.id,
        )
        self._progress(
            ticket,
            "execution",
            "blocked" if execution.blocked else "succeeded" if execution_status is AgentRunStatus.SUCCEEDED else "failed",
            _execution_summary(execution),
            payload_ref=execution.id,
        )
        ticket = ticket.model_copy(
            deep=True,
            update={"metadata": ticket.metadata | {"execution_result_id": execution.id}},
        )
        self.store.save_ticket(ticket)
        execution_preview = generate_execution_feedback_preview(self.store, self.store.load_ticket(ticket.id), execution)
        execution_preview_result = apply_backlog_preview(self.store, execution_preview.id)
        backlog_preview_ids.append(execution_preview.id)
        if execution_preview_result.update:
            applied_preview_update_ids.append(execution_preview_result.update.id)
        self._progress(
            self.store.load_ticket(ticket.id),
            "backlog_preview",
            "succeeded",
            "Applied execution feedback backlog preview.",
            payload_ref=execution_preview.id,
        )

        ticket_for_review = self.store.load_ticket(ticket.id)
        review_run = _start_run(
            self.store,
            ticket_for_review,
            "Reviewer",
            "reviewer",
            assignment_id=self.assignment_id,
            runtime_id=self.runtime_id,
        )
        ticket = self.store.load_ticket(ticket.id).append_event(
            "review_started",
            "Reviewer",
            "Reviewer started conservative result check.",
            payload_ref=review_run.id,
        )
        self.store.save_ticket(ticket)
        review = review_execution(self.store, ticket_for_review, packet, execution)
        self.store.save_review_report(review)
        review_artifact = self.store.write_artifact(
            ticket.id,
            review_run.id,
            ArtifactType.REVIEW_REPORT,
            "review_report.json",
            review.model_dump_json(indent=2) + "\n",
            f"Reviewer verdict: {review.verdict.value}",
            metadata={"review_report_id": review.id},
        )
        self.store.append_run_message(
            review_run.id,
            "review_report",
            RunMessageType.ARTIFACT,
            f"Wrote review report with verdict {review.verdict.value}.",
            artifact_ref=review_artifact.id,
            result_ref=review.id,
            metadata={"path": review_artifact.path},
        )
        review_run = _finish_run(
            self.store,
            review_run,
            AgentRunStatus.SUCCEEDED,
            f"Reviewer verdict: {review.verdict.value}.",
            [review_artifact.id],
        )
        try:
            from ariadne_ltb.knowledge import reflect_on_run

            reflect_on_run(self.store, run=review_run, review=review)
        except Exception:
            pass
        ticket = self.store.load_ticket(ticket.id).with_run(review_run.id).with_artifacts([review_artifact])
        ticket = ticket.append_event(
            "review_finished",
            "Reviewer",
            f"Reviewer verdict: {review.verdict.value}.",
            payload_ref=review_artifact.id,
        )
        self._progress(
            ticket,
            "review",
            "succeeded",
            f"Reviewer verdict: {review.verdict.value}.",
            payload_ref=review_artifact.id,
            kind=CommentKind.REVIEW,
        )
        ticket = ticket.model_copy(
            deep=True,
            update={"metadata": ticket.metadata | {"review_report_id": review.id}},
        )
        if review.verdict is ReviewVerdict.NEEDS_FIX:
            record_handoff(
                self.store,
                ticket,
                self.runtime_id,
                "Reviewer",
                "Execution",
                "Reviewer requested a fix.",
                self.assignment_id,
                payload_ref=review_artifact.id,
                status=HandoffStatus.BLOCKED,
            )
        else:
            record_handoff(
                self.store,
                ticket,
                self.runtime_id,
                "Reviewer",
                "Memory",
                f"Reviewer verdict={review.verdict.value}.",
                self.assignment_id,
                payload_ref=review_artifact.id,
            )
        ticket = ticket.with_status(_status_for_review(review.verdict), "Reviewer")
        self.store.save_ticket(ticket)

        memory_run = _start_run(
            self.store,
            ticket,
            "Memory / Feishu",
            "memory_feishu",
            assignment_id=self.assignment_id,
            runtime_id=self.runtime_id,
        )
        memory, memory_path = write_memory_record(self.store, ticket, packet, execution, review)
        feishu_plan, feishu_path = generate_feishu_plan(self.store, ticket, packet, execution, review)
        memory_artifact = _write_memory_artifact(self.store, ticket.id, memory_run.id, memory, memory_path)
        feishu_artifact = _write_feishu_artifact(self.store, ticket.id, memory_run.id, feishu_plan, feishu_path)
        self.store.append_run_message(
            memory_run.id,
            "memory",
            RunMessageType.ARTIFACT,
            "Wrote local memory record.",
            artifact_ref=memory_artifact.id,
            result_ref=memory.id,
            metadata={"path": memory_artifact.path, "memory_path": str(memory_path)},
        )
        self.store.append_run_message(
            memory_run.id,
            "feishu_plan",
            RunMessageType.ARTIFACT,
            "Wrote Feishu preview plan.",
            artifact_ref=feishu_artifact.id,
            result_ref=feishu_plan.id,
            metadata={"path": feishu_artifact.path, "feishu_plan_path": str(feishu_path)},
        )
        ticket = self.store.load_ticket(ticket.id).append_event(
            "memory_written",
            "Memory / Feishu",
            "Wrote local memory and Feishu preview plan.",
            payload_ref=memory_artifact.id,
        )
        self.store.save_ticket(ticket)
        self._progress(
            ticket,
            "memory",
            "succeeded",
            "Memory wrote decision log and Feishu preview plan.",
            payload_ref=memory_artifact.id,
            kind=CommentKind.MEMORY,
        )
        next_tickets_artifact = generate_next_tickets_artifact(
            self.store,
            ticket,
            packet,
            execution,
            review,
            memory_run.id,
        )
        backlog_next_tickets_path = next_tickets_artifact.path
        backlog_planner_artifact = None
        if backlog_planner == "llm":
            llm_backlog = generate_llm_backlog_artifact(
                self.store,
                ticket,
                packet,
                execution,
                review,
                memory_run.id,
                next_tickets_artifact.path,
                client=backlog_planner_client,
            )
            backlog_planner_artifact = llm_backlog.artifact
            backlog_next_tickets_path = llm_backlog.effective_next_tickets_path
            self.store.append_run_message(
                memory_run.id,
                "llm_backlog_planner",
                RunMessageType.ARTIFACT if llm_backlog.succeeded else RunMessageType.ERROR,
                (
                    "LLM backlog planner generated ticket delta suggestions."
                    if llm_backlog.succeeded
                    else f"LLM backlog planner blocked: {llm_backlog.error}"
                ),
                artifact_ref=llm_backlog.artifact.id,
                metadata={
                    "path": llm_backlog.artifact.path,
                    "fallback_next_tickets_path": next_tickets_artifact.path,
                    "effective_next_tickets_path": backlog_next_tickets_path,
                    "succeeded": llm_backlog.succeeded,
                },
            )
            ticket = (
                self.store.load_ticket(ticket.id)
                .with_artifacts([llm_backlog.artifact])
                .append_event(
                    "llm_backlog_planner_finished",
                    "Memory / Feishu",
                    (
                        "LLM backlog planner generated ticket delta suggestions."
                        if llm_backlog.succeeded
                        else "LLM backlog planner blocked; deterministic backlog suggestions remain in use."
                    ),
                    payload_ref=llm_backlog.artifact.id,
                )
            )
            self.store.save_ticket(ticket)
        elif backlog_planner != "deterministic":
            msg = f"unknown backlog planner: {backlog_planner}"
            raise ValueError(msg)
        self.store.append_run_message(
            memory_run.id,
            "next_tickets",
            RunMessageType.ARTIFACT,
            "Generated next Build Ticket suggestions.",
            artifact_ref=next_tickets_artifact.id,
            metadata={"path": next_tickets_artifact.path},
        )
        record_handoff(
            self.store,
            ticket,
            self.runtime_id,
            "Memory",
            "Build Lead",
            "Memory and next tickets are written.",
            self.assignment_id,
            payload_ref=next_tickets_artifact.id,
        )
        ticket = self.store.load_ticket(ticket.id).append_event(
            "next_tickets_generated",
            "Memory / Feishu",
            "Generated follow-up Build Ticket suggestions.",
            payload_ref=next_tickets_artifact.id,
        )
        self.store.save_ticket(ticket)
        final_status = TicketStatus.DONE if review.verdict is ReviewVerdict.PASS else _status_for_review(review.verdict)
        ticket = (
            self.store.load_ticket(ticket.id)
            .with_run(memory_run.id)
            .with_artifacts([memory_artifact, feishu_artifact, next_tickets_artifact])
            .with_status(final_status, "Memory / Feishu")
        )
        ticket = ticket.model_copy(
            deep=True,
            update={
                "metadata": ticket.metadata
                | {
                    "memory_record_id": memory.id,
                    "memory_path": str(memory_path),
                    "feishu_write_plan_id": feishu_plan.id,
                    "feishu_plan_path": str(feishu_path),
                    "next_tickets_path": next_tickets_artifact.path,
                    "backlog_planner_name": backlog_planner,
                    "backlog_planner_artifact_path": backlog_planner_artifact.path
                    if backlog_planner_artifact
                    else None,
                    "backlog_next_tickets_path": backlog_next_tickets_path,
                    "selected_for_execution": True,
                    "backend_name": backend_name,
                    "external_execution_enabled": __import__("os").environ.get(
                        "ARIADNE_ENABLE_EXTERNAL_EXECUTION"
                    )
                    == "1",
                },
            },
        )
        self.store.save_ticket(ticket)
        self._progress(
            ticket,
            "next_tickets",
            "succeeded",
            "Generated next Build Ticket suggestions.",
            payload_ref=next_tickets_artifact.id,
        )
        memory_preview = generate_memory_gap_preview(
            self.store,
            ticket,
            packet,
            execution,
            review,
            memory.id,
            backlog_next_tickets_path,
        )
        memory_preview_result = apply_backlog_preview(self.store, memory_preview.id)
        backlog_preview_ids.append(memory_preview.id)
        if memory_preview_result.update:
            applied_preview_update_ids.append(memory_preview_result.update.id)
        codebase_preview = generate_codebase_observation_preview(
            self.store,
            self.store.load_ticket(ticket.id),
            packet,
            execution,
            review,
            backlog_next_tickets_path,
        )
        codebase_preview_result = apply_backlog_preview(self.store, codebase_preview.id)
        backlog_preview_ids.append(codebase_preview.id)
        if codebase_preview_result.update:
            applied_preview_update_ids.append(codebase_preview_result.update.id)
        review_preview = generate_review_feedback_preview(self.store, self.store.load_ticket(ticket.id), review)
        review_preview_result = apply_backlog_preview(self.store, review_preview.id)
        backlog_preview_ids.append(review_preview.id)
        if review_preview_result.update:
            applied_preview_update_ids.append(review_preview_result.update.id)
        backlog_update_ids = list(applied_preview_update_ids)
        current_backlog_updates = [
            update for update in self.store.list_backlog_updates() if update.id in backlog_update_ids
        ]
        ticket = self.store.load_ticket(ticket.id)
        self.store.append_run_message(
            memory_run.id,
            "backlog_update",
            RunMessageType.RESULT,
            "Recorded feedback-driven backlog updates.",
            metadata={
                "backlog_preview_ids": backlog_preview_ids,
                "backlog_update_ids": backlog_update_ids,
                "created_ticket_ids": [
                    ticket_id
                    for update in current_backlog_updates
                    for ticket_id in update.created_ticket_ids
                ],
                "updated_ticket_ids": [
                    ticket_id
                    for update in current_backlog_updates
                    for ticket_id in update.updated_ticket_ids
                ],
            },
        )
        self._progress(
            ticket,
            "backlog_update",
            "succeeded",
            f"Recorded {len(backlog_update_ids)} feedback-driven backlog update(s) from applied previews.",
            payload_ref=",".join(backlog_update_ids),
        )
        if agent_runtime == "llm":
            memory_role_result = run_ticket_llm_agent(
                self.store,
                self.store.load_ticket(ticket.id),
                LLMAgentRole.MEMORY,
                client=llm_agent_client,
            )
            if memory_role_result.artifact_path:
                llm_agent_artifact_paths.append(memory_role_result.artifact_path)
            ticket = self.store.load_ticket(ticket.id)
            self._progress(
                ticket,
                "llm_memory",
                "succeeded" if memory_role_result.succeeded else "blocked",
                (
                    "DeepSeek Memory role completed."
                    if memory_role_result.succeeded
                    else f"DeepSeek Memory role blocked: {memory_role_result.error}"
                ),
                payload_ref=memory_role_result.artifact_id,
            )
            self._require_llm_role_success(ticket, memory_role_result)
        memory_run = _finish_run(
            self.store,
            memory_run,
            AgentRunStatus.SUCCEEDED,
            "Wrote local memory, Feishu preview plan, next ticket suggestions, and backlog updates.",
            [
                memory_artifact.id,
                feishu_artifact.id,
                next_tickets_artifact.id,
                *([backlog_planner_artifact.id] if backlog_planner_artifact else []),
            ],
        )
        board_path = _export_board_if_not_daemon_assignment(self.store, self.assignment_id)
        ticket = self.store.load_ticket(ticket.id).append_event(
            "board_exported",
            "Build Board",
            f"Exported board to {board_path}.",
            payload_ref=str(board_path),
        )
        self.store.save_ticket(ticket)
        manifest_artifact = _write_orchestrator_result_artifact(
            self.store,
            ticket.id,
            memory_run.id,
            {
                "ticket_id": ticket.id,
                "ticket_key": ticket.key,
                "backend_name": backend_name,
                "planner_name": planner,
                "agent_runtime": agent_runtime,
                "build_packet_id": packet.id,
                "handoff_artifact_id": handoff_artifact.id,
                "execution_result_id": execution.id,
                "review_report_id": review.id,
                "review_verdict": review.verdict.value,
                "permission_profile_id": permission_profile.id,
                "skill_bundle_artifact_id": skill_bundle_artifact.id,
                "changed_files": execution.changed_files,
                "test_command": execution.test_command,
                "test_exit_code": execution.test_exit_code,
                "memory_record_id": memory.id,
                "feishu_plan_id": feishu_plan.id,
                "backlog_planner_name": backlog_planner,
                "backlog_planner_artifact_id": backlog_planner_artifact.id
                if backlog_planner_artifact
                else None,
                "backlog_next_tickets_path": backlog_next_tickets_path,
                "llm_agent_artifact_paths": llm_agent_artifact_paths,
                "backlog_preview_ids": backlog_preview_ids,
                "backlog_update_ids": backlog_update_ids,
                "board_path": str(board_path),
                "board_html_path": str(self.store.board_dir / "index.html"),
                "worktree_path": worktree_path,
                "external_execution_enabled": os.environ.get("ARIADNE_ENABLE_EXTERNAL_EXECUTION") == "1",
                "confirm_execution": confirm_execution,
                "artifacts": {
                    "memory_path": str(memory_path),
                    "feishu_plan_path": str(feishu_path),
                    "next_tickets_path": next_tickets_artifact.path,
                    "backlog_planner_artifact_path": backlog_planner_artifact.path
                    if backlog_planner_artifact
                    else None,
                    "backlog_next_tickets_path": backlog_next_tickets_path,
                    "llm_agent_artifact_paths": llm_agent_artifact_paths,
                    "board_path": str(board_path),
                    "permission_profile_path": permission_artifact.path,
                    "skill_bundle_path": skill_bundle_artifact.path,
                    "provider_skill_dir": skill_materializations[0].provider_skill_dir
                    if skill_materializations
                    else "",
                },
            },
        )
        landing_json_artifact, landing_md_artifact = _write_landing_evidence_artifacts(
            self.store,
            ticket,
            memory_run.id,
            backend_name=backend_name,
            planner_name=planner,
            agent_runtime=agent_runtime,
            backlog_planner_name=backlog_planner,
            target_repo=target_repo,
            worktree_path=worktree_path,
            execution=execution,
            review_id=review.id,
            review_verdict=review.verdict,
            memory_path=str(memory_path),
            board_path=str(board_path),
            next_tickets_path=next_tickets_artifact.path,
            feishu_plan_path=str(feishu_path),
            orchestrator_result_path=manifest_artifact.path,
            linked_artifacts={
                "execution_log": execution_artifacts["execution_log"],
                "git_diff": execution_artifacts["git_diff"],
                "changed_files": execution_artifacts["changed_files"],
                "test_output": execution_artifacts["test_output"],
                "review_report": review_artifact,
                "memory_record": memory_artifact,
                "next_tickets": next_tickets_artifact,
                "feishu_plan": feishu_artifact,
                "orchestrator_result": manifest_artifact,
            },
        )
        ticket = (
            self.store.load_ticket(ticket.id)
            .with_artifacts([manifest_artifact, landing_json_artifact, landing_md_artifact])
            .append_event(
                "orchestrator_result_written",
                "Build Lead",
                "Wrote structured ticket run result manifest.",
                payload_ref=manifest_artifact.id,
            )
            .append_event(
                "landing_evidence_written",
                "Build Lead",
                "Wrote ticket landing evidence packet.",
                payload_ref=landing_json_artifact.id,
            )
            .model_copy(
                deep=True,
                update={
                    "metadata": self.store.load_ticket(ticket.id).metadata
                    | {
                        "orchestrator_result_artifact_id": manifest_artifact.id,
                        "orchestrator_result_path": manifest_artifact.path,
                        "landing_evidence_json_artifact_id": landing_json_artifact.id,
                        "landing_evidence_md_artifact_id": landing_md_artifact.id,
                        "landing_evidence_json_path": landing_json_artifact.path,
                        "landing_evidence_md_path": landing_md_artifact.path,
                    }
                },
            )
        )
        self.store.save_ticket(ticket)
        self._progress(
            ticket,
            "board",
            "succeeded",
            f"Board path recorded at {board_path}.",
            payload_ref=str(board_path),
        )
        return TicketRunResult(
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            backend_name=backend_name,
            planner_name=planner,
            agent_runtime=agent_runtime,
            build_packet_id=packet.id,
            handoff_artifact_id=handoff_artifact.id,
            execution_result_id=execution.id,
            review_report_id=review.id,
            review_verdict=review.verdict.value,
            changed_files=execution.changed_files,
            test_exit_code=execution.test_exit_code,
            memory_record_id=memory.id,
            memory_path=str(memory_path),
            feishu_plan_id=feishu_plan.id,
            feishu_plan_path=str(feishu_path),
            next_tickets_path=next_tickets_artifact.path,
            backlog_planner_name=backlog_planner,
            backlog_planner_artifact_path=backlog_planner_artifact.path
            if backlog_planner_artifact
            else None,
            llm_agent_artifact_paths=llm_agent_artifact_paths,
            backlog_preview_ids=backlog_preview_ids,
            backlog_update_ids=backlog_update_ids,
            board_path=str(board_path),
            board_html_path=str(self.store.board_dir / "index.html"),
            orchestrator_result_path=manifest_artifact.path,
            landing_evidence_json_path=landing_json_artifact.path,
            landing_evidence_md_path=landing_md_artifact.path,
            worktree_path=worktree_path,
        )

    def _progress(
        self,
        ticket,
        stage: str,
        event_type: str,
        body: str,
        payload_ref: str | None = None,
        kind: CommentKind = CommentKind.PROGRESS,
    ) -> None:
        current = self.store.load_ticket(ticket.id)
        self.store.add_comment(
            current,
            CommentAuthorType.AGENT,
            self.actor_name,
            kind,
            body,
            payload_ref=payload_ref,
            thread_id=self.assignment_id,
        )
        self.store.append_runtime_event(
            event := runtime_event(
                current,
                self.runtime_id,
                stage,
                event_type,
                self.actor_name,
                assignment_id=self.assignment_id,
                payload_ref=payload_ref,
            )
        )
        self._heartbeat(current, stage, event.id, event_type)

    def _load_assignment_handoff_packet(self) -> HandoffPacket | None:
        if not self.assignment_id:
            return None
        try:
            assignment = self.store.load_assignment(self.assignment_id)
        except FileNotFoundError:
            return None
        packet_id = assignment.metadata.get("handoff_packet_id")
        if not packet_id:
            return None
        return self.store.load_handoff_packet(str(packet_id))

    def _heartbeat(self, ticket, stage: str, event_id: str, event_type: str) -> None:  # type: ignore[no-untyped-def]
        try:
            existing = self.store.load_worker_heartbeat(self.runtime_id)
            started_at = existing.started_at
        except FileNotFoundError:
            started_at = utc_now()
        status = DaemonStatus.RUNNING
        if event_type == "blocked":
            status = DaemonStatus.BLOCKED
        elif event_type == "failed":
            status = DaemonStatus.FAILED
        self.store.save_worker_heartbeat(
            WorkerHeartbeat(
                runtime_id=self.runtime_id,
                pid=os.getpid(),
                status=status,
                current_assignment_id=self.assignment_id,
                current_ticket_id=ticket.id,
                current_ticket_key=ticket.key,
                current_stage=stage,
                started_at=started_at,
                heartbeat_at=utc_now(),
                last_event_id=event_id,
            )
        )

    def _require_llm_role_success(self, ticket: BuildTicket, result: LLMAgentResult) -> None:
        if result.succeeded:
            return
        msg = result.error or "unknown LLM role failure"
        if _llm_role_failure_can_fallback(msg):
            self._progress(
                ticket,
                f"llm_{result.role.value}",
                "fallback",
                f"DeepSeek {result.role.value.replace('_', ' ')} role returned unusable structured output; continuing with deterministic fallback.",
                payload_ref=result.artifact_id,
            )
            return
        board_path = export_board(self.store)
        role_name = result.role.value.replace("_", " ")
        raise RuntimeError(
            f"DeepSeek {role_name} role blocked for {ticket.key}: {msg}; board: {board_path}"
        )


def _start_run(
    store: AriadneStore,
    ticket,
    agent_name: str,
    agent_role: str,
    backend_name: str | None = None,
    assignment_id: str | None = None,
    runtime_id: str | None = None,
) -> AgentRun:
    for run_id in ticket.agent_run_ids:
        existing = store.load_run(run_id)
        if existing.agent_role == agent_role and not existing.is_terminal:
            store.save_run(
                existing.mark_finished(
                    AgentRunStatus.FAILED,
                    f"Superseded by a new {agent_role} attempt.",
                    "Previous attempt did not reach a terminal state.",
                )
            )
    attempt = 1 + sum(
        1 for run_id in ticket.agent_run_ids if store.load_run(run_id).agent_role == agent_role
    )
    run = AgentRun(
        id=stable_id("run", ticket.id, agent_role, attempt),
        ticket_id=ticket.id,
        agent_name=agent_name,
        agent_role=agent_role,
        input_summary=f"{agent_name} for {ticket.key}.",
        attempt=attempt,
        backend_name=backend_name,
        runtime_id=runtime_id,
        metadata={
            key: value
            for key, value in {
                "assignment_id": assignment_id,
                "runtime_id": runtime_id,
            }.items()
            if value
        },
    ).mark_running()
    store.save_run(run)
    store.reset_run_messages(run.id)
    store.append_run_message(
        run.id,
        "start",
        RunMessageType.STATUS,
        f"{agent_name} started for {ticket.key}.",
        metadata={"agent_role": agent_role, "attempt": attempt, "backend_name": backend_name},
    )
    updated = ticket.with_run(run.id).append_event(
        "agent_run_started",
        agent_name,
        f"{agent_name} started.",
        payload_ref=run.id,
    )
    store.save_ticket(updated)
    return run


def _finish_run(
    store: AriadneStore,
    run: AgentRun,
    status: AgentRunStatus,
    summary: str,
    artifact_ids: list[str],
    failure_reason: FailureReason | None = None,
) -> AgentRun:
    finished = run.model_copy(update={"artifact_ids": artifact_ids}).mark_finished(
        status,
        summary,
        failure_reason=failure_reason,
    )
    store.save_run(finished)
    try:
        from ariadne_ltb.knowledge import reflect_on_run

        reflect_on_run(store, run=finished, review=None)
    except Exception:
        pass
    store.append_run_message(
        finished.id,
        "finish",
        RunMessageType.RESULT,
        summary,
        metadata={
            "status": status.value,
            "failure_reason": failure_reason.value if failure_reason else None,
            "artifact_ids": artifact_ids,
        },
    )
    return finished


def _blocked_execution(
    context: ExecutionContext,
    backend_name: str,
    reason: str,
    failure_reason: FailureReason,
) -> ExecutionResult:
    repo = Path(context.target_repo_path)
    started = utc_now()
    status = git_status(repo)
    return ExecutionResult(
        id=stable_id("execution", context.ticket_id, backend_name, failure_reason.value, reason),
        ticket_id=context.ticket_id,
        backend_name=backend_name,
        target_repo_path=context.target_repo_path,
        target_worktree_path=context.target_worktree_path,
        dry_run=False,
        blocked=True,
        block_reason=reason,
        failure_reason=failure_reason,
        command=context.command,
        exit_code=2,
        stderr=reason,
        started_at=started,
        ended_at=utc_now(),
        git_head_before=git_head(repo),
        git_head_after=git_head(repo),
        git_status_before=status,
        git_status_after=status,
        changed_files=[],
        git_diff="",
        test_command=context.test_command,
        test_exit_code=None,
        warnings=[reason],
        assignment_id=context.assignment_id,
        run_id=context.run_id,
    )


def _llm_role_failure_can_fallback(error: str) -> bool:
    normalized = error.lower()
    external_blockers = [
        "api_key",
        "api key",
        "unauthorized",
        "authentication",
        "quota",
        "rate limit",
        "billing",
        "transport_error",
        "timeout",
    ]
    if any(token in normalized for token in external_blockers):
        return False
    fallback_errors = [
        "valid json",
        "json",
        "schema validation",
        "invalid_response",
        "failed schema",
    ]
    return any(token in normalized for token in fallback_errors)


def _export_board_if_not_daemon_assignment(store: AriadneStore, assignment_id: str | None) -> str:
    _ = assignment_id
    return str(export_board(store))


def _augment_handoff_with_project_resources(
    handoff_prompt: str,
    project_resources: list[ProjectResource],
    target_repo: Path,
    worktree_path: str | None,
) -> str:
    lines = [
        "## Project Resources",
        "",
        f"Target repo path: `{target_repo}`",
    ]
    if worktree_path:
        lines.append(f"Target worktree path: `{worktree_path}`")
    lines.append("")
    for resource in project_resources:
        ref = resource.resource_ref
        label = resource.label or ref.get("label") or resource.resource_type
        local_path = ref.get("local_path")
        lines.append(f"- ProjectResource `{resource.id}` ({label}): `{local_path}`")
    section = "\n".join(lines) + "\n\n"
    marker = "\n## Safety Constraints\n"
    if marker in handoff_prompt:
        return handoff_prompt.replace(marker, f"\n{section}## Safety Constraints\n", 1)
    return handoff_prompt.rstrip() + "\n\n" + section


def _write_execution_artifacts(
    store: AriadneStore,
    run_id: str,
    execution: ExecutionResult,
) -> dict[str, Artifact]:
    log = store.write_artifact(
        execution.ticket_id,
        run_id,
        ArtifactType.EXECUTION_LOG,
        "execution_log.json",
        execution.model_dump_json(indent=2) + "\n",
        "Execution stdout/stderr/exit code capture",
        metadata={"execution_result_id": execution.id},
    )
    diff = store.write_artifact(
        execution.ticket_id,
        run_id,
        ArtifactType.GIT_DIFF,
        "git_diff.patch",
        execution.git_diff or "",
        "Target project git diff",
        metadata={"execution_result_id": execution.id},
    )
    changed = store.write_artifact(
        execution.ticket_id,
        run_id,
        ArtifactType.CHANGED_FILES,
        "changed_files.json",
        json.dumps(execution.changed_files, indent=2) + "\n",
        "Changed file list",
        metadata={"execution_result_id": execution.id},
    )
    tests = store.write_artifact(
        execution.ticket_id,
        run_id,
        ArtifactType.TEST_OUTPUT,
        "test_output.json",
        json.dumps(
            {
                "test_command": execution.test_command,
                "test_exit_code": execution.test_exit_code,
                "test_stdout": execution.test_stdout,
                "test_stderr": execution.test_stderr,
            },
            indent=2,
        )
        + "\n",
        "Target project test output",
        metadata={"execution_result_id": execution.id},
    )
    for stage, artifact in {
        "execution_log": log,
        "git_diff": diff,
        "changed_files": changed,
        "test_output": tests,
    }.items():
        store.append_run_message(
            run_id,
            stage,
            RunMessageType.ARTIFACT,
            f"Wrote {artifact.artifact_type.value}: {artifact.summary}.",
            artifact_ref=artifact.id,
            result_ref=execution.id,
            metadata={"path": artifact.path},
        )
    store.append_run_message(
        run_id,
        "execution_result",
        RunMessageType.RESULT,
        _execution_summary(execution),
        result_ref=execution.id,
        metadata={
            "exit_code": execution.exit_code,
            "test_exit_code": execution.test_exit_code,
            "blocked": execution.blocked,
            "changed_files": execution.changed_files,
        },
    )
    return {
        "execution_log": log,
        "git_diff": diff,
        "changed_files": changed,
        "test_output": tests,
    }


def _write_orchestrator_result_artifact(
    store: AriadneStore,
    ticket_id: str,
    agent_run_id: str,
    payload: dict,
) -> Artifact:
    return store.write_artifact(
        ticket_id,
        agent_run_id,
        ArtifactType.ORCHESTRATOR_RESULT,
        "orchestrator_result.json",
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        "Structured ticket run result manifest",
        metadata={
            "execution_result_id": str(payload.get("execution_result_id", "")),
            "review_report_id": str(payload.get("review_report_id", "")),
        },
    )


def _write_landing_evidence_artifacts(
    store: AriadneStore,
    ticket: BuildTicket,
    agent_run_id: str,
    *,
    backend_name: str,
    planner_name: str,
    agent_runtime: str,
    backlog_planner_name: str,
    target_repo: Path,
    worktree_path: str | None,
    execution: ExecutionResult,
    review_id: str,
    review_verdict: ReviewVerdict,
    memory_path: str,
    board_path: str,
    next_tickets_path: str,
    feishu_plan_path: str,
    orchestrator_result_path: str,
    linked_artifacts: dict[str, Artifact],
) -> tuple[Artifact, Artifact]:
    missing_fields = [
        name
        for name, value in {
            "memory_path": memory_path,
            "board_path": board_path,
            "next_tickets_path": next_tickets_path,
            "feishu_plan_path": feishu_plan_path,
            "orchestrator_result_path": orchestrator_result_path,
        }.items()
        if not value
    ]
    execution_failed = execution.exit_code != 0 or (
        execution.test_exit_code is not None and execution.test_exit_code != 0
    )
    evidence = LandingEvidence(
        id=stable_id("landing_evidence", ticket.id, execution.id, review_id),
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        ticket_title=ticket.title,
        ticket_status=ticket.status,
        backend_name=backend_name,
        planner_name=planner_name,
        agent_runtime=agent_runtime,
        backlog_planner_name=backlog_planner_name,
        branch=git_branch(target_repo),
        target_repo_path=str(target_repo),
        worktree_path=worktree_path,
        execution_result_id=execution.id,
        review_report_id=review_id,
        review_verdict=review_verdict,
        changed_files=execution.changed_files,
        git_diff_summary=_summarize_diff(execution.git_diff),
        test_results=[
            LandingTestResult(
                command=execution.test_command,
                exit_code=execution.test_exit_code,
                status=_test_status(execution),
                output_artifact_path=linked_artifacts.get("test_output").path
                if linked_artifacts.get("test_output")
                else None,
            )
        ]
        if execution.test_command
        else [],
        memory_path=memory_path,
        board_path=board_path,
        next_tickets_path=next_tickets_path,
        feishu_plan_path=feishu_plan_path,
        orchestrator_result_path=orchestrator_result_path,
        gate_inputs={
            "external_execution_enabled": os.environ.get("ARIADNE_ENABLE_EXTERNAL_EXECUTION") == "1",
            "confirm_execution_required": execution.backend_name in {"codex", "claude-code", "shell"},
            "blocked": execution.blocked,
            "execution_blocked": execution.blocked,
            "block_reason": execution.block_reason,
            "failure_reason": execution.failure_reason.value if execution.failure_reason else None,
            "execution_exit_code": execution.exit_code,
            "test_exit_code": execution.test_exit_code,
            "execution_failed": execution_failed,
            "review_verdict": review_verdict.value,
        },
        linked_artifacts=[
            LandingArtifactRef(
                kind=kind,
                artifact_id=artifact.id,
                path=artifact.path,
                summary=artifact.summary,
            )
            for kind, artifact in linked_artifacts.items()
        ],
        partial=execution.blocked
        or execution_failed
        or review_verdict is not ReviewVerdict.PASS
        or bool(missing_fields),
        missing_fields=missing_fields,
    )
    json_artifact = store.write_artifact(
        ticket.id,
        agent_run_id,
        ArtifactType.LANDING_EVIDENCE,
        "landing_evidence.json",
        evidence.model_dump_json(indent=2) + "\n",
        "Ticket landing evidence packet",
        metadata={
            "landing_evidence_id": evidence.id,
            "format": "json",
            "partial": evidence.partial,
            "review_verdict": review_verdict.value,
            "execution_result_id": execution.id,
        },
    )
    md_artifact = store.write_artifact(
        ticket.id,
        agent_run_id,
        ArtifactType.LANDING_EVIDENCE,
        "landing_evidence.md",
        _landing_evidence_markdown(evidence),
        "Ticket landing evidence summary",
        metadata={
            "landing_evidence_id": evidence.id,
            "format": "markdown",
            "partial": evidence.partial,
            "review_verdict": review_verdict.value,
            "json_artifact_id": json_artifact.id,
        },
    )
    return json_artifact, md_artifact


def _summarize_diff(diff: str) -> dict[str, object]:
    additions = 0
    deletions = 0
    files: set[str] = set()
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            files.add(line.removeprefix("+++ b/"))
        elif line.startswith("--- a/"):
            files.add(line.removeprefix("--- a/"))
        elif line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
    return {
        "files_changed": len(files),
        "additions": additions,
        "deletions": deletions,
        "raw_diff_embedded": False,
    }


def _test_status(execution: ExecutionResult) -> str:
    if execution.test_exit_code == 0:
        return "passed"
    if execution.test_exit_code is None:
        return "not_run"
    return "failed"


def _landing_evidence_markdown(evidence: LandingEvidence) -> str:
    tests = "\n".join(
        f"- `{test.command}`: `{test.status}` exit=`{test.exit_code}`"
        for test in evidence.test_results
    )
    artifacts = "\n".join(
        f"- `{artifact.kind}`: `{artifact.path}`" for artifact in evidence.linked_artifacts
    )
    return f"""# Landing Evidence: {evidence.ticket_key}

- Ticket: `{evidence.ticket_key}` {evidence.ticket_title}
- Backend: `{evidence.backend_name}`
- Planner: `{evidence.planner_name}`
- Review: `{evidence.review_verdict.value}`
- Partial: `{str(evidence.partial).lower()}`
- Branch: `{evidence.branch or 'unknown'}`
- Worktree: `{evidence.worktree_path or evidence.target_repo_path}`

## Changed Files

{_markdown_bullets(evidence.changed_files)}

## Diff Summary

- Files changed: `{evidence.git_diff_summary.get('files_changed', 0)}`
- Additions: `{evidence.git_diff_summary.get('additions', 0)}`
- Deletions: `{evidence.git_diff_summary.get('deletions', 0)}`

## Tests

{tests or '- No test command recorded.'}

## Required Evidence

- Memory: `{evidence.memory_path}`
- Board: `{evidence.board_path}`
- Feishu plan: `{evidence.feishu_plan_path}`
- Next tickets: `{evidence.next_tickets_path}`
- Orchestrator result: `{evidence.orchestrator_result_path or 'missing'}`

## Missing Fields

{_markdown_bullets(evidence.missing_fields) if evidence.missing_fields else '- None'}

## Linked Artifacts

{artifacts or '- None'}
"""


def _markdown_bullets(values: list[str]) -> str:
    if not values:
        return "- None"
    return "\n".join(f"- `{value}`" for value in values)


def _write_memory_artifact(
    store: AriadneStore,
    ticket_id: str,
    run_id: str,
    memory: MemoryRecord,
    path: Path,
) -> Artifact:
    return store.write_artifact(
        ticket_id,
        run_id,
        ArtifactType.MEMORY_RECORD,
        "memory_record.json",
        memory.model_dump_json(indent=2) + "\n",
        "Local memory write-back record",
        metadata={"memory_record_id": memory.id, "memory_path": str(path)},
    )


def _write_feishu_artifact(
    store: AriadneStore,
    ticket_id: str,
    run_id: str,
    plan: FeishuWritePlan,
    path: Path,
) -> Artifact:
    return store.write_artifact(
        ticket_id,
        run_id,
        ArtifactType.FEISHU_WRITE_PLAN,
        "feishu_write_plan.json",
        plan.model_dump_json(indent=2) + "\n",
        "Feishu preview write plan",
        metadata={"feishu_write_plan_id": plan.id, "path": str(path), "dry_run": True},
    )


def _status_for_review(verdict: ReviewVerdict) -> TicketStatus:
    return {
        ReviewVerdict.PASS: TicketStatus.WRITING_MEMORY,
        ReviewVerdict.NEEDS_FIX: TicketStatus.NEEDS_FIX,
        ReviewVerdict.BLOCKED: TicketStatus.BLOCKED,
        ReviewVerdict.NEEDS_HUMAN_REVIEW: TicketStatus.WAITING_APPROVAL,
    }[verdict]


def _execution_summary(execution: ExecutionResult) -> str:
    if execution.blocked:
        return f"Execution blocked: {execution.block_reason}"
    return (
        f"Execution exit {execution.exit_code}; tests {execution.test_exit_code}; "
        f"changed {', '.join(execution.changed_files) or 'no files'}."
    )
