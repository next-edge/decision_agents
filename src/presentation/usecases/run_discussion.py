"""チーム議論を実行するユースケース。"""

from pathlib import Path

from src.domain.entities.discussion import DiscussionLog
from src.domain.repositories.team_repository import TeamRepository
from src.domain.services.discussion_service import DiscussionService
from src.domain.services.report_service import ReportService


class RunDiscussionUsecase:
    """チームを選択し、議題に対する議論を実行してレポートを出力する。"""

    def __init__(
        self,
        team_repository: TeamRepository,
        discussion_service: DiscussionService,
        report_service: ReportService,
    ) -> None:
        self._team_repository = team_repository
        self._discussion_service = discussion_service
        self._report_service = report_service

    def list_teams(self) -> list[dict[str, str]]:
        """利用可能なチームの一覧を返す。"""
        teams = self._team_repository.list_teams()
        return [
            {"id": t.id, "name": t.name, "description": t.description}
            for t in teams
        ]

    async def execute(self, team_id: str, topic: str) -> Path:
        """議論を実行し、レポートを保存してパスを返す。"""
        team = self._team_repository.get_team(team_id)
        log: DiscussionLog = await self._discussion_service.run(team, topic)
        report_path = self._report_service.save(log, team)
        return report_path
