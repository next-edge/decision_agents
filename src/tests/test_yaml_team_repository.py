"""YamlTeamRepository のテスト。"""

from pathlib import Path

import pytest

from src.data.repositories.yaml_team_repository import YamlTeamRepository

TEAMS_DIR = Path(__file__).resolve().parents[2] / "configs" / "teams"


@pytest.fixture
def repo() -> YamlTeamRepository:
    return YamlTeamRepository(TEAMS_DIR)


def test_list_teams(repo: YamlTeamRepository) -> None:
    teams = repo.list_teams()
    assert len(teams) >= 1
    assert teams[0].id == "startup_team_v1"


def test_get_team(repo: YamlTeamRepository) -> None:
    team = repo.get_team("startup_team_v1")
    assert team.name == "スタートアップチーム(v1)"
    assert len(team.members) == 5
    assert len(team.topology.phases) == 4


def test_get_team_not_found(repo: YamlTeamRepository) -> None:
    with pytest.raises(ValueError, match="見つかりません"):
        repo.get_team("nonexistent")


def test_members(repo: YamlTeamRepository) -> None:
    team = repo.get_team("startup_team_v1")
    member_ids = [m.id for m in team.members]
    assert member_ids == ["ceo", "cmo", "cfo", "cto", "devils_advocate"]
    for member in team.members:
        assert member.name
        assert member.prompt


def test_topology_phases(repo: YamlTeamRepository) -> None:
    team = repo.get_team("startup_team_v1")
    phases = team.topology.phases
    assert phases[0].fallback is None
    assert phases[1].fallback == "phase1"
    assert phases[2].fallback == "phase2"
    assert phases[3].fallback == "phase3"
    assert phases[3].members == ["ceo", "cmo", "cfo", "cto", "devils_advocate"]
    for phase in phases:
        assert phase.rounds == 2
