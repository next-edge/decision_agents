"""ステップ構成に沿った議論フローを制御するドメインサービス。"""

from collections.abc import Callable

from src.domain.agents.agent import AgentGateway
from src.domain.entities.discussion import (
    DiscussionLog,
    FallbackEvent,
    QualityEvaluation,
    StepResult,
    Utterance,
)
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
        step_id_to_index = {s.id: i for i, s in enumerate(team.steps)}
        fallback_used: set[str] = set()
        failed_step_results: list[StepResult] = []

        total_steps = len(team.steps)
        step_idx = 0
        while step_idx < total_steps:
            step = team.steps[step_idx]
            prev_step_member_ids = (
                team.steps[step_idx - 1].members if step_idx > 0 else []
            )

            self._on_progress(
                f"[Step {step_idx + 1}/{total_steps}] {step.name} を開始..."
            )
            step_result = await self._run_step(
                team=team,
                step_id=step.id,
                step_name=step.name,
                description=step.description,
                output=step.output,
                prompt=step.prompt,
                step_member_ids=step.members,
                prev_step_member_ids=prev_step_member_ids,
                rounds=step.rounds,
                members_map=members_map,
                previous_step_results=log.step_results,
                failed_step_results=failed_step_results,
                topic=topic,
            )

            # Step の結論を生成
            self._on_progress(f"  {step.name} の結論を要約中...")
            step_result.conclusion = await self._generate_step_conclusion(
                step_result, topic, step.output
            )

            # 品質評価 & fallback
            should_fallback = False
            fallback_target_id: str | None = None
            fallback_reason = ""
            if step.fallback and step.id not in fallback_used and step.output:
                # 各候補の情報を構築
                fallback_candidates: list[dict[str, str]] = []
                for cid in step.fallback:
                    if cid == step.id:
                        fallback_candidates.append({
                            "id": step.id,
                            "name": step.name,
                            "description": f"当該ステップ自身をやり直す（{step.description}）",
                        })
                    else:
                        cs = team.steps[step_id_to_index[cid]]
                        fallback_candidates.append({
                            "id": cs.id,
                            "name": cs.name,
                            "description": cs.description,
                        })

                evaluation = await self._evaluate_step_quality(
                    conclusion=step_result.conclusion,
                    expected_output=step.output,
                    step_name=step.name,
                    topic=topic,
                    fallback_candidates=fallback_candidates,
                )
                if not evaluation.is_passed:
                    should_fallback = True
                    fallback_target_id = evaluation.fallback_target_step_id
                    fallback_reason = evaluation.reason

            if should_fallback:
                assert fallback_target_id is not None
                fallback_used.add(step.id)
                fallback_idx = step_id_to_index[fallback_target_id]

                self._on_progress(
                    f"  {step.name} の品質が基準を満たさないため、"
                    f"{fallback_target_id} から再実行します..."
                )

                # 失敗コンテキストを構築: fallback 地点以降の既存結果 + 今回の失敗結果
                removed = [
                    r
                    for r in log.step_results
                    if step_id_to_index.get(r.step_id, 0) >= fallback_idx
                ]
                failed_step_results = removed + [step_result]

                log.fallback_events.append(
                    FallbackEvent(
                        failed_step_id=step.id,
                        failed_step_name=step.name,
                        fallback_target_step_id=fallback_target_id,
                        failed_conclusion=step_result.conclusion,
                        reason=fallback_reason,
                        failed_step_results=failed_step_results,
                    )
                )

                # log.step_results を fallback 地点の前まで巻き戻す
                log.step_results = [
                    r
                    for r in log.step_results
                    if step_id_to_index.get(r.step_id, 0) < fallback_idx
                ]

                step_idx = fallback_idx
                continue

            # 通常進行
            log.step_results.append(step_result)
            failed_step_results = []
            step_idx += 1

        # 全体の結論を生成
        self._on_progress("全体の結論を要約中...")
        log.conclusion = await self._generate_overall_conclusion(log)

        return log

    async def _run_step(
        self,
        team: Team,
        step_id: str,
        step_name: str,
        description: str,
        output: str,
        prompt: str,
        step_member_ids: list[str],
        prev_step_member_ids: list[str],
        rounds: int,
        members_map: dict,
        previous_step_results: list[StepResult],
        topic: str,
        failed_step_results: list[StepResult] | None = None,
    ) -> StepResult:
        """1ステップの議論を実行する。"""
        step_result = StepResult(
            step_id=step_id,
            step_name=step_name,
            description=description,
            output=output,
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
            previous_step_results, failed_step_results
        )

        # 当該ステップ内の会話履歴（ラウンド内で蓄積）
        current_step_history: list[dict[str, str]] = []

        system_context = f"議題: {topic}\nステップ: {step_name}\n目的: {description}"
        if output:
            system_context += f"\n期待されるアウトプット: {output}"
        if prompt:
            system_context += f"\n議論の方針: {prompt}"

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
        self, step_result: StepResult, topic: str, output: str = ""
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
        system_context = f"議題: {topic}\nステップ: {step_result.step_name}\n目的: {step_result.description}"
        if output:
            system_context += f"\n期待されるアウトプット: {output}"
        return await self._agent_gateway.generate_response(
            member=summarizer,
            conversation_history=history,
            system_context=system_context,
        )

    async def _evaluate_step_quality(
        self,
        conclusion: str,
        expected_output: str,
        step_name: str,
        topic: str,
        fallback_candidates: list[dict[str, str]] | None = None,
    ) -> QualityEvaluation:
        """結論が期待されるアウトプットの要件を満たすか評価する。

        fallback_candidates が指定されている場合、不合格時にどのステップへ
        差し戻すかも LLM に判断させる。
        """
        if fallback_candidates is None:
            fallback_candidates = []

        # 差し戻し候補の説明を構築
        candidates_text = ""
        if fallback_candidates:
            lines = []
            for c in fallback_candidates:
                lines.append(f"  - {c['id']}: {c['name']}（{c['description']}）")
            candidates_text = "\n".join(lines)

        prompt_parts = [
            "あなたは議論の品質を評価する担当者です。",
            "ステップの結論が、期待されるアウトプットの要件を十分に満たしているか判定してください。",
            "",
            "以下の基準で評価してください：",
            "- 期待されるアウトプットで求められている内容が結論に含まれているか",
            "- 結論の具体性と実用性が十分か",
            "",
        ]

        if candidates_text:
            prompt_parts.extend([
                "不合格の場合、以下の差し戻し候補から最も適切な差し戻し先を選んでください：",
                candidates_text,
                "",
                "差し戻し先の選択基準：",
                "- 当該ステップ自身: 議論の進め方に問題がありやり直せば改善が見込める場合",
                "- 前のステップ: 前ステップから引き継いだ情報の質が低くそこからやり直す必要がある場合",
                "",
                "回答形式：",
                "- 合格時: 「判定: 合格」",
                "- 不合格時（3行で回答）:",
                "  判定: 不合格",
                "  差し戻し先: （候補の中から選んだステップID）",
                "  理由: （差し戻し理由）",
            ])
        else:
            prompt_parts.append(
                "最後に必ず「判定: 合格」または「判定: 不合格」のいずれかで回答してください。"
            )

        evaluator = Member(
            id="quality_evaluator",
            name="品質評価担当",
            prompt="\n".join(prompt_parts),
        )
        conversation_history = [
            {
                "role": "agent",
                "name": f"{step_name}の結論",
                "text": conclusion,
            }
        ]
        system_context = (
            f"議題: {topic}\n"
            f"ステップ: {step_name}\n"
            f"期待されるアウトプット: {expected_output}"
        )
        response = await self._agent_gateway.generate_response(
            member=evaluator,
            conversation_history=conversation_history,
            system_context=system_context,
        )

        if "判定: 不合格" not in response:
            return QualityEvaluation(is_passed=True)

        # 差し戻し先を抽出
        target_id: str | None = None
        reason = ""
        for line in response.splitlines():
            stripped = line.strip()
            if stripped.startswith("差し戻し先:"):
                target_id = stripped.replace("差し戻し先:", "").strip()
            elif stripped.startswith("理由:"):
                reason = stripped.replace("理由:", "").strip()

        # 候補リストに含まれない場合は先頭をデフォルトとする
        candidate_ids = [c["id"] for c in fallback_candidates]
        if candidate_ids and (target_id is None or target_id not in candidate_ids):
            target_id = candidate_ids[0]

        return QualityEvaluation(
            is_passed=False,
            fallback_target_step_id=target_id,
            reason=reason,
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
        self,
        step_results: list[StepResult],
        failed_step_results: list[StepResult] | None = None,
    ) -> str:
        """前ステップまでの結論を結合したコンテキスト文字列を返す。"""
        if not step_results and not failed_step_results:
            return ""
        parts: list[str] = []
        if failed_step_results:
            for result in failed_step_results:
                if result.conclusion:
                    parts.append(
                        f"【前回の{result.step_name}の結論（品質不足で差し戻し）】\n{result.conclusion}"
                    )
        for result in step_results:
            if result.conclusion:
                parts.append(f"【{result.step_name}の結論】\n{result.conclusion}")
        return "\n\n".join(parts)
