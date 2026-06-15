from __future__ import annotations

import json

from ariadne_ltb.models import (
    AgentRun,
    Artifact,
    ArtifactType,
    BuildDecision,
    BuildPacket,
    Evidence,
    FeishuWritePlan,
    ReviewReport,
    ReviewVerdict,
    TicketStatus,
    stable_id,
)
from ariadne_ltb.runtime import AgentStepResult, RuntimeContext


def _artifact_by_type(context: RuntimeContext, artifact_type: ArtifactType) -> Artifact | None:
    for artifact_id in context.ticket.artifact_ids:
        artifact = context.store.load_artifact(artifact_id)
        if artifact.artifact_type is artifact_type:
            return artifact
    return None


def _append_unique(values: list[str], value: str) -> list[str]:
    return [existing for existing in values if existing != value] + [value]


class BuildLeadAgent:
    name = "Build Lead"
    role = "build_lead"

    def run(self, context: RuntimeContext, run: AgentRun) -> AgentStepResult:
        content = f"""# Lead Routing

Ticket: {context.ticket.key} - {context.ticket.title}

Decision: continue as a scoped Ariadne MVP `code_task`.

Routing:

- Learning Agent extracts architecture lessons from the source note.
- Knowledge Agent grounds the work in local ADR and templates.
- Repo Agent inspects the current repository structure.
- Planner Agent creates the Build Packet and coding-agent handoff.
- Execution backend remains dry-run only.
- Reviewer checks visible state and artifacts conservatively.
- Feishu Agent creates a dry-run memory write-back plan.

Safety:

- No external APIs.
- No real Feishu writes.
- No auto-commit, auto-push, or auto-merge.
"""
        artifact = context.store.write_artifact(
            context.ticket.id,
            run.id,
            ArtifactType.RESEARCH_SUMMARY,
            "lead_routing.md",
            content,
            "Build Lead routing decision",
        )
        return AgentStepResult(
            output_summary="Routed ticket to the deterministic MVP pipeline.",
            artifacts=[artifact],
            ticket_status=TicketStatus.ANALYZING,
        )


class LearningAgent:
    name = "Learning"
    role = "learning"

    def run(self, context: RuntimeContext, run: AgentRun) -> AgentStepResult:
        evidence = [
            Evidence(
                id=stable_id("evidence", context.ticket.id, "visible-work-carrier"),
                source_ref=context.ticket.source_ref,
                quote_or_summary="A Build Ticket acts as the visible work carrier for agent work.",
                location="Product decision",
                confidence=0.95,
            ),
            Evidence(
                id=stable_id("evidence", context.ticket.id, "dry-run-runtime"),
                source_ref=context.ticket.source_ref,
                quote_or_summary="The MVP should use a deterministic local runtime and dry-run backend.",
                location="Product decision",
                confidence=0.9,
            ),
        ]
        context.values["evidence"] = evidence
        content = """# Learning Summary

The Multica research note is useful because it makes agent collaboration visible
through work objects, assignments, runs, and status. Ariadne should not copy the
whole managed-agent platform. It should extract the issue/run/agent/board
pattern and specialize it for Learning-to-Build.

## Extracted Insights

- Build Ticket: visible work carrier and board card.
- Build Packet: structured knowledge-to-build object inside the ticket.
- Agent Run: one visible execution record per role.
- Artifact: reviewable output, not hidden agent chat.
- Local Runner: deterministic execution boundary for the MVP.
"""
        artifact = context.store.write_artifact(
            context.ticket.id,
            run.id,
            ArtifactType.RESEARCH_SUMMARY,
            "learning_summary.md",
            content,
            "Architecture insights extracted from the source note",
        )
        return AgentStepResult(
            output_summary="Extracted Multica-to-Ariadne architecture evidence.",
            artifacts=[artifact],
        )


class KnowledgeAgent:
    name = "Knowledge"
    role = "knowledge"

    def run(self, context: RuntimeContext, run: AgentRun) -> AgentStepResult:
        content = """# Knowledge Context

MVP historical context is local only:

- `docs/adr/ADR-0001-multica-architecture-extraction.md`
- `templates/BUILD_TICKET_TEMPLATE.md`
- `templates/CODEX_HANDOFF_TEMPLATE.md`
- `templates/REVIEW_REPORT_TEMPLATE.md`
- `templates/FEISHU_WRITE_PLAN_TEMPLATE.md`

Full vector retrieval, external crawlers, and Feishu reads are intentionally out
of scope. The existing seed ADR supports the decision to borrow Multica's
collaboration architecture without cloning the whole platform.
"""
        artifact = context.store.write_artifact(
            context.ticket.id,
            run.id,
            ArtifactType.RESEARCH_SUMMARY,
            "knowledge_context.md",
            content,
            "Local seed docs and templates used as MVP knowledge context",
        )
        return AgentStepResult(
            output_summary="Collected local ADR/template context.",
            artifacts=[artifact],
        )


