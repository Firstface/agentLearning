"""配置管理：集中存放可调参数，支持从环境变量覆盖。"""

import os
from typing import Any, Dict, Optional

from pydantic import BaseModel


class Config(BaseModel):
    """框架运行配置。所有字段都有默认值，零配置即可运行。"""

    # LLM 相关
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    timeout: int = 60

    # 系统相关
    debug: bool = False
    max_history_length: int = 100

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量构造配置，未设置的项使用默认值。"""
        return cls(
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
            max_tokens=(
                int(os.getenv("LLM_MAX_TOKENS")) if os.getenv("LLM_MAX_TOKENS") else None
            ),
            timeout=int(os.getenv("LLM_TIMEOUT", "60")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            max_history_length=int(os.getenv("MAX_HISTORY_LENGTH", "100")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
