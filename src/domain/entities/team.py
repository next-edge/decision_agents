"""チーム・メンバー・ステップのエンティティ定義。"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Member:
    """チーム内のメンバーを表すエンティティ。"""

    id: str
    name: str
    prompt: str
    tools: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Step:
    """議論の1ステップを表すエンティティ。"""

    id: str
    name: str
    members: list[str]
    description: str
    output: str = ""
    prompt: str = ""
    rounds: int = 2
    fallback: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Team:
    """チーム全体を表すエンティティ。"""

    id: str
    name: str
    description: str
    members: list[Member]
    steps: list[Step]