class RepoAgent:
    name = "Repo"
    role = "repo"

    def run(self, context: RuntimeContext, run: AgentRun) -> AgentStepResult:
        root = context.store.root
        visible_entries = [
            path.name
            for path in sorted(root.iterdir(), key=lambda item: item.name)
            if path.name not in {".git", ".ariadne", ".pytest_cache", "__pycache__"}
        ]
        entry_list = "\n".join(f"- `{entry}`" for entry in visible_entries) or "- empty"
        content = f"""# Repository Context

Root: `{root}`

Visible top-level entries:

{entry_list}

Recommended module placement:

- `ariadne_ltb/models.py`: domain models and enums.
- `ariadne_ltb/storage.py`: JSON persistence and artifact writer.
- `ariadne_ltb/runtime.py`: deterministic local runner.
- `ariadne_ltb/agents.py`: deterministic agent nodes.
- `ariadne_ltb/board.py`: static board exporter.
- `ariadne_ltb/cli.py`: Typer CLI.
- `tests/`: model, storage, pipeline, reviewer, and CLI tests.
"""
        artifact = context.store.write_artifact(
            context.ticket.id,
            run.id,
            ArtifactType.REPO_CONTEXT,
            "repo_context.md",
            content,
            "Safe repository context inspection",
        )
        return AgentStepResult(output_summary="Inspected repository structure safely.", artifacts=[artifact])


