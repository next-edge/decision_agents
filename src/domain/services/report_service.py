"""議論結果のレポートを生成するドメインサービス。"""

from datetime import datetime
from pathlib import Path

from src.domain.entities.discussion import DiscussionLog
from src.domain.entities.team import Team


class ReportService:
    """DiscussionLog からマークダウン形式のレポートを生成し、ファイルに出力する。"""

    def __init__(self, output_dir: str | Path) -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, log: DiscussionLog, team: Team) -> Path:
        """レポートを生成してファイルに保存し、出力パスを返す。"""
        content = self._render(log, team)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{log.team_id}_{timestamp}.md"
        path = self._output_dir / filename
        path.write_text(content, encoding="utf-8")
        return path

    def _render(self, log: DiscussionLog, team: Team) -> str:
        lines: list[str] = []
        lines.append(f"# 議論レポート: {log.team_name}")
        lines.append("")
        lines.append(f"**議題:** {log.topic}")
        lines.append("")

        # チーム構成
        lines.append("## チーム構成")
        lines.append("")
        lines.append(f"**チーム名:** {team.name}")
        lines.append("")
        lines.append(f"**概要:** {team.description}")
        lines.append("")
        lines.append("### メンバー")
        lines.append("")
        lines.append("| ID | 名前 |")
        lines.append("| --- | --- |")
        for member in team.members:
            lines.append(f"| {member.id} | {member.name} |")
        lines.append("")

        # ステップ構成
        lines.append("### ステップ構成")
        lines.append("")
        lines.append("| Step | 名前 | 参加メンバー | 目的 | ラウンド数 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for step in team.steps:
            members_str = ", ".join(step.members)
            lines.append(
                f"| {step.id} | {step.name} | {members_str} "
                f"| {step.goal} | {step.rounds} |"
            )
        lines.append("")

        # 結論
        if log.conclusion:
            lines.append("## 結論")
            lines.append("")
            lines.append(log.conclusion)
            lines.append("")

        # 各ステップの詳細
        lines.append("---")
        lines.append("")
        lines.append("## 議論の詳細")
        lines.append("")

        for step_result in log.step_results:
            lines.append(f"### {step_result.step_name}")
            lines.append("")
            lines.append(f"**目的:** {step_result.goal}")
            lines.append("")

            if step_result.conclusion:
                lines.append(f"#### このステップの結論")
                lines.append("")
                lines.append(step_result.conclusion)
                lines.append("")

            current_round = 0
            for utterance in step_result.utterances:
                if utterance.round_number != current_round:
                    current_round = utterance.round_number
                    lines.append(f"#### Round {current_round}")
                    lines.append("")

                lines.append(f"##### {utterance.member_name}")
                lines.append("")
                lines.append(utterance.text)
                lines.append("")

        return "\n".join(lines)
