"""工具注册表。

统一管理两类工具：
- Tool 对象（复杂工具，带参数 schema）
- 裸函数（简单工具，签名为 (str) -> str）

对外屏蔽差异：execute_tool(name, input) 用统一的「字符串入/字符串出」调用，
get_available_tools() 生成可注入 prompt 的工具清单。
"""

from typing import Callable, Dict, List

from ..core.exceptions import ToolNotFoundError
from .base import Tool


class ToolRegistry:
    """工具注册与调度中枢。"""

    def __init__(self):
        # name -> {"description": str, "tool": Tool | None, "func": Callable | None}
        self._tools: Dict[str, dict] = {}

    def register_tool(self, tool: Tool) -> None:
        """注册一个 Tool 对象。"""
        if tool.name in self._tools:
            print(f"警告：工具 '{tool.name}' 已存在，将被覆盖。")
        self._tools[tool.name] = {
            "description": tool.description,
            "tool": tool,
            "func": None,
        }

    def register_function(
        self, name: str, description: str, func: Callable[[str], str]
    ) -> None:
        """注册一个裸函数工具（签名 (str) -> str）。"""
        if name in self._tools:
            print(f"警告：工具 '{name}' 已存在，将被覆盖。")
        self._tools[name] = {
            "description": description,
            "tool": None,
            "func": func,
        }

    def execute_tool(self, name: str, tool_input: str) -> str:
        """以字符串入/出的方式执行工具。"""
        if name not in self._tools:
            raise ToolNotFoundError(f"未找到名为 '{name}' 的工具。")
        entry = self._tools[name]
        if entry["tool"] is not None:
            return entry["tool"].run_text(tool_input)
        return entry["func"](tool_input)

    def get_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def get_available_tools(self) -> str:
        """生成可注入提示词的工具清单字符串。"""
        if not self._tools:
            return "（暂无可用工具）"
        return "\n".join(
            f"- {name}: {entry['description']}" for name, entry in self._tools.items()
        )
