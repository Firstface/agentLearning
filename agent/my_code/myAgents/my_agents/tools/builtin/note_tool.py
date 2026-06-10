"""笔记工具（NoteTool）：把笔记以 Markdown 文件 + JSON 索引落盘。

支持 action：create / read / update / list / search / delete。
纯本地、零依赖，适合给 Agent 做"工作记忆外置"（把发现写进笔记，后续再查）。
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List

from ..base import Tool, ToolParameter


class NoteTool(Tool):
    """基于文件系统的笔记工具。"""

    def __init__(self, workspace: str = "./notes"):
        super().__init__(
            name="Note",
            description=(
                "笔记工具。action=create 新建(title, content)，"
                "action=read 读取(title)，action=update 更新(title, content)，"
                "action=list 列出全部，action=search 搜索(query)，action=delete 删除(title)。"
            ),
        )
        self.workspace = workspace
        os.makedirs(self.workspace, exist_ok=True)
        self.index_path = os.path.join(self.workspace, "notes_index.json")
        self._index: Dict[str, Dict] = self._load_index()

    def _load_index(self) -> Dict[str, Dict]:
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_index(self) -> None:
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _safe_name(title: str) -> str:
        # 防路径穿越：只保留安全字符
        name = re.sub(r"[^\w\u4e00-\u9fff-]", "_", title)
        return name or "untitled"

    def _path(self, title: str) -> str:
        return os.path.join(self.workspace, self._safe_name(title) + ".md")

    def run(self, parameters: Dict[str, Any]) -> str:
        action = parameters.get("action", "list")
        title = parameters.get("title", "")
        content = parameters.get("content", "")

        if action == "create":
            if not title:
                return "错误：create 需要 title。"
            path = self._path(title)
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n{content}\n")
            self._index[title] = {"path": path, "updated": datetime.now().isoformat()}
            self._save_index()
            return f"已创建笔记: {title}"

        if action == "read":
            if title not in self._index:
                return f"错误：笔记 '{title}' 不存在。"
            with open(self._index[title]["path"], "r", encoding="utf-8") as f:
                return f.read()

        if action == "update":
            if title not in self._index:
                return f"错误：笔记 '{title}' 不存在，请先 create。"
            with open(self._index[title]["path"], "a", encoding="utf-8") as f:
                f.write(f"\n{content}\n")
            self._index[title]["updated"] = datetime.now().isoformat()
            self._save_index()
            return f"已更新笔记: {title}"

        if action == "list":
            if not self._index:
                return "（暂无笔记）"
            return "\n".join(f"- {t}" for t in self._index)

        if action == "search":
            query = parameters.get("query", "").lower()
            hits = []
            for t, meta in self._index.items():
                try:
                    with open(meta["path"], "r", encoding="utf-8") as f:
                        body = f.read()
                except Exception:
                    continue
                if query in t.lower() or query in body.lower():
                    hits.append(t)
            return "\n".join(f"- {t}" for t in hits) if hits else "（未找到匹配笔记）"

        if action == "delete":
            if title not in self._index:
                return f"错误：笔记 '{title}' 不存在。"
            try:
                os.remove(self._index[title]["path"])
            except OSError:
                pass
            del self._index[title]
            self._save_index()
            return f"已删除笔记: {title}"

        if action == "summary":
            return self._summary()

        return f"错误：未知 action '{action}'。"

    def _summary(self, recent_limit: int = 5) -> str:
        """生成笔记库的概览（结构化）。

        设计要点（参考 chapter9 NoteTool）：
        - **聚合统计**字段（total_notes / type_distribution）始终全量，
          因为它们只占常数 token，不会随笔记数量爆炸。
        - **列表**字段（recent_notes）只取最近 N 条，避免大量笔记把
          上下文撑爆。LLM 拿到 id 后可用 read(title=...) 二级展开看正文。
        """
        if not self._index:
            return "笔记库为空（共 0 篇）。"

        # 1) 计算聚合统计（type 来自 metadata，无则归为 'note'）
        items = []
        type_dist: Dict[str, int] = {}
        for t, meta in self._index.items():
            note_type = meta.get("type", "note")
            type_dist[note_type] = type_dist.get(note_type, 0) + 1
            try:
                with open(meta["path"], "r", encoding="utf-8") as f:
                    body = f.read()
            except Exception:
                body = ""
            items.append(
                {
                    "title": t,
                    "type": note_type,
                    "updated": meta.get("updated", ""),
                    "char_count": len(body),
                    "preview": next(
                        (
                            ln[:30]
                            for ln in body.splitlines()
                            if ln.strip() and not ln.startswith("# ")
                        ),
                        "(空)",
                    ),
                }
            )

        # 2) 按更新时间倒序，截断到 recent_limit
        items.sort(key=lambda x: x["updated"], reverse=True)
        recent = items[:recent_limit]

        # 3) 渲染：先聚合，再列表
        lines = [
            f"笔记库概览（共 {len(self._index)} 篇）：",
            f"- 类型分布: {type_dist}",
            f"- 最近 {len(recent)} 篇（按更新时间倒序，更早的请用 search/read 查看）:",
        ]
        for it in recent:
            lines.append(
                f"  · [{it['type']}] {it['title']} | {it['char_count']} 字"
                f" | 更新于 {it['updated'][:19].replace('T', ' ')} | 预览: {it['preview']}"
            )
        return "\n".join(lines)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="action", type="string", description="create/read/update/list/search/delete/summary"),
            ToolParameter(name="title", type="string", description="笔记标题", required=False),
            ToolParameter(name="content", type="string", description="笔记内容", required=False),
            ToolParameter(name="query", type="string", description="搜索关键词", required=False),
        ]
