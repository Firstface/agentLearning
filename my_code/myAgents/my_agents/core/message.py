"""消息系统：统一的对话消息数据结构。

设计原则「对内丰富，对外兼容」：内部携带 role/content/timestamp/metadata，
对外通过 to_dict() 输出 OpenAI Chat 接口所需的 {"role", "content"} 格式。
"""

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

# 限定合法角色，与 OpenAI Chat 规范一致
MessageRole = Literal["user", "assistant", "system", "tool"]


class Message(BaseModel):
    """单条对话消息。"""

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, str]:
        """转换为 OpenAI Chat 接口需要的最小字典。"""
        return {"role": self.role, "content": self.content}

    def __str__(self) -> str:
        return f"[{self.role}] {self.content}"
