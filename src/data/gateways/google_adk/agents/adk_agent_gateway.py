"""Google ADK を使ったエージェントゲートウェイの具象実装。"""

from __future__ import annotations

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.data.gateways.google_adk.tools.registry import ToolRegistry
from src.domain.agents.agent import AgentGateway
from src.domain.entities.team import Member


class AdkAgentGateway(AgentGateway):
    """Google ADK を利用してエージェントの応答を生成する。"""

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self._model = model
        self._tool_registry = tool_registry

    async def generate_response(
        self,
        member: Member,
        conversation_history: list[dict[str, str]],
        system_context: str,
    ) -> str:
        instruction = f"{member.prompt}\n\n【現在の議論の目的】\n{system_context}"

        history_text = self._format_history(conversation_history)
        if history_text:
            instruction += f"\n\n【これまでの議論】\n{history_text}"

        tools = []
        if self._tool_registry and member.tools:
            tools = self._tool_registry.resolve_all(member.tools)
            tool_names = ", ".join(member.tools)
            instruction += (
                f"\n\n【ツール利用ルール】\n"
                f"あなたには以下のツールが付与されています: {tool_names}\n"
                f"ツールで得た情報を引用する際は、以下のルールを厳守してください:\n"
                f"1. 検索結果から得た具体的な情報源名（組織名・レポート名・記事タイトル）と URL を必ず明記する\n"
                f"2. 数値データを引用する場合は、出典元の名称・発行年・URL をセットで記載する\n"
                f"3. 検索結果に含まれない情報を、あたかも検索で得たかのように記述しない\n"
                f"4. 発言末尾に「出典」セクションを設け、引用した情報源を箇条書きで一覧にする\n"
                f"\n"
                f"悪い例: 「Gartnerの調査によれば79%が〜」（調査名・年・URL なし）\n"
                f"良い例: 「Gartner『2024 CEO Survey』(https://...) によれば79%が〜」"
            )

        agent = Agent(
            name=member.id,
            model=self._model,
            instruction=instruction,
            tools=tools,
        )

        session_service = InMemorySessionService()
        runner = Runner(
            app_name="decision_agents",
            agent=agent,
            session_service=session_service,
        )

        session = await session_service.create_session(
            app_name="decision_agents",
            user_id="system",
        )

        prompt = (
            f"あなたは「{member.name}」として議論に参加しています。"
            f"上記の議論の目的とこれまでの議論を踏まえ、あなたの専門的な観点から意見を述べてください。\n\n"
            f"【発言ルール】\n"
            f"- 1回の発言は1〜2つの論点に絞り、500文字以内で簡潔に述べる\n"
            f"- 他のメンバーの直前の発言に対する応答・反論・補足を優先する\n"
            f"- 網羅的な分析レポートではなく、対話として自然なやり取りをする\n"
            f"- 自分の過去の発言内容を繰り返さない"
        )

        response_text = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=prompt)],
            ),
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text

        return response_text

    def _format_history(self, conversation_history: list[dict[str, str]]) -> str:
        if not conversation_history:
            return ""
        lines = []
        for entry in conversation_history:
            lines.append(f"【{entry['name']}】\n{entry['text']}")
        return "\n\n".join(lines)
