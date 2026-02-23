"""チーム議論を実行するCLIスクリプト。"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from prompt_toolkit import prompt as pt_prompt

from src.data.gateways.google_adk.agents.adk_agent_gateway import AdkAgentGateway
from src.data.gateways.google_adk.tools.registry import create_default_registry
from src.data.repositories.yaml_team_repository import YamlTeamRepository
from src.domain.services.discussion_service import DiscussionService
from src.domain.services.report_service import ReportService
from src.presentation.usecases.run_discussion import RunDiscussionUsecase

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEAMS_DIR = PROJECT_ROOT / "configs" / "teams"
OUTPUT_DIR = PROJECT_ROOT / "outputs"


def create_usecase() -> RunDiscussionUsecase:
    model = os.environ.get("LLM_MODEL_AGENT", "gemini-2.5-flash")
    team_repository = YamlTeamRepository(TEAMS_DIR)
    tool_registry = create_default_registry()
    agent_gateway = AdkAgentGateway(model=model, tool_registry=tool_registry)
    discussion_service = DiscussionService(
        agent_gateway=agent_gateway,
        on_progress=lambda msg: print(msg),
    )
    report_service = ReportService(output_dir=OUTPUT_DIR)
    return RunDiscussionUsecase(
        team_repository=team_repository,
        discussion_service=discussion_service,
        report_service=report_service,
    )


def select_team(usecase: RunDiscussionUsecase) -> str:
    teams = usecase.list_teams()
    if not teams:
        print("利用可能なチームがありません。")
        raise SystemExit(1)

    print("=== チーム選択 ===")
    for i, team in enumerate(teams, 1):
        print(f"  {i}. {team['name']} - {team['description']}")
    print()

    while True:
        choice = input(f"チームを選択してください (1-{len(teams)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(teams):
            selected = teams[int(choice) - 1]
            print(f"\n選択: {selected['name']}")
            return selected["id"]
        print("無効な選択です。もう一度入力してください。")


def input_topic() -> str:
    print("\n=== 議題入力 ===")
    print("（複数行入力可。確定: Alt+Enter / Esc→Enter）")
    while True:
        topic = pt_prompt("議題> ", multiline=True).strip()
        if topic:
            return topic
        print("議題を入力してください。")


async def run_discussion(usecase: RunDiscussionUsecase, team_id: str, topic: str) -> None:
    print(f"\n議論を開始します...\n")
    report_path = await usecase.execute(team_id, topic)
    print(f"\n議論が完了しました。レポートを出力しました: {report_path}")


def main() -> None:
    load_dotenv()
    usecase = create_usecase()

    team_id = select_team(usecase)
    topic = input_topic()

    asyncio.run(run_discussion(usecase, team_id, topic))


if __name__ == "__main__":
    main()
