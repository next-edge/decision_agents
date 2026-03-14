"""Google ADK の最小動作確認スクリプト。

環境変数が正しく設定されていること、Vertex AI 経由でエージェントが応答することを確認する。
"""

import asyncio
import os

from dotenv import load_dotenv
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


async def main():
    load_dotenv()

    model = os.environ.get("LLM_MODEL_AGENT", "gemini-2.5-flash")
    print(f"--- モデル: {model} ---")

    agent = Agent(
        name="hello_agent",
        model=model,
        instruction="あなたは親切なアシスタントです。日本語で簡潔に応答してください。",
    )

    runner = Runner(
        app_name="decision_agents",
        agent=agent,
        session_service=InMemorySessionService(),
    )

    session = await runner.session_service.create_session(
        app_name="decision_agents",
        user_id="test_user",
    )

    print("--- エージェントにメッセージを送信中 ---")

    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="こんにちは！自己紹介をしてください。")],
        ),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}] {part.text}")

    print("--- 完了 ---")


if __name__ == "__main__":
    asyncio.run(main())
