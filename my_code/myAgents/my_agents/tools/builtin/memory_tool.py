"""记忆工具（MemoryTool）：把工作记忆封装成统一 action 调度的 Tool。

支持的 action：
- add     ：新增记忆     参数 content, importance
- search  ：检索记忆     参数 query, limit
- summary ：列出全部记忆
- stats   ：统计信息
- clear   ：清空记忆

精简版仅内置 working 记忆（纯内存、无外部依赖）。
episodic / semantic / perceptual 等长期记忆需 Qdrant/Neo4j/CLIP，此处预留扩展位。
"""

from typing import Any, Dict, List

from ...core.memory import WorkingMemory
from ..base import Tool, ToolParameter


class MemoryTool(Tool):
    """统一的记忆管理工具（精简版：working memory）。"""

    def __init__(self, capacity: int = 50, ttl_seconds: float = 3600):
        super().__init__(
            name="Memory",
            description=(
                "记忆工具。可保存与检索短期记忆。"
                "action=add 保存(content, importance)，"
                "action=search 检索(query, limit)，"
                "action=summary 列出全部，action=stats 统计，action=clear 清空。"
            ),
        )
        self.working = WorkingMemory(capacity=capacity, ttl_seconds=ttl_seconds)

    def run(self, parameters: Dict[str, Any]) -> str:
        action = parameters.get("action", "search")

        if action == "add":
            content = parameters.get("content", "")
            if not content:
                return "错误：add 需要 content 参数。"
            importance = float(parameters.get("importance", 0.5))
            self.working.add(content, importance=importance)
            return f"已记住: {content}"

        if action == "search":
            query = parameters.get("query", "")
            limit = int(parameters.get("limit", 5))
            items = self.working.retrieve(query, limit=limit)
            if not items:
                return "（未检索到相关记忆）"
            return "\n".join(f"- {it.content}" for it in items)

        if action == "summary":
            items = self.working.all()
            if not items:
                return "（暂无记忆）"
            return "\n".join(f"- {it.content}" for it in items)

        if action == "stats":
            return f"当前记忆条数: {len(self.working)} / 容量 {self.working.capacity}"

        if action == "clear":
            self.working.clear()
            return "已清空记忆。"

        return f"错误：未知 action '{action}'。"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="action", type="string", description="add/search/summary/stats/clear"),
            ToolParameter(name="content", type="string", description="add 时要保存的内容", required=False),
            ToolParameter(name="query", type="string", description="search 时的查询", required=False),
            ToolParameter(name="importance", type="number", description="重要性 0~1", required=False, default=0.5),
            ToolParameter(name="limit", type="integer", description="检索返回条数", required=False, default=5),
        ]