class PlannerAgent:
    name = "Planner"
    role = "planner"

    def run(self, context: RuntimeContext, run: AgentRun) -> AgentStepResult:
        evidence = context.values.get("evidence") or [
            Evidence(
                id=stable_id("evidence", context.ticket.id, "fallback"),
                source_ref=context.ticket.source_ref,
                quote_or_summary="The source recommends a local deterministic Ticket Kernel.",
                location="Suggested MVP Build Ticket",
                confidence=0.8,
            )
        ]
        packet_id = stable_id("packet", context.ticket.id)
        packet = BuildPacket(
            id=packet_id,
            ticket_id=context.ticket.id,
            source_summary=(
                "The Multica note argues that agent work should be visible through "
                "ticket-like carriers, agent runs, artifacts, review, and board state."
            ),
            insight=(
                "Ariadne should start as a Mini-Multica-style Ticket Kernel that "
                "turns learning material into executable coding-agent context."
            ),
            evidence=evidence,
            project_relevance=(
                "This directly defines Ariadne v0.1: Build Ticket, Build Packet, "
                "Agent Run, Artifact, dry-run execution, conservative review, and board export."
            ),
            build_decision=BuildDecision.CODE_TASK,
            tasks=[
                "Implement Pydantic domain models for ProjectSpace, BuildTicket, BuildPacket, AgentRun, Artifact, ReviewReport, FeishuWritePlan, and BuildSkill.",
                "Implement JSON persistence under `.ariadne/` with artifact files under `.ariadne/artifacts/<ticket_id>/`.",
                "Implement deterministic local pipeline nodes for Build Lead, Learning, Knowledge, Repo, Planner, Execution Dry Run, Reviewer, and Feishu Plan.",
                "Expose Typer CLI commands for demo, ticket create/show/run, and static board export.",
                "Add tests and documentation for the MVP safety boundaries.",
            ],
            acceptance_criteria=[
                "`python -m ariadne_ltb.cli demo` creates ARI-001 and runs all eight nodes.",
                "Every Agent Run reaches a terminal status.",
                "Build Packet evidence and acceptance criteria are non-empty.",
                "Dry-run execution artifact states that no code was executed or committed.",
                "Feishu write plan is dry-run only.",
                "`.ariadne/board/index.md` shows ticket status, timeline, artifacts, review verdict, and Feishu summary.",
            ],
            affected_modules=[
                "ariadne_ltb/models.py",
                "ariadne_ltb/storage.py",
                "ariadne_ltb/runtime.py",
                "ariadne_ltb/agents.py",
                "ariadne_ltb/board.py",
                "ariadne_ltb/demo.py",
                "ariadne_ltb/cli.py",
                "tests/",
            ],
            risks=[
                "MVP reviewer cannot verify the final Feishu plan before the Feishu Plan node runs because the required pipeline orders Reviewer before Feishu Plan.",
                "Static markdown board is inspectable but not interactive.",
            ],
            assumptions=[
                "The demo uses deterministic rules instead of LLM calls.",
                "JSON storage is sufficient for the v0.1 single-project kernel.",
                "Reviewer treats the Feishu plan as a dry-run contract during the pipeline and the final Feishu Plan node writes the actual dry-run proposal.",
            ],
            confidence=0.9,
        )

        execution_plan = self._execution_plan(packet)
        plan_artifact = context.store.write_artifact(
            context.ticket.id,
            run.id,
            ArtifactType.EXECUTION_PLAN,
            "execution_plan.md",
            execution_plan,
            "Planner execution plan",
        )
        handoff = self._codex_handoff(packet)
        handoff_artifact = context.store.write_artifact(
            context.ticket.id,
            run.id,
            ArtifactType.CODEX_HANDOFF,
            "codex_handoff.md",
            handoff,
            "Coding-agent handoff prompt",
        )
        packet = packet.model_copy(
            deep=True,
            update={
                "coding_agent_handoff_id": handoff_artifact.id,
            },
        )
        context.store.save_build_packet(packet)
        packet_artifact = context.store.write_artifact(
            context.ticket.id,
            run.id,
            ArtifactType.BUILD_PACKET,
            "build_packet.json",
            packet.model_dump_json(indent=2) + "\n",
            "Structured Build Packet",
            metadata={"build_packet_id": packet.id},
        )
        context.values["build_packet"] = packet
        updated_ticket = context.ticket.model_copy(
            deep=True,
            update={"build_packet_id": packet.id},
        )
        context.store.save_ticket(updated_ticket)
        context.ticket = updated_ticket
        return AgentStepResult(
            output_summary="Created Build Packet, execution plan, and Codex handoff.",
            artifacts=[packet_artifact, plan_artifact, handoff_artifact],
            ticket_status=TicketStatus.PLANNING,
        )

    def _execution_plan(self, packet: BuildPacket) -> str:
        tasks = "\n".join(f"{index}. {task}" for index, task in enumerate(packet.tasks, start=1))
        criteria = "\n".join(f"- [ ] {item}" for item in packet.acceptance_criteria)
        return f"""# Execution Plan

## Goal

Implement the Ariadne v0.1 local deterministic Ticket Kernel.

## Tasks

{tasks}

## Acceptance Criteria

{criteria}

## Safety

Execution remains dry-run by default. No external APIs, Feishu writes, coding
agent execution, commits, pushes, merges, or PR creation are performed by the
MVP runtime.
"""

    def _codex_handoff(self, packet: BuildPacket) -> str:
        modules = "\n".join(f"- `{module}`" for module in packet.affected_modules)
        tasks = "\n".join(f"{index}. {task}" for index, task in enumerate(packet.tasks, start=1))
        criteria = "\n".join(f"- [ ] {item}" for item in packet.acceptance_criteria)
        return f"""# Codex Handoff

## Goal

Build the Ariadne local deterministic Ticket Kernel.

## Context

{packet.source_summary}

Insight: {packet.insight}

## Relevant files/modules

{modules}

## Constraints

- Do not expand scope.
- Do not call external APIs unless explicitly allowed.
- Do not auto-commit, auto-push, or auto-merge.
- Preserve dry-run safety.

## Implementation plan

{tasks}

## Acceptance criteria

{criteria}

## Test plan

```bash
pytest
python -m ariadne_ltb.cli demo
python -m ariadne_ltb.cli export board
```

## Expected output

A local `.ariadne/` workspace containing the demo ticket, terminal agent runs,
artifacts, review report, Feishu dry-run write plan, and static board export.

## Known non-goals

- Do not implement real Feishu API writes.
- Do not require real Codex runtime.
- Do not build a full web UI in MVP.
"""


