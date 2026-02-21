"""議論の記録を表すエンティティ定義。"""

from dataclasses import dataclass, field


@dataclass
class Utterance:
    """1回の発言を表す。"""

    phase_id: str
    round_number: int
    member_id: str
    member_name: str
    text: str


@dataclass
class PhaseResult:
    """1フェーズの議論結果。"""

    phase_id: str
    phase_name: str
    goal: str
    utterances: list[Utterance] = field(default_factory=list)
    conclusion: str = ""


@dataclass
class DiscussionLog:
    """議論全体の記録。"""

    team_id: str
    team_name: str
    topic: str
    phase_results: list[PhaseResult] = field(default_factory=list)
    conclusion: str = ""
