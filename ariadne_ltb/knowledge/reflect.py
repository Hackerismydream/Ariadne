from __future__ import annotations

from ariadne_ltb.knowledge.llm_adapter import KnowledgeLLM, call_json, has_deepseek_key
from ariadne_ltb.knowledge.models import BlockerLearning, OutcomeEntry
from ariadne_ltb.knowledge.store import ProjectKnowledgeStore
from ariadne_ltb.llm import LLMClientError
from ariadne_ltb.models import AgentRun, AgentRunStatus, ReviewReport, stable_id
from ariadne_ltb.storage import AriadneStore


def reflect_on_run(
    store: AriadneStore,
    *,
    run: AgentRun,
    review: ReviewReport | None = None,
    llm: KnowledgeLLM | None = None,
) -> None:
    if not run.status.is_terminal:
        return
    try:
        _reflect_inner(store, run, review, llm)
    except Exception:
        return


def _reflect_inner(
    store: AriadneStore,
    run: AgentRun,
    review: ReviewReport | None,
    llm: KnowledgeLLM | None,
) -> None:
    ticket = store.load_ticket(run.ticket_id)
    project_id = str(ticket.metadata.get("target_project_id") or "default")
    knowledge_store = ProjectKnowledgeStore(store, project_id)
    log = knowledge_store.load_outcomes_log()
    new_status = _outcome_status(run.status)
    new_blocker = run.failure_reason.value if run.failure_reason else None
    new_review = review.verdict.value if review else None
    new_learning = run.output_summary or run.error or ""

    open_entry = None
    for entry in reversed(log.entries):
        if entry.ticket_key != ticket.key:
            continue
        if entry.review_verdict is None or (
            entry.status == "done" and entry.blocker_reason is None and new_blocker
        ):
            open_entry = entry
        break

    blocker_added = False
    if open_entry is not None:
        if new_review and open_entry.review_verdict is None:
            open_entry.review_verdict = new_review
        if new_blocker and open_entry.blocker_reason is None:
            open_entry.blocker_reason = new_blocker
            blocker_added = True
            if open_entry.status == "done":
                open_entry.status = new_status
        if new_learning and new_learning not in open_entry.learnings:
            open_entry.learnings.append(new_learning)
    else:
        log.entries.append(
            OutcomeEntry(
                ticket_key=ticket.key,
                ticket_title=ticket.title,
                status=new_status,
                review_verdict=new_review,
                blocker_reason=new_blocker,
                learnings=[new_learning] if new_learning else [],
            )
        )
        blocker_added = bool(new_blocker)

    knowledge_store.save_outcomes_log(log)
    if new_blocker and blocker_added:
        _upsert_blocker_learning(
            knowledge_store,
            ticket.key,
            new_blocker,
            new_learning,
            llm,
        )


def _outcome_status(status: AgentRunStatus) -> str:
    if status is AgentRunStatus.SUCCEEDED:
        return "done"
    if status in {AgentRunStatus.BLOCKED, AgentRunStatus.FAILED}:
        return "blocked"
    return "abandoned"


def _upsert_blocker_learning(
    knowledge_store: ProjectKnowledgeStore,
    ticket_key: str,
    blocker_reason: str,
    summary: str,
    llm: KnowledgeLLM | None,
) -> None:
    existing = {
        item.blocker_reason: item for item in knowledge_store.list_blocker_learnings()
    }
    previous = existing.get(blocker_reason)
    pattern = summary[:500] or blocker_reason
    mitigation = "Retry after fixing the recorded blocker and rerun checks."
    if llm and has_deepseek_key():
        try:
            from ariadne_ltb.knowledge.prompts import blocker_learning_prompt

            response = call_json(llm, blocker_learning_prompt(ticket_key, blocker_reason, summary), "BlockerLearning")
            pattern = str(response.get("failure_pattern") or pattern)
            mitigation = str(response.get("mitigation") or mitigation)
        except LLMClientError:
            pass
    learning = BlockerLearning(
        id=previous.id if previous else stable_id("blocker_learning", knowledge_store.project_id, blocker_reason),
        project_id=knowledge_store.project_id,
        blocker_reason=blocker_reason,
        failure_pattern=pattern if previous is None else previous.failure_pattern,
        mitigation=mitigation if previous is None else previous.mitigation,
        seen_in_ticket_keys=sorted({*(previous.seen_in_ticket_keys if previous else []), ticket_key}),
        seen_count=(previous.seen_count + 1) if previous else 1,
    )
    knowledge_store.save_blocker_learning(learning)
