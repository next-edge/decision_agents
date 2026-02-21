"""ツール短縮名から ADK ツールオブジェクトへの解決を行うレジストリ。"""

from __future__ import annotations

from typing import Any


class ToolRegistry:
    """短縮名 → ADK ツールオブジェクトのマッピングを管理する。"""

    def __init__(self) -> None:
        self._tools: dict[str, Any] = {}

    def register(self, name: str, tool: Any) -> None:
        """ツールを短縮名で登録する。"""
        self._tools[name] = tool

    def resolve(self, name: str) -> Any:
        """短縮名から ADK ツールオブジェクトを取得する。

        Raises:
            KeyError: 未登録のツール名が指定された場合。
        """
        if name not in self._tools:
            raise KeyError(f"ツール '{name}' は登録されていません")
        return self._tools[name]

    def resolve_all(self, names: list[str]) -> list[Any]:
        """複数の短縮名を一括で解決する。"""
        return [self.resolve(name) for name in names]


def create_default_registry() -> ToolRegistry:
    """デフォルトのツールレジストリを生成する。

    google_search を登録済みの状態で返す。
    """
    from google.adk.tools.google_search_tool import GoogleSearchTool

    registry = ToolRegistry()
    registry.register("google_search", GoogleSearchTool())
    return registry
