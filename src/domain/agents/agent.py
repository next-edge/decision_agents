"""エージェントのインタフェース定義。"""

from abc import ABC, abstractmethod

from src.domain.entities.team import Member


class AgentGateway(ABC):
    """LLMエージェントとの対話を担当するゲートウェイのインタフェース。"""

    @abstractmethod
    async def generate_response(
        self,
        member: Member,
        conversation_history: list[dict[str, str]],
        system_context: str,
    ) -> str:
        """メンバーの設定と会話履歴に基づいて応答を生成する。

        Args:
            member: 発言するメンバーの定義。
            conversation_history: これまでの会話履歴。
                各要素は {"role": "user"|"agent", "name": str, "text": str}。
            system_context: フェーズの目的等、追加のシステムコンテキスト。

        Returns:
            エージェントの応答テキスト。
        """
