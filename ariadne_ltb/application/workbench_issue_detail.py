from __future__ import annotations

from ariadne_ltb.application.dtos import IssueDetailResponse
from ariadne_ltb.application.workbench_issues import WorkbenchIssuesService
from ariadne_ltb.storage import AriadneStore


class WorkbenchIssueDetailService:
    def __init__(self, store: AriadneStore) -> None:
        self._issues = WorkbenchIssuesService(store)

    def get(self, issue_id_or_key: str) -> IssueDetailResponse:
        return self._issues.detail(issue_id_or_key)
