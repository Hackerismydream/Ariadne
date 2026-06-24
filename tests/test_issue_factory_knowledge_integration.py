from __future__ import annotations

from ariadne_ltb.application.issue_compiler import compile_issue_specs
from ariadne_ltb.knowledge import compile_issues

from tests.test_issue_factory_compiler import _seed_mini_code_agent_context


def test_compile_issues_falls_back_without_deepseek_key(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    store, goal_id, project_id, source_ids = _seed_mini_code_agent_context(tmp_path)
    from ariadne_ltb.application.build_context import assemble_issue_factory_context
    from ariadne_ltb.application.project_goals import ProjectGoalService

    goal = ProjectGoalService(store).load(goal_id)
    sources = [store.load_source_document(source_id) for source_id in source_ids]
    context = assemble_issue_factory_context(store, goal, sources, project_id)

    fallback = compile_issue_specs(store, title=goal.title, north_star=goal.north_star, context=context)
    compiled = compile_issues(
        store,
        project_id=project_id,
        title=goal.title,
        north_star=goal.north_star,
        context=context,
    )

    assert [item.title for item in compiled] == [item.title for item in fallback]
    assert not (store.base / "knowledge" / project_id).exists()

