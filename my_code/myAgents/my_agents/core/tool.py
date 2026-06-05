"""向后兼容层：保留早期 core/tool.py 的对外接口。

历史代码使用 `from ...core.tool import search, ToolExecutor`，并调用
register_tool / get_tool / list_tools。这里让 ToolExecutor 继承新的
ToolRegistry，既复用新实现，又保留旧方法名，确保旧代码无需改动即可运行。
"""

from typing import Callable

from ..tools.builtin.search import search  # noqa: F401  (对外重新导出)
from ..tools.registry import ToolRegistry


class ToolExecutor(ToolRegistry):
    """兼容旧接口的工具执行器（底层即新的 ToolRegistry）。"""

    # 旧接口：register_tool(name, description, func) —— 参数顺序与新 ToolRegistry 不同，
    # 这里覆盖为旧签名（按名注册函数工具）。
    def register_tool(self, name: str, description: str, func: Callable) -> None:
        self.register_function(name, description, func)
        print(f"工具 '{name}' 注册成功")

    # 旧接口：驼峰命名别名
    def registerTool(self, name: str, description: str, func: Callable) -> None:
        self.register_function(name, description, func)
        print(f"工具 '{name}' 已注册。")

    def getTool(self, name: str) -> Callable:
        """返回一个 (str)->str 的可调用，未找到返回 None。"""
        if name not in self._tools:
            return None

        def _runner(tool_input: str) -> str:
            return self.execute_tool(name, tool_input)

        return _runner

    def getAvailableTools(self) -> str:
        return self.get_available_tools()

    def list_tools(self) -> None:
        """打印可用工具清单（旧接口为打印而非返回）。"""
        print(self.get_available_tools())


if __name__ == "__main__":
    executor = ToolExecutor()
    executor.register_tool(
        "Search",
        "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。",
        search,
    )
    print("\n--- 可用的工具 ---")
    executor.list_tools()
