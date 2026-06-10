"""SimpleAgent：最简单的单轮对话 Agent，不带工具循环。

适合普通问答场景，演示 Agent 基类的最小实现。
"""

from typing import Optional

from ..core.agent import Agent
from ..core.config import Config
from ..core.exceptions import LLMError
from ..core.llm_client import MyAgentLLM
from ..core.message import Message


class SimpleAgent(Agent):
    """单轮对话智能体。"""

    def __init__(
        self,
        llm: MyAgentLLM,
        name: str = "SimpleAgent",
        system_prompt: Optional[str] = "你是一个有用的 AI 助手。",
        config: Optional[Config] = None,
    ):
        super().__init__(name=name, llm=llm, system_prompt=system_prompt, config=config)

    def run(self, input_text: str, **kwargs) -> Optional[str]:
        """带历史的单轮对话。"""
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        # 带上历史，支持多轮
        messages.extend(m.to_dict() for m in self._history)
        messages.append({"role": "user", "content": input_text})

        try:
            answer = self.llm.think(messages)
        except LLMError as e:
            print(f"\n错误：LLM 调用失败。{e}")
            return None

        # 记录历史
        self.add_message(Message(role="user", content=input_text))
        self.add_message(Message(role="assistant", content=answer))
        return answer
