"""RAG 工具（精简版）：纯 Python TF-IDF 检索，无 Qdrant / embedding 依赖。

流程：add_text 入库 -> 自动分块 -> 检索时用 TF-IDF 余弦相似度排序。
这是「无重型依赖」的兜底实现，用于离线演示 RAG 的核心思想（chunk -> retrieve）。
如需向量检索/文档解析，可在此基础上接入 Qdrant + embedding + markitdown。
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..base import Tool, ToolParameter


@dataclass
class Chunk:
    text: str
    tokens: List[str] = field(default_factory=list)


def _tokenize(text: str) -> List[str]:
    """简单分词：按非字母数字与中文字符切分，中文按字切。"""
    # 英文按单词，中文按单字，兼顾两种语言的检索
    tokens = re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]", text.lower())
    return tokens


def _split_chunks(text: str, chunk_size: int = 120) -> List[str]:
    """按句子边界粗略分块，每块累计长度不超过 chunk_size。"""
    sentences = re.split(r"(?<=[。！？.!?\n])", text)
    chunks, buf = [], ""
    for s in sentences:
        if not s.strip():
            continue
        if len(buf) + len(s) > chunk_size and buf:
            chunks.append(buf.strip())
            buf = s
        else:
            buf += s
    if buf.strip():
        chunks.append(buf.strip())
    return chunks or [text]


class RAGTool(Tool):
    """基于 TF-IDF 的轻量检索工具。"""

    def __init__(self, chunk_size: int = 120):
        super().__init__(
            name="RAG",
            description=(
                "知识检索工具。action=add_text 入库(text)，"
                "action=search 检索(query, limit)，action=stats 统计。"
            ),
        )
        self.chunk_size = chunk_size
        self._chunks: List[Chunk] = []

    def add_text(self, text: str) -> int:
        """把文本分块入库，返回新增块数。"""
        new_chunks = [Chunk(text=c, tokens=_tokenize(c)) for c in _split_chunks(text, self.chunk_size)]
        self._chunks.extend(new_chunks)
        return len(new_chunks)

    def _idf(self, token: str) -> float:
        df = sum(1 for ch in self._chunks if token in ch.tokens)
        if df == 0:
            return 0.0
        return math.log((1 + len(self._chunks)) / (1 + df)) + 1.0

    def _score(self, query_tokens: List[str], chunk: Chunk) -> float:
        """TF-IDF 余弦相似度（简化版）。"""
        if not chunk.tokens or not query_tokens:
            return 0.0
        q_tf = Counter(query_tokens)
        c_tf = Counter(chunk.tokens)
        common = set(q_tf) & set(c_tf)
        if not common:
            return 0.0
        dot = sum(q_tf[t] * c_tf[t] * (self._idf(t) ** 2) for t in common)
        q_norm = math.sqrt(sum((q_tf[t] * self._idf(t)) ** 2 for t in q_tf))
        c_norm = math.sqrt(sum((c_tf[t] * self._idf(t)) ** 2 for t in c_tf))
        if q_norm == 0 or c_norm == 0:
            return 0.0
        return dot / (q_norm * c_norm)

    def search(self, query: str, limit: int = 3) -> List[str]:
        q_tokens = _tokenize(query)
        scored = [(self._score(q_tokens, ch), ch) for ch in self._chunks]
        scored = [(s, ch) for s, ch in scored if s > 0]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ch.text for _, ch in scored[:limit]]

    def run(self, parameters: Dict[str, Any]) -> str:
        action = parameters.get("action", "search")
        if action == "add_text":
            text = parameters.get("text", "")
            if not text:
                return "错误：add_text 需要 text 参数。"
            n = self.add_text(text)
            return f"已入库 {n} 个文本块。"
        if action == "search":
            results = self.search(parameters.get("query", ""), int(parameters.get("limit", 3)))
            if not results:
                return "（未检索到相关内容）"
            return "\n\n".join(f"[{i + 1}] {r}" for i, r in enumerate(results))
        if action == "stats":
            return f"知识库块数: {len(self._chunks)}"
        return f"错误：未知 action '{action}'。"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="action", type="string", description="add_text/search/stats"),
            ToolParameter(name="text", type="string", description="add_text 时入库的文本", required=False),
            ToolParameter(name="query", type="string", description="search 时的查询", required=False),
            ToolParameter(name="limit", type="integer", description="返回块数", required=False, default=3),
        ]
