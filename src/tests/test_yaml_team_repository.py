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
    assert len(team.members) == 4
    assert len(team.steps) == 3


def test_get_team_not_found(repo: YamlTeamRepository) -> None:
    with pytest.raises(ValueError, match="見つかりません"):
        repo.get_team("nonexistent")


def test_members(repo: YamlTeamRepository) -> None:
    team = repo.get_team("startup_team_v1")
    member_ids = [m.id for m in team.members]
    assert member_ids == ["ceo", "cmo", "cfo", "cto"]
    for member in team.members:
        assert member.name
        assert member.prompt


def test_steps(repo: YamlTeamRepository) -> None:
    team = repo.get_team("startup_team_v1")
    steps = team.steps
    assert steps[0].fallback == []
    assert steps[1].fallback == ["step2", "step1"]
    assert steps[2].fallback == ["step3", "step2"]
    assert steps[2].members == ["ceo", "cmo", "cfo", "cto"]
    for step in steps:
        assert step.rounds == 4
        assert step.output != ""
        assert step.prompt != ""


def test_normalize_fallback() -> None:
    """_normalize_fallback が各入力形式を正しく変換する。"""
    assert YamlTeamRepository._normalize_fallback(None) == []
    assert YamlTeamRepository._normalize_fallback("step1") == ["step1"]
    assert YamlTeamRepository._normalize_fallback(["a", "b"]) == ["a", "b"]
