"""工作记忆（Working Memory）：纯内存实现，无外部依赖。

特性：
- 容量上限 + TTL 过期（模拟人类短期记忆的遗忘）
- 混合检索：关键词重叠 × 时间衰减 × 重要性权重
检索打分公式参考项目约定：
    score = 相关性 × exp(-decay * hours) × (0.8 + importance * 0.4)
重要性权重被限制在 [0.8, 1.2]。
"""

import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _tokenize(text: str) -> set:
    """分词：英文按单词、中文按单字，兼顾中英文检索（中文无空格）。"""
    return set(re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]", text.lower()))


@dataclass
class MemoryItem:
    """单条记忆。"""

    content: str
    importance: float = 0.5  # 0~1
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkingMemory:
    """短期工作记忆：容量受限、随时间衰减。"""

    def __init__(self, capacity: int = 50, ttl_seconds: float = 3600, decay: float = 0.1):
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        self.decay = decay  # 时间衰减系数（每小时）
        self._items: List[MemoryItem] = []

    def add(self, content: str, importance: float = 0.5, metadata: Optional[Dict] = None) -> None:
        """新增一条记忆，超出容量时淘汰最旧的一条。"""
        self._items.append(
            MemoryItem(content=content, importance=importance, metadata=metadata or {})
        )
        self._evict_expired()
        if len(self._items) > self.capacity:
            # 容量溢出：丢弃最旧的
            self._items = self._items[-self.capacity:]

    def _evict_expired(self) -> None:
        """清除已过期（超过 TTL）的记忆。"""
        now = time.time()
        self._items = [
            it for it in self._items if now - it.timestamp <= self.ttl_seconds
        ]

    @staticmethod
    def _keyword_overlap(query: str, content: str) -> float:
        """基于词集合的 Jaccard 重叠度，作为轻量相关性。"""
        q = _tokenize(query)
        c = _tokenize(content)
        if not q or not c:
            return 0.0
        return len(q & c) / len(q | c)

    def retrieve(self, query: str, limit: int = 5) -> List[MemoryItem]:
        """按混合得分返回最相关的若干条记忆。"""
        self._evict_expired()
        now = time.time()
        scored = []
        for it in self._items:
            relevance = self._keyword_overlap(query, it.content)
            if relevance == 0:
                continue
            hours = (now - it.timestamp) / 3600.0
            time_decay = math.exp(-self.decay * hours)
            # 重要性权重限制在 [0.8, 1.2]
            importance_weight = 0.8 + max(0.0, min(1.0, it.importance)) * 0.4
            score = relevance * time_decay * importance_weight
            scored.append((score, it))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in scored[:limit]]

    def all(self) -> List[MemoryItem]:
        self._evict_expired()
        return list(self._items)

    def clear(self) -> None:
        self._items = []

    def __len__(self) -> int:
        self._evict_expired()
        return len(self._items)
