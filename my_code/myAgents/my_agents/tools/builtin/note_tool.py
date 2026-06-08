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

        return f"错误：未知 action '{action}'。"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="action", type="string", description="create/read/update/list/search/delete"),
            ToolParameter(name="title", type="string", description="笔记标题", required=False),
            ToolParameter(name="content", type="string", description="笔记内容", required=False),
            ToolParameter(name="query", type="string", description="搜索关键词", required=False),
        ]
