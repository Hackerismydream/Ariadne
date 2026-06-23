from __future__ import annotations

from typing import Any

from ariadne_ltb.knowledge.models import SynthesisTheme


def theme_issue_dicts(themes: list[SynthesisTheme]) -> list[dict[str, Any]]:
    return [
        {
            "title": f"Implement {theme.label}",
            "reason": (
                f"ProjectKnowledge theme '{theme.label}' indicates this work is needed: "
                + "; ".join(theme.claims[:3])
            ),
            "priority": "P0" if theme.priority_signal == "high" else "P1",
            "affected_modules": theme.affected_modules,
            "acceptance_criteria": [
                f"The implementation addresses ProjectKnowledge theme '{theme.label}'.",
                "Verification evidence is captured for the affected modules.",
            ],
            "evidence_refs": [theme.id],
            "depends_on": [],
            "owner_agent": "Build Lead",
            "build_decision": "code_task",
            "risks": [],
            "assumptions": ["Generated from persisted ProjectKnowledge themes."],
        }
        for theme in themes[:10]
    ]