class ExecutionDryRunAgent:
    name = "Execution Dry Run"
    role = "execution_dry_run"

    def run(self, context: RuntimeContext, run: AgentRun) -> AgentStepResult:
        handoff_artifact = _artifact_by_type(context, ArtifactType.CODEX_HANDOFF)
        handoff_path = handoff_artifact.path if handoff_artifact else "missing"
        content = f"""# Dry-run Execution

Dry-run: true

The local MVP backend simulated coding-agent execution only. It did not call
Codex, Claude Code, Cursor, Feishu, GitHub APIs, or any external service. It did
not commit, push, merge, or create a pull request.

## Handoff used

`{handoff_path}`

## Planned file changes

- Create `ariadne_ltb/models.py`
- Create `ariadne_ltb/storage.py`
- Create `ariadne_ltb/runtime.py`
- Create `ariadne_ltb/agents.py`
- Create `ariadne_ltb/board.py`
- Create `ariadne_ltb/demo.py`
- Create `ariadne_ltb/cli.py`
- Add tests under `tests/`
- Add README, ADR, templates, example note, and development report

## Test plan

```bash
pytest
python -m ariadne_ltb.cli demo
python -m ariadne_ltb.cli export board
```

## Result

No real code changes were made by this backend. The artifact is a reviewable
execution plan for a coding agent.
"""
        artifact = context.store.write_artifact(
            context.ticket.id,
            run.id,
            ArtifactType.DRY_RUN_EXECUTION,
            "dry_run_execution.md",
            content,
            "Dry-run execution backend output",
            metadata={"dry_run": True},
        )
        return AgentStepResult(
            output_summary="Produced dry-run execution artifact.",
            artifacts=[artifact],
            ticket_status=TicketStatus.CODING,
        )


class ReviewerAgent:
    name = "Reviewer"
    role = "reviewer"

    def run(self, context: RuntimeContext, run: AgentRun) -> AgentStepResult:
        review = self.evaluate(context)
        context.store.save_review_report(review)
        artifact = context.store.write_artifact(
            context.ticket.id,
            run.id,
            ArtifactType.REVIEW_REPORT,
            "review_report.json",
            review.model_dump_json(indent=2) + "\n",
            f"Reviewer verdict: {review.verdict.value}",
            metadata={"review_report_id": review.id},
        )
        status = TicketStatus.REVIEWING
        if review.verdict is ReviewVerdict.NEEDS_FIX:
            status = TicketStatus.NEEDS_FIX
        elif review.verdict is ReviewVerdict.BLOCKED:
            status = TicketStatus.BLOCKED
        return AgentStepResult(
            output_summary=f"Reviewer verdict: {review.verdict.value}.",
            artifacts=[artifact],
            ticket_status=status,
            metadata={"review_report_id": review.id},
        )

    def evaluate(self, context: RuntimeContext) -> ReviewReport:
        passed: list[str] = []
        failed: list[str] = []
        warnings: list[str] = []
        required_fixes: list[str] = []

        packet = None
        if context.ticket.build_packet_id:
            try:
                packet = context.store.load_build_packet(context.ticket.build_packet_id)
                passed.append("Build Packet exists")
            except FileNotFoundError:
                failed.append("Build Packet metadata is missing")
        else:
            failed.append("Build Packet exists")

        if packet and packet.evidence:
            passed.append("Evidence exists")
        else:
            failed.append("Evidence exists")
            required_fixes.append("Add evidence to the Build Packet.")

        if packet and packet.acceptance_criteria:
            passed.append("Acceptance criteria exist")
        else:
            failed.append("Acceptance criteria exist")
            required_fixes.append("Add acceptance criteria to the Build Packet.")

        codex_handoff = _artifact_by_type(context, ArtifactType.CODEX_HANDOFF)
        if codex_handoff:
            passed.append("Codex handoff exists")
        else:
            failed.append("Codex handoff exists")
            required_fixes.append("Generate a Codex handoff artifact.")

        dry_run = _artifact_by_type(context, ArtifactType.DRY_RUN_EXECUTION)
        if dry_run and "dry-run" in context.store.read_artifact_text(dry_run).lower():
            passed.append("Execution is dry-run")
        else:
            failed.append("Execution is dry-run")
            required_fixes.append("Generate a dry-run execution artifact.")

        feishu_plan = _artifact_by_type(context, ArtifactType.FEISHU_WRITE_PLAN)
        if feishu_plan:
            payload = json.loads(context.store.read_artifact_text(feishu_plan))
            if payload.get("dry_run") is True:
                passed.append("Feishu plan is dry-run")
            else:
                failed.append("Feishu plan is dry-run")
                required_fixes.append("Ensure Feishu write plan has dry_run=true.")
        else:
            warnings.append(
                "Feishu plan is generated after Reviewer in the required pipeline; FeishuPlanAgent must keep it dry-run."
            )

        non_terminal_runs = []
        for run_id in context.ticket.agent_run_ids:
            if run_id == context.current_run_id:
                continue
            agent_run = context.store.load_run(run_id)
            if not agent_run.is_terminal:
                non_terminal_runs.append(run_id)
        if non_terminal_runs:
            failed.append("All Agent Runs have terminal status")
            required_fixes.append(f"Finish non-terminal runs: {', '.join(non_terminal_runs)}.")
        else:
            passed.append("All Agent Runs have terminal status")

        verdict = ReviewVerdict.PASS if not failed else ReviewVerdict.NEEDS_FIX
        return ReviewReport(
            id=stable_id("review", context.ticket.id),
            ticket_id=context.ticket.id,
            verdict=verdict,
            passed_checks=passed,
            failed_checks=failed,
            warnings=warnings,
            required_fixes=required_fixes,
        )


