"""Agent 抽象基类。

所有范式 Agent（ReAct / Simple / PlanSolve / Reflection）都继承自 Agent，
统一通过 run(input_text) 入口执行，并复用历史管理逻辑。
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .config import Config
from .llm_client import MyAgentLLM
from .message import Message


class Agent(ABC):
    """智能体基类：定义统一接口与通用历史管理。"""

    def __init__(
        self,
        name: str,
        llm: MyAgentLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
    ):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()
        self._history: List[Message] = []

    @abstractmethod
    def run(self, input_text: str, **kwargs) -> Optional[str]:
        """执行任务并返回最终答案。子类必须实现。"""
        raise NotImplementedError

    def add_message(self, message: Message) -> None:
        """追加一条历史消息，并按上限裁剪，避免无限增长。"""
        self._history.append(message)
        max_len = self.config.max_history_length
        if max_len and len(self._history) > max_len:
            self._history = self._history[-max_len:]

    def clear_history(self) -> None:
        self._history = []

    def get_history(self) -> List[Message]:
        """返回历史副本，避免外部直接修改内部状态。"""
        return list(self._history)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
