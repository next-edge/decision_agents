"""チームリポジトリのインタフェース定義。"""

from abc import ABC, abstractmethod

from src.domain.entities.team import Team


class TeamRepository(ABC):
    """チーム定義の読み込みを担当するリポジトリのインタフェース。"""

    @abstractmethod
    def list_teams(self) -> list[Team]:
        """利用可能な全チームを返す。"""

    @abstractmethod
    def get_team(self, team_id: str) -> Team:
        """指定IDのチームを返す。見つからない場合は例外を送出する。"""
