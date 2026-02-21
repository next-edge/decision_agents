"""議論の記録を表すエンティティ定義。"""

from dataclasses import dataclass, field


@dataclass
class Utterance:
    """1回の発言を表す。"""

    step_id: str
    round_number: int
    member_id: str
    member_name: str
    text: str


@dataclass
class StepResult:
    """1ステップの議論結果。"""

    step_id: str
    step_name: str
    goal: str
    utterances: list[Utterance] = field(default_factory=list)
    conclusion: str = ""


@dataclass
class DiscussionLog:
    """議論全体の記録。"""

    team_id: str
    team_name: str
    topic: str
    step_results: list[StepResult] = field(default_factory=list)
    conclusion: str = ""
