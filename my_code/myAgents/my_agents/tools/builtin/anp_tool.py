"""ANP 工具：把 ANP 服务发现/调用能力接入 ToolRegistry。

让 Agent 能通过统一的工具接口去发现并调用网络中其它"智能体服务"。
基于纯内存的 ANPNetwork，零外部依赖。
"""

from typing import Any, Dict, List

from ...protocols.anp import ANPNetwork
from ..base import Tool, ToolParameter


class ANPTool(Tool):
    """智能体网络服务发现与调用工具。"""

    def __init__(self, network: ANPNetwork = None):
        super().__init__(
            name="ANP",
            description=(
                "智能体网络工具。action=list 列出可用服务，"
                "action=discover 发现服务(service)，"
                "action=invoke 调用服务(service, payload)。"
            ),
        )
        self.network = network or ANPNetwork()

    def run(self, parameters: Dict[str, Any]) -> str:
        action = parameters.get("action", "list")
        if action == "list":
            services = self.network.list_services()
            return "\n".join(f"- {s}" for s in services) if services else "（暂无服务）"
        if action == "discover":
            service = parameters.get("service", "")
            found = self.network.registry.discover_service(service)
            if not found:
                return f"未发现服务 '{service}'。"
            return f"服务 '{service}' 有 {len(found)} 个提供者。"
        if action == "invoke":
            service = parameters.get("service", "")
            payload = parameters.get("payload", "")
            return self.network.invoke_balanced(service, payload)
        return f"错误：未知 action '{action}'。"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="action", type="string", description="list/discover/invoke"),
            ToolParameter(name="service", type="string", description="服务名", required=False),
            ToolParameter(name="payload", type="string", description="调用服务时的输入", required=False),
        ]
