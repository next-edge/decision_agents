"""議論の記録を表すエンティティ定義。"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Utterance:
    """1回の発言を表す。"""

    step_id: str
    round_number: int
    member_id: str
    member_name: str
    text: str


@dataclass
class QualityEvaluation:
    """品質評価の結果。"""

    is_passed: bool
    fallback_target_step_id: str | None = None
    reason: str = ""


@dataclass
class StepResult:
    """1ステップの議論結果。"""

    step_id: str
    step_name: str
    description: str
    output: str = ""
    utterances: list[Utterance] = field(default_factory=list)
    conclusion: str = ""


@dataclass
class FallbackEvent:
    """品質差し戻しの記録。"""

    failed_step_id: str
    failed_step_name: str
    fallback_target_step_id: str
    failed_conclusion: str
    reason: str = ""
    failed_step_results: list[StepResult] = field(default_factory=list)


@dataclass
class DiscussionLog:
    """議論全体の記録。"""

    team_id: str
    team_name: str
    topic: str
    step_results: list[StepResult] = field(default_factory=list)
    fallback_events: list[FallbackEvent] = field(default_factory=list)
    conclusion: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
