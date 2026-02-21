"""YAML ファイルからチーム定義を読み込むリポジトリの具象実装。"""

from pathlib import Path

import yaml

from src.domain.entities.team import Member, Phase, Team, Topology
from src.domain.repositories.team_repository import TeamRepository


class YamlTeamRepository(TeamRepository):
    """configs/teams/ 配下の YAML ファイルからチーム定義を読み込む。"""

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

        phases = [
            Phase(
                id=p["id"],
                name=p["name"],
                members=p["members"],
                goal=p["goal"],
                rounds=p.get("rounds", 2),
                fallback=p.get("fallback"),
            )
            for p in data["topology"]["phases"]
        ]

        return Team(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            members=members,
            topology=Topology(phases=phases),
        )
