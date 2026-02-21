"""Google ADK を使ったエージェントゲートウェイの具象実装。"""

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.domain.agents.agent import AgentGateway
from src.domain.entities.team import Member


class AdkAgentGateway(AgentGateway):
    """Google ADK を利用してエージェントの応答を生成する。"""

    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self._model = model

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

        agent = Agent(
            name=member.id,
            model=self._model,
            instruction=instruction,
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
            f"上記の議論の目的とこれまでの議論を踏まえ、あなたの専門的な観点から意見を述べてください。"
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