class FeishuPlanAgent:
    name = "Feishu Plan"
    role = "feishu_plan"

    def run(self, context: RuntimeContext, run: AgentRun) -> AgentStepResult:
        review_id = context.ticket.metadata.get("review_report_id")
        review_verdict = "needs_human_review"
        if review_id:
            review_verdict = context.store.load_review_report(review_id).verdict.value
        packet = (
            context.store.load_build_packet(context.ticket.build_packet_id)
            if context.ticket.build_packet_id
            else None
        )
        packet_ref = packet.id if packet else "missing"
        write_plan = FeishuWritePlan(
            id=stable_id("feishu", context.ticket.id),
            ticket_id=context.ticket.id,
            dry_run=True,
            proposed_docs=[
                {
                    "title": f"{context.ticket.key} Ariadne MVP Ticket Kernel Decision",
                    "outline": [
                        "Why Build Tickets are the visible work carrier",
                        "How Build Packet, Agent Run, and Artifact stay separate",
                        "Dry-run safety and next tickets",
                    ],
                }
            ],
            proposed_tasks=[
                {
                    "title": "ARI-002 - Real Codex backend adapter",
                    "description": "Add approval-gated Codex CLI execution with captured logs and no auto-commit.",
                    "priority": "medium",
                    "due": "unscheduled",
                },
                {
                    "title": "ARI-003 - Feishu API adapter",
                    "description": "Add approval-gated Feishu write-back with dry-run preview.",
                    "priority": "medium",
                    "due": "unscheduled",
                },
            ],
            decision_log_entry=(
                f"Decision: implement Ariadne v0.1 as a local deterministic Ticket Kernel. "
                f"Reason: source evidence supports visible ticket/run/artifact state. "
                f"BuildPacket: {packet_ref}. Review verdict: {review_verdict}."
            ),
            run_summary=(
                f"Ticket {context.ticket.key} ran the local deterministic pipeline with "
                f"{len(context.ticket.agent_run_ids)} Agent Runs. External writes remain dry-run."
            ),
            next_actions=[
                "Review generated artifacts under `.ariadne/artifacts/`.",
                "Use the development report next tickets for v0.2 planning.",
                "Keep Feishu writes dry-run until an approval-gated adapter exists.",
            ],
        )
        context.store.save_feishu_write_plan(write_plan)
        artifact = context.store.write_artifact(
            context.ticket.id,
            run.id,
            ArtifactType.FEISHU_WRITE_PLAN,
            "feishu_write_plan.json",
            write_plan.model_dump_json(indent=2) + "\n",
            "Dry-run Feishu write-back plan",
            metadata={"feishu_write_plan_id": write_plan.id, "dry_run": True},
        )
        if packet:
            packet = packet.model_copy(
                deep=True,
                update={"feishu_write_plan_id": write_plan.id},
            )
            context.store.save_build_packet(packet)
        return AgentStepResult(
            output_summary="Created dry-run Feishu write plan.",
            artifacts=[artifact],
            ticket_status=TicketStatus.DONE,
            metadata={"feishu_write_plan_id": write_plan.id},
        )


def default_pipeline_nodes() -> list:
    return [
        BuildLeadAgent(),
        LearningAgent(),
        KnowledgeAgent(),
        RepoAgent(),
        PlannerAgent(),
        ExecutionDryRunAgent(),
        ReviewerAgent(),
        FeishuPlanAgent(),
    ]
