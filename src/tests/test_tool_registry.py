"""ToolRegistry のテスト。"""

import pytest

from src.data.gateways.google_adk.tools.registry import ToolRegistry, create_default_registry


class TestToolRegistry:
    """ToolRegistry の単体テスト。"""

    def test_register_and_resolve(self) -> None:
        registry = ToolRegistry()
        dummy_tool = object()
        registry.register("my_tool", dummy_tool)
        assert registry.resolve("my_tool") is dummy_tool

    def test_resolve_unregistered_raises_key_error(self) -> None:
        registry = ToolRegistry()
        with pytest.raises(KeyError, match="unknown"):
            registry.resolve("unknown")

    def test_resolve_all(self) -> None:
        registry = ToolRegistry()
        tool_a = object()
        tool_b = object()
        registry.register("a", tool_a)
        registry.register("b", tool_b)
        resolved = registry.resolve_all(["a", "b"])
        assert resolved == [tool_a, tool_b]

    def test_resolve_all_empty(self) -> None:
        registry = ToolRegistry()
        assert registry.resolve_all([]) == []

    def test_resolve_all_with_unregistered_raises(self) -> None:
        registry = ToolRegistry()
        registry.register("a", object())
        with pytest.raises(KeyError):
            registry.resolve_all(["a", "missing"])


class TestCreateDefaultRegistry:
    """create_default_registry のテスト。"""

    def test_google_search_registered(self) -> None:
        registry = create_default_registry()
        tool = registry.resolve("google_search")
        assert tool is not None
        assert tool.name == "google_search"
