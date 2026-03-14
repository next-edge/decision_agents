"""YAML ファイルからチーム定義を読み込むリポジトリの具象実装。"""

from pathlib import Path

import yaml

from src.domain.entities.team import Member, Step, Team
from src.domain.repositories.team_repository import TeamRepository


class YamlTeamRepository(TeamRepository):
    """configs/teams/ 配下の YAML ファイルからチーム定義を読み込む。"""

    @staticmethod
    def _normalize_fallback(raw: str | list[str] | None) -> list[str]:
        """fallback フィールドを list[str] に正規化する（後方互換）。"""
        if raw is None:
            return []
        if isinstance(raw, str):
            return [raw]
        if isinstance(raw, list):
            return raw
        raise ValueError(f"fallback の形式が不正です: {raw!r}")

    def __init__(self, teams_dir: str | Path) -> None:
        self._teams_dir = Path(teams_dir)

    def list_teams(self) -> list[Team]:
        teams = []
        for path in sorted(self._teams_dir.glob("*.yaml")):
            teams.append(self._load(path))
        return teams

    def get_team(self, team_id: str) -> Team:
        for team in self.list_teams():
            if team.id == team_id:
                return team
        raise ValueError(f"チーム '{team_id}' が見つかりません")

    def _load(self, path: Path) -> Team:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        members = [
            Member(
                id=m["id"],
                name=m["name"],
                prompt=m["prompt"].strip(),
                tools=m.get("tools", []),
            )
            for m in data["members"]
        ]

        steps = [
            Step(
                id=s["id"],
                name=s["name"],
                members=s["members"],
                description=s["description"],
                output=s.get("output", ""),
                prompt=s.get("prompt", ""),
                rounds=s.get("rounds", 2),
                fallback=self._normalize_fallback(s.get("fallback")),
            )
            for s in data["steps"]
        ]

        return Team(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            members=members,
            steps=steps,
        )
