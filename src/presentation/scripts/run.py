"""チーム議論を実行するCLIスクリプト。"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from src.data.gateways.google_adk.agents.adk_agent_gateway import AdkAgentGateway
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
    agent_gateway = AdkAgentGateway(model=model)
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
    while True:
        topic = input("議論してほしい議題を入力してください: ").strip()
        if topic:
            return topic
        print("議題を入力してください。")


async def main() -> None:
    load_dotenv()
    usecase = create_usecase()

    team_id = select_team(usecase)
    topic = input_topic()

    print(f"\n議論を開始します...\n")
    report_path = await usecase.execute(team_id, topic)
    print(f"\n議論が完了しました。レポートを出力しました: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
