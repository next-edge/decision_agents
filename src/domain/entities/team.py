"""チーム・メンバー・トポロジーのエンティティ定義。"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Member:
    """チーム内のメンバーを表すエンティティ。"""

    id: str
    name: str
    prompt: str
    tools: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Phase:
    """トポロジーの1フェーズを表すエンティティ。"""

    id: str
    name: str
    members: list[str]
    goal: str
    rounds: int = 2
    fallback: str | None = None


@dataclass(frozen=True)
class Topology:
    """チームのトポロジー（議論の進め方）を表すエンティティ。"""

    phases: list[Phase]


@dataclass(frozen=True)
class Team:
    """チーム全体を表すエンティティ。"""

    id: str
    name: str
    description: str
    members: list[Member]
    topology: Topology
