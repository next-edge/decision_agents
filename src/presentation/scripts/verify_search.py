"""Google Search ツールの動作検証スクリプト。"""

import asyncio

from dotenv import load_dotenv
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.genai import types


async def main() -> None:
    load_dotenv()

    agent = Agent(
        name="cmo",
        model="gemini-2.5-flash",
        instruction="あなたは市場調査の専門家です。Google検索ツールを使って情報を調べてください。",
        tools=[GoogleSearchTool()],
    )

    session_service = InMemorySessionService()
    runner = Runner(app_name="verify", agent=agent, session_service=session_service)
    session = await session_service.create_session(app_name="verify", user_id="test")

    print("質問: 2025年の日本のSaaS市場規模を検索してください\n")

    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="2025年の日本のSaaS市場規模を検索してください")],
        ),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text, end="")

    print()


if __name__ == "__main__":
    asyncio.run(main())
