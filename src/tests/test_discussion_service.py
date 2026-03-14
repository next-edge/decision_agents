"""DiscussionService の fallback ロジックのテスト。"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.domain.agents.agent import AgentGateway
from src.domain.entities.discussion import StepResult
from src.domain.entities.team import Member, Step, Team
from src.domain.services.discussion_service import DiscussionService


class MockAgentGateway(AgentGateway):
    """テスト用の AgentGateway モック。"""

    def __init__(self) -> None:
        self._mock = AsyncMock(return_value="テスト応答")

    async def generate_response(
        self,
        member: Member,
        conversation_history: list[dict[str, str]],
        system_context: str,
    ) -> str:
        return await self._mock(
            member=member,
            conversation_history=conversation_history,
            system_context=system_context,
        )

    def set_return_value(self, value: str) -> None:
        self._mock.return_value = value

    def set_side_effect(self, side_effect):  # noqa: ANN001
        self._mock.side_effect = side_effect


def _make_team(steps: list[Step]) -> Team:
    """テスト用のチームを生成する。"""
    return Team(
        id="test_team",
        name="テストチーム",
        description="テスト用",
        members=[
            Member(id="m1", name="メンバー1", prompt="テストプロンプト"),
            Member(id="m2", name="メンバー2", prompt="テストプロンプト"),
        ],
        steps=steps,
    )


def _make_steps_no_fallback() -> list[Step]:
    return [
        Step(
            id="step1",
            name="ステップ1",
            members=["m1"],
            description="テスト",
            output="アウトプット1",
            rounds=1,
        ),
        Step(
            id="step2",
            name="ステップ2",
            members=["m1", "m2"],
            description="テスト",
            output="アウトプット2",
            rounds=1,
        ),
    ]


def _make_steps_with_fallback() -> list[Step]:
    return [
        Step(
            id="step1",
            name="ステップ1",
            members=["m1"],
            description="テスト",
            output="アウトプット1",
            rounds=1,
        ),
        Step(
            id="step2",
            name="ステップ2",
            members=["m1", "m2"],
            description="テスト",
            output="アウトプット2",
            rounds=1,
            fallback=["step2", "step1"],
        ),
    ]


@pytest.mark.anyio
async def test_run_no_fallback() -> None:
    """全ステップ合格時は fallback_events が空で step_results が順序通り。"""
    gateway = MockAgentGateway()

    service = DiscussionService(agent_gateway=gateway)
    team = _make_team(_make_steps_no_fallback())
    log = await service.run(team, "テスト議題")

    assert len(log.step_results) == 2
    assert log.step_results[0].step_id == "step1"
    assert log.step_results[1].step_id == "step2"
    assert len(log.fallback_events) == 0


@pytest.mark.anyio
async def test_run_with_fallback() -> None:
    """step2 が不合格の場合、LLM が選んだ step1 から再実行し fallback_events に 1 件記録。"""
    gateway = MockAgentGateway()
    quality_eval_count = 0

    async def side_effect(*, member, conversation_history, system_context):
        nonlocal quality_eval_count
        if member.id == "quality_evaluator":
            quality_eval_count += 1
            if quality_eval_count == 1:
                return "判定: 不合格\n差し戻し先: step1\n理由: 前ステップの情報が不足"
            return "判定: 合格"
        return "テスト応答"

    gateway.set_side_effect(side_effect)

    service = DiscussionService(agent_gateway=gateway)
    team = _make_team(_make_steps_with_fallback())
    log = await service.run(team, "テスト議題")

    assert len(log.fallback_events) == 1
    assert log.fallback_events[0].failed_step_id == "step2"
    assert log.fallback_events[0].fallback_target_step_id == "step1"
    assert log.fallback_events[0].reason == "前ステップの情報が不足"

    assert len(log.step_results) == 2
    assert log.step_results[0].step_id == "step1"
    assert log.step_results[1].step_id == "step2"


@pytest.mark.anyio
async def test_run_with_self_fallback() -> None:
    """step2 が自身を選択した場合に step2 から再実行される。"""
    gateway = MockAgentGateway()
    quality_eval_count = 0

    async def side_effect(*, member, conversation_history, system_context):
        nonlocal quality_eval_count
        if member.id == "quality_evaluator":
            quality_eval_count += 1
            if quality_eval_count == 1:
                return "判定: 不合格\n差し戻し先: step2\n理由: 議論の進め方に問題がある"
            return "判定: 合格"
        return "テスト応答"

    gateway.set_side_effect(side_effect)

    service = DiscussionService(agent_gateway=gateway)
    team = _make_team(_make_steps_with_fallback())
    log = await service.run(team, "テスト議題")

    assert len(log.fallback_events) == 1
    assert log.fallback_events[0].failed_step_id == "step2"
    assert log.fallback_events[0].fallback_target_step_id == "step2"
    assert log.fallback_events[0].reason == "議論の進め方に問題がある"

    # step1 の結果は巻き戻されず、step2 のみ再実行
    assert len(log.step_results) == 2
    assert log.step_results[0].step_id == "step1"
    assert log.step_results[1].step_id == "step2"


@pytest.mark.anyio
async def test_fallback_max_once() -> None:
    """同一ステップの fallback は 1 回のみ。2 回目の不合格でもそのまま進行。"""
    gateway = MockAgentGateway()

    async def side_effect(*, member, conversation_history, system_context):
        if member.id == "quality_evaluator":
            return "判定: 不合格\n差し戻し先: step1\n理由: 不足"
        return "テスト応答"

    gateway.set_side_effect(side_effect)

    service = DiscussionService(agent_gateway=gateway)
    team = _make_team(_make_steps_with_fallback())
    log = await service.run(team, "テスト議題")

    assert len(log.fallback_events) == 1
    assert len(log.step_results) == 2


@pytest.mark.anyio
async def test_evaluate_quality_pass() -> None:
    """「判定: 合格」を含む応答は is_passed=True を返す。"""
    gateway = MockAgentGateway()
    gateway.set_return_value("結論は十分です。判定: 合格")

    service = DiscussionService(agent_gateway=gateway)
    result = await service._evaluate_step_quality(
        conclusion="テスト結論",
        expected_output="期待される出力",
        step_name="ステップ1",
        topic="テスト議題",
    )
    assert result.is_passed is True


@pytest.mark.anyio
async def test_evaluate_quality_fail() -> None:
    """「判定: 不合格」を含む応答は is_passed=False を返す。"""
    gateway = MockAgentGateway()
    gateway.set_return_value(
        "具体性が不足しています。\n判定: 不合格\n差し戻し先: step1\n理由: 具体性が不足"
    )

    service = DiscussionService(agent_gateway=gateway)
    result = await service._evaluate_step_quality(
        conclusion="テスト結論",
        expected_output="期待される出力",
        step_name="ステップ1",
        topic="テスト議題",
        fallback_candidates=[
            {"id": "step1", "name": "ステップ1", "description": "テスト"},
        ],
    )
    assert result.is_passed is False
    assert result.fallback_target_step_id == "step1"
    assert result.reason == "具体性が不足"


@pytest.mark.anyio
async def test_evaluate_quality_fail_invalid_target() -> None:
    """無効な step ID の場合、候補リストの先頭にフォールバック。"""
    gateway = MockAgentGateway()
    gateway.set_return_value(
        "判定: 不合格\n差し戻し先: invalid_step\n理由: テスト"
    )

    service = DiscussionService(agent_gateway=gateway)
    result = await service._evaluate_step_quality(
        conclusion="テスト結論",
        expected_output="期待される出力",
        step_name="ステップ2",
        topic="テスト議題",
        fallback_candidates=[
            {"id": "step2", "name": "ステップ2", "description": "自身"},
            {"id": "step1", "name": "ステップ1", "description": "前ステップ"},
        ],
    )
    assert result.is_passed is False
    assert result.fallback_target_step_id == "step2"  # 先頭候補


@pytest.mark.anyio
async def test_evaluate_quality_parse_fallback() -> None:
    """パース不能な応答は is_passed=True（安全側に倒す）。"""
    gateway = MockAgentGateway()
    gateway.set_return_value("よくわかりません")

    service = DiscussionService(agent_gateway=gateway)
    result = await service._evaluate_step_quality(
        conclusion="テスト結論",
        expected_output="期待される出力",
        step_name="ステップ1",
        topic="テスト議題",
    )
    assert result.is_passed is True


def test_build_conclusions_with_failed() -> None:
    """失敗コンテキストが正しいラベルで含まれる。"""
    gateway = MockAgentGateway()
    service = DiscussionService(agent_gateway=gateway)

    step_results = [
        StepResult(
            step_id="step1", step_name="ステップ1", description="テスト", conclusion="結論1"
        ),
    ]
    failed_step_results = [
        StepResult(
            step_id="step2", step_name="ステップ2", description="テスト", conclusion="失敗した結論"
        ),
    ]

    context = service._build_step_conclusions_context(step_results, failed_step_results)

    assert "【前回のステップ2の結論（品質不足で差し戻し）】" in context
    assert "失敗した結論" in context
    assert "【ステップ1の結論】" in context
    assert "結論1" in context

    # 失敗コンテキストが先に表示される
    failed_pos = context.index("前回のステップ2")
    normal_pos = context.index("ステップ1の結論")
    assert failed_pos < normal_pos
