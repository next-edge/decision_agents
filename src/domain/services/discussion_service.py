"""トポロジーに沿った議論フローを制御するドメインサービス。"""

from collections.abc import Callable

from src.domain.agents.agent import AgentGateway
from src.domain.entities.discussion import DiscussionLog, PhaseResult, Utterance
from src.domain.entities.team import Member, Team

ProgressCallback = Callable[[str], None]


class DiscussionService:
    """チームのトポロジーに従い、複数エージェントによる議論を実行する。"""

    def __init__(
        self,
        agent_gateway: AgentGateway,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        self._agent_gateway = agent_gateway
        self._on_progress = on_progress or (lambda _: None)

    async def run(self, team: Team, topic: str) -> DiscussionLog:
        """議論を実行し、全フェーズの記録を返す。"""
        log = DiscussionLog(
            team_id=team.id,
            team_name=team.name,
            topic=topic,
        )

        members_map = {m.id: m for m in team.members}
        prev_phase_member_ids: list[str] = []

        total_phases = len(team.topology.phases)
        for phase_idx, phase in enumerate(team.topology.phases, 1):
            self._on_progress(
                f"[Phase {phase_idx}/{total_phases}] {phase.name} を開始..."
            )
            phase_result = await self._run_phase(
                team=team,
                phase_id=phase.id,
                phase_name=phase.name,
                goal=phase.goal,
                phase_member_ids=phase.members,
                prev_phase_member_ids=prev_phase_member_ids,
                rounds=phase.rounds,
                members_map=members_map,
                previous_phase_results=log.phase_results,
                topic=topic,
            )

            # Phase の結論を生成
            self._on_progress(f"  {phase.name} の結論を要約中...")
            phase_result.conclusion = await self._generate_phase_conclusion(
                phase_result, topic
            )

            log.phase_results.append(phase_result)
            prev_phase_member_ids = phase.members

        # 全体の結論を生成
        self._on_progress("全体の結論を要約中...")
        log.conclusion = await self._generate_overall_conclusion(log)

        return log

    async def _run_phase(
        self,
        team: Team,
        phase_id: str,
        phase_name: str,
        goal: str,
        phase_member_ids: list[str],
        prev_phase_member_ids: list[str],
        rounds: int,
        members_map: dict,
        previous_phase_results: list[PhaseResult],
        topic: str,
    ) -> PhaseResult:
        """1フェーズの議論を実行する。"""
        phase_result = PhaseResult(
            phase_id=phase_id,
            phase_name=phase_name,
            goal=goal,
        )

        # 新規参加者を先頭、既存メンバーを後ろにした発言順序を決定
        new_member_ids = [
            mid for mid in phase_member_ids if mid not in prev_phase_member_ids
        ]
        existing_member_ids = [
            mid for mid in phase_member_ids if mid in prev_phase_member_ids
        ]
        speaking_order = new_member_ids + existing_member_ids

        # 新規メンバーには前フェーズの結論を、既存メンバーには当該フェーズの会話履歴を渡す
        # まず前フェーズまでの結論を構築
        phase_conclusions_context = self._build_phase_conclusions_context(
            previous_phase_results
        )

        # 当該フェーズ内の会話履歴（ラウンド内で蓄積）
        current_phase_history: list[dict[str, str]] = []

        system_context = f"議題: {topic}\nフェーズ: {phase_name}\n目的: {goal}"

        for round_num in range(1, rounds + 1):
            self._on_progress(f"  Round {round_num}/{rounds}")
            for member_id in speaking_order:
                member = members_map[member_id]
                self._on_progress(f"    {member.name} が発言中...")

                # 会話履歴を構築: 前フェーズの結論 + 当該フェーズ内の発言
                conversation_history = []
                if phase_conclusions_context:
                    conversation_history.append(
                        {
                            "role": "system",
                            "name": "前フェーズまでの結論",
                            "text": phase_conclusions_context,
                        }
                    )
                conversation_history.extend(current_phase_history)

                response = await self._agent_gateway.generate_response(
                    member=member,
                    conversation_history=conversation_history,
                    system_context=system_context,
                )

                utterance = Utterance(
                    phase_id=phase_id,
                    round_number=round_num,
                    member_id=member_id,
                    member_name=member.name,
                    text=response,
                )
                phase_result.utterances.append(utterance)

                # 当該フェーズの会話履歴に追加
                current_phase_history.append(
                    {
                        "role": "agent",
                        "name": member.name,
                        "text": response,
                    }
                )

        return phase_result

    async def _generate_phase_conclusion(
        self, phase_result: PhaseResult, topic: str
    ) -> str:
        """1フェーズの議論を踏まえて結論を要約する。"""
        summarizer = Member(
            id="phase_summarizer",
            name="フェーズ要約担当",
            prompt=(
                "あなたは議論の要約担当です。\n"
                "このフェーズの議論内容を分析し、以下の構成で簡潔に要約してください。\n\n"
                "1. このフェーズの結論（合意事項・決定事項）\n"
                "2. 主要な論点と各メンバーの見解\n"
                "3. 次のフェーズに引き継ぐべき課題"
            ),
        )
        history: list[dict[str, str]] = [
            {"role": "agent", "name": u.member_name, "text": u.text}
            for u in phase_result.utterances
        ]
        return await self._agent_gateway.generate_response(
            member=summarizer,
            conversation_history=history,
            system_context=f"議題: {topic}\nフェーズ: {phase_result.phase_name}\n目的: {phase_result.goal}",
        )

    async def _generate_overall_conclusion(self, log: DiscussionLog) -> str:
        """全フェーズの結論を踏まえて全体の結論を要約する。"""
        summarizer = Member(
            id="overall_summarizer",
            name="全体要約担当",
            prompt=(
                "あなたは議論の要約担当です。\n"
                "複数フェーズにわたる議論の結論を分析し、以下の構成で簡潔に要約してください。\n\n"
                "1. 議論の最終結論（最も重要な合意事項や決定事項）\n"
                "2. 各フェーズで得られた主要な知見\n"
                "3. 残された課題やリスク"
            ),
        )
        # 各フェーズの結論を会話履歴として渡す
        history: list[dict[str, str]] = [
            {
                "role": "agent",
                "name": f"{r.phase_name}の結論",
                "text": r.conclusion,
            }
            for r in log.phase_results
            if r.conclusion
        ]
        return await self._agent_gateway.generate_response(
            member=summarizer,
            conversation_history=history,
            system_context=f"議題: {log.topic}",
        )

    def _build_phase_conclusions_context(
        self, phase_results: list[PhaseResult]
    ) -> str:
        """前フェーズまでの結論を結合したコンテキスト文字列を返す。"""
        if not phase_results:
            return ""
        parts: list[str] = []
        for result in phase_results:
            if result.conclusion:
                parts.append(f"【{result.phase_name}の結論】\n{result.conclusion}")
        return "\n\n".join(parts)
