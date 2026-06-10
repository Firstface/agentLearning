"""工具基类与参数描述。

设计原则「万物皆为工具」：除核心 Agent 外的能力（搜索、计算、记忆、RAG…）
都抽象为 Tool。每个工具自描述其参数（get_parameters），统一通过 run 执行。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ToolParameter(BaseModel):
    """单个工具参数的元数据，用于自动生成说明与校验。"""

    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None


class Tool(ABC):
    """工具抽象基类。"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, parameters: Dict[str, Any]) -> str:
        """执行工具，接收参数字典，返回字符串结果。"""
        raise NotImplementedError

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]:
        """返回参数定义列表，供文档生成与参数校验。"""
        raise NotImplementedError

    def run_text(self, text_input: str) -> str:
        """便捷入口：以单个字符串调用工具。

        默认把字符串塞给第一个必填参数；若无参数定义则用 'input'。
        这样 ReAct 这类「工具名[字符串]」协议无需关心参数 schema。
        """
        params = self.get_parameters()
        key = params[0].name if params else "input"
        return self.run({key: text_input})
