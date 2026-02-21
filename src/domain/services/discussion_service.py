"""ステップ構成に沿った議論フローを制御するドメインサービス。"""

from collections.abc import Callable

from src.domain.agents.agent import AgentGateway
from src.domain.entities.discussion import DiscussionLog, StepResult, Utterance
from src.domain.entities.team import Member, Team

ProgressCallback = Callable[[str], None]


class DiscussionService:
    """チームのステップ構成に従い、複数エージェントによる議論を実行する。"""

    def __init__(
        self,
        agent_gateway: AgentGateway,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        self._agent_gateway = agent_gateway
        self._on_progress = on_progress or (lambda _: None)

    async def run(self, team: Team, topic: str) -> DiscussionLog:
        """議論を実行し、全ステップの記録を返す。"""
        log = DiscussionLog(
            team_id=team.id,
            team_name=team.name,
            topic=topic,
        )

        members_map = {m.id: m for m in team.members}
        prev_step_member_ids: list[str] = []

        total_steps = len(team.steps)
        for step_idx, step in enumerate(team.steps, 1):
            self._on_progress(
                f"[Step {step_idx}/{total_steps}] {step.name} を開始..."
            )
            step_result = await self._run_step(
                team=team,
                step_id=step.id,
                step_name=step.name,
                goal=step.goal,
                step_member_ids=step.members,
                prev_step_member_ids=prev_step_member_ids,
                rounds=step.rounds,
                members_map=members_map,
                previous_step_results=log.step_results,
                topic=topic,
            )

            # Step の結論を生成
            self._on_progress(f"  {step.name} の結論を要約中...")
            step_result.conclusion = await self._generate_step_conclusion(
                step_result, topic
            )

            log.step_results.append(step_result)
            prev_step_member_ids = step.members

        # 全体の結論を生成
        self._on_progress("全体の結論を要約中...")
        log.conclusion = await self._generate_overall_conclusion(log)

        return log

    async def _run_step(
        self,
        team: Team,
        step_id: str,
        step_name: str,
        goal: str,
        step_member_ids: list[str],
        prev_step_member_ids: list[str],
        rounds: int,
        members_map: dict,
        previous_step_results: list[StepResult],
        topic: str,
    ) -> StepResult:
        """1ステップの議論を実行する。"""
        step_result = StepResult(
            step_id=step_id,
            step_name=step_name,
            goal=goal,
        )

        # 新規参加者を先頭、既存メンバーを後ろにした発言順序を決定
        new_member_ids = [
            mid for mid in step_member_ids if mid not in prev_step_member_ids
        ]
        existing_member_ids = [
            mid for mid in step_member_ids if mid in prev_step_member_ids
        ]
        speaking_order = new_member_ids + existing_member_ids

        # 新規メンバーには前ステップの結論を、既存メンバーには当該ステップの会話履歴を渡す
        # まず前ステップまでの結論を構築
        step_conclusions_context = self._build_step_conclusions_context(
            previous_step_results
        )

        # 当該ステップ内の会話履歴（ラウンド内で蓄積）
        current_step_history: list[dict[str, str]] = []

        system_context = f"議題: {topic}\nステップ: {step_name}\n目的: {goal}"

        for round_num in range(1, rounds + 1):
            self._on_progress(f"  Round {round_num}/{rounds}")
            for member_id in speaking_order:
                member = members_map[member_id]
                self._on_progress(f"    {member.name} が発言中...")

                # 会話履歴を構築: 前ステップの結論 + 当該ステップ内の発言
                # 自分自身の過去発言は要約に置き換え、重複を抑制する
                conversation_history = []
                if step_conclusions_context:
                    conversation_history.append(
                        {
                            "role": "system",
                            "name": "前ステップまでの結論",
                            "text": step_conclusions_context,
                        }
                    )
                for entry in current_step_history:
                    if entry["name"] == member.name:
                        excerpt = self._truncate(entry["text"], max_chars=200)
                        conversation_history.append(
                            {
                                **entry,
                                "text": f"（あなたの過去の発言の要旨）{excerpt}",
                            }
                        )
                    else:
                        conversation_history.append(entry)

                response = await self._agent_gateway.generate_response(
                    member=member,
                    conversation_history=conversation_history,
                    system_context=system_context,
                )

                utterance = Utterance(
                    step_id=step_id,
                    round_number=round_num,
                    member_id=member_id,
                    member_name=member.name,
                    text=response,
                )
                step_result.utterances.append(utterance)

                # 当該ステップの会話履歴に追加
                current_step_history.append(
                    {
                        "role": "agent",
                        "name": member.name,
                        "text": response,
                    }
                )

        return step_result

    async def _generate_step_conclusion(
        self, step_result: StepResult, topic: str
    ) -> str:
        """1ステップの議論を踏まえて結論を要約する。"""
        summarizer = Member(
            id="step_summarizer",
            name="ステップ要約担当",
            prompt=(
                "あなたは議論の要約担当です。\n"
                "このステップの議論内容を分析し、以下の構成で簡潔に要約してください。\n\n"
                "1. このステップの結論（合意事項・決定事項）\n"
                "2. 主要な論点と各メンバーの見解\n"
                "3. 次のステップに引き継ぐべき課題"
            ),
        )
        history: list[dict[str, str]] = [
            {"role": "agent", "name": u.member_name, "text": u.text}
            for u in step_result.utterances
        ]
        return await self._agent_gateway.generate_response(
            member=summarizer,
            conversation_history=history,
            system_context=f"議題: {topic}\nステップ: {step_result.step_name}\n目的: {step_result.goal}",
        )

    async def _generate_overall_conclusion(self, log: DiscussionLog) -> str:
        """全ステップの結論を踏まえて全体の結論を要約する。"""
        summarizer = Member(
            id="overall_summarizer",
            name="全体要約担当",
            prompt=(
                "あなたは議論の要約担当です。\n"
                "複数ステップにわたる議論の結論を分析し、以下の構成で簡潔に要約してください。\n\n"
                "1. 議論の最終結論（最も重要な合意事項や決定事項）\n"
                "2. 各ステップで得られた主要な知見\n"
                "3. 残された課題やリスク"
            ),
        )
        # 各ステップの結論を会話履歴として渡す
        history: list[dict[str, str]] = [
            {
                "role": "agent",
                "name": f"{r.step_name}の結論",
                "text": r.conclusion,
            }
            for r in log.step_results
            if r.conclusion
        ]
        return await self._agent_gateway.generate_response(
            member=summarizer,
            conversation_history=history,
            system_context=f"議題: {log.topic}",
        )

    @staticmethod
    def _truncate(text: str, max_chars: int = 200) -> str:
        """テキストを指定文字数で切り詰める。"""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "…（以降省略）"

    def _build_step_conclusions_context(
        self, step_results: list[StepResult]
    ) -> str:
        """前ステップまでの結論を結合したコンテキスト文字列を返す。"""
        if not step_results:
            return ""
        parts: list[str] = []
        for result in step_results:
            if result.conclusion:
                parts.append(f"【{result.step_name}の結論】\n{result.conclusion}")
        return "\n\n".join(parts)
