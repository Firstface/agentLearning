"""上下文工程：ContextBuilder（GSSC 流水线）。

把分散的信息源（系统指令、记忆、检索结果、对话历史）按相关性与新近性
筛选、组织、压缩成一段适合喂给 LLM 的上下文。

GSSC 四步：
- Gather   汇集所有候选信息（封装为 ContextPacket）
- Select   按 相关性×权重 + 新近性×权重 贪心选取，受 token 预算约束
- Structure 模板化拼装
- Compress 超出预算时截断

零外部依赖：相关性用 Jaccard 词重叠，新近性用指数衰减，token 用字符估算。
"""

import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _tokenize(text: str) -> set:
    """分词：英文按单词、中文按单字，兼顾中英文（中文无空格）。"""
    return set(re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]", text.lower()))


@dataclass
class ContextConfig:
    """上下文构建配置。"""

    max_tokens: int = 2000
    relevance_weight: float = 0.7
    recency_weight: float = 0.3
    min_relevance: float = 0.0
    recency_decay: float = 0.05  # 每小时衰减
    enable_compression: bool = True


@dataclass
class ContextPacket:
    """一段候选上下文。"""

    content: str
    source: str = "misc"  # system / memory / rag / history
    timestamp: float = field(default_factory=time.time)
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def token_count(self) -> int:
        # 粗略估算：中文按字、英文按 ~4 字符/token，这里统一用字符数/2 近似
        return max(1, len(self.content) // 2)


class ContextBuilder:
    """上下文构建器。memory_tool / rag_tool 为可选注入，实现与运行时解耦。"""

    def __init__(self, memory_tool=None, rag_tool=None, config: Optional[ContextConfig] = None):
        self.memory_tool = memory_tool
        self.rag_tool = rag_tool
        self.config = config or ContextConfig()

    def build(
        self,
        user_query: str,
        conversation_history: Optional[List[str]] = None,
        system_instructions: Optional[str] = None,
        custom_packets: Optional[List[ContextPacket]] = None,
    ) -> str:
        packets = self._gather(
            user_query, conversation_history, system_instructions, custom_packets
        )
        selected = self._select(user_query, packets)
        text = self._structure(selected)
        if self.config.enable_compression:
            text = self._compress(text)
        return text

    def _gather(self, query, history, system, custom) -> List[ContextPacket]:
        packets: List[ContextPacket] = []
        # 系统指令始终最高优先（用 source=system 在 select 中保底）
        if system:
            packets.append(ContextPacket(content=system, source="system"))
        # 记忆
        if self.memory_tool is not None:
            mem = self.memory_tool.run({"action": "search", "query": query, "limit": 5})
            if mem and "未检索" not in mem and "暂无" not in mem:
                packets.append(ContextPacket(content=mem, source="memory"))
        # 检索
        if self.rag_tool is not None:
            rag = self.rag_tool.run({"action": "search", "query": query, "limit": 3})
            if rag and "未检索" not in rag:
                packets.append(ContextPacket(content=rag, source="rag"))
        # 历史
        for i, h in enumerate(history or []):
            packets.append(
                ContextPacket(
                    content=h,
                    source="history",
                    # 越靠后的历史越新
                    timestamp=time.time() - (len(history) - i) * 60,
                )
            )
        # 自定义
        packets.extend(custom or [])
        return packets

    @staticmethod
    def _relevance(query: str, content: str) -> float:
        q = _tokenize(query)
        c = _tokenize(content)
        if not q or not c:
            return 0.0
        return len(q & c) / len(q | c)

    def _recency(self, ts: float) -> float:
        hours = (time.time() - ts) / 3600.0
        return math.exp(-self.config.recency_decay * hours)

    def _select(self, query: str, packets: List[ContextPacket]) -> List[ContextPacket]:
        """打分排序后在 token 预算内贪心选取。system 源始终保留。"""
        budget = self.config.max_tokens
        forced = [p for p in packets if p.source == "system"]
        others = [p for p in packets if p.source != "system"]

        for p in others:
            rel = self._relevance(query, p.content)
            rec = self._recency(p.timestamp)
            p.relevance_score = (
                self.config.relevance_weight * rel + self.config.recency_weight * rec
            )
        others.sort(key=lambda p: p.relevance_score, reverse=True)

        selected = list(forced)
        used = sum(p.token_count for p in forced)
        for p in others:
            if p.relevance_score < self.config.min_relevance:
                continue
            if used + p.token_count > budget:
                continue
            selected.append(p)
            used += p.token_count
        return selected

    @staticmethod
    def _structure(packets: List[ContextPacket]) -> str:
        labels = {
            "system": "## 系统指令",
            "memory": "## 相关记忆",
            "rag": "## 检索资料",
            "history": "## 对话历史",
            "misc": "## 补充信息",
        }
        # 按来源分组，保持稳定顺序
        order = ["system", "memory", "rag", "history", "misc"]
        sections = []
        for src in order:
            items = [p.content for p in packets if p.source == src]
            if items:
                sections.append(labels.get(src, "## 信息") + "\n" + "\n".join(items))
        return "\n\n".join(sections)

    def _compress(self, text: str) -> str:
        limit = self.config.max_tokens * 2  # token 估算约为字符数/2，故字符上限约 2x
        if len(text) <= limit:
            return text
        return text[:limit] + "\n...(上下文已截断)"
