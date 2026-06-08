"""MCP（Model Context Protocol）适配器骨架。

把 MCP server 暴露的工具适配成 my_agents 的 Tool，注册进 ToolRegistry。
MCP 的官方 SDK（mcp / fastmcp）为可选依赖：未安装时不报错，调用时给出友好提示，
保证框架在无该依赖的离线环境也能正常导入与运行（优雅降级）。

真实接入步骤（需安装 mcp 并起一个 MCP server）：
    adapter = MCPToolAdapter(server_command=["python", "my_mcp_server.py"])
    adapter.connect()
    registry.register_tool(adapter.as_tool("add"))
"""

from typing import Any, Dict, List, Optional

from ..tools.base import Tool, ToolParameter

try:  # 可选依赖探测
    import mcp  # noqa: F401

    _MCP_AVAILABLE = True
except Exception:
    _MCP_AVAILABLE = False


def mcp_available() -> bool:
    """运行时查询 MCP SDK 是否可用。"""
    return _MCP_AVAILABLE


class MCPTool(Tool):
    """把单个 MCP 远程工具封装为本地 Tool。"""

    def __init__(self, adapter: "MCPToolAdapter", tool_name: str, description: str):
        super().__init__(name=tool_name, description=description or f"MCP 工具 {tool_name}")
        self._adapter = adapter
        self._tool_name = tool_name

    def run(self, parameters: Dict[str, Any]) -> str:
        return self._adapter.call_tool(self._tool_name, parameters)

    def get_parameters(self) -> List[ToolParameter]:
        # MCP 工具参数 schema 在 connect 后可从 server 获取，这里给通用占位
        return [ToolParameter(name="input", type="string", description="传给 MCP 工具的输入", required=False)]


class MCPToolAdapter:
    """MCP server 连接适配器（骨架）。"""

    def __init__(self, server_command: Optional[List[str]] = None):
        self.server_command = server_command or []
        self._connected = False

    def connect(self) -> bool:
        """连接 MCP server。未安装 mcp SDK 时返回 False 并提示。"""
        if not _MCP_AVAILABLE:
            print("提示：未安装 MCP SDK（pip install mcp），无法连接真实 MCP server。")
            return False
        # 真实实现：用 mcp 的 stdio client 启动 server_command 并握手。
        # 此处保留骨架，避免在离线环境引入运行时副作用。
        self._connected = True
        return True

    def list_tools(self) -> List[str]:
        if not self._connected:
            return []
        # 真实实现：return [t.name for t in client.list_tools()]
        return []

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        if not _MCP_AVAILABLE:
            return "错误：未安装 MCP SDK，无法调用 MCP 工具。请 pip install mcp 并连接 server。"
        if not self._connected:
            return "错误：尚未连接 MCP server，请先调用 connect()。"
        # 真实实现：return client.call_tool(tool_name, arguments)
        return f"(MCP 调用占位) {tool_name}({arguments})"

    def as_tool(self, tool_name: str, description: str = "") -> MCPTool:
        """把指定 MCP 工具包装成可注册进 ToolRegistry 的 Tool。"""
        return MCPTool(self, tool_name, description)
