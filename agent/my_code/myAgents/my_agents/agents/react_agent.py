"""ReAct 范式 Agent：推理(Reasoning) + 行动(Acting) 循环。

Thought -> Action -> Observation 不断迭代，直到模型给出 Finish[...] 或达到最大步数。

相比早期实现，这里修复了若干健壮性问题：
1. 退出原因区分清晰，不再「解析失败」却打印「已达到最大步数」。
2. Action 正则使用明确的结束边界，避免非贪婪匹配到空串。
3. 工具入参自动去除首尾引号，兼容 Search["xxx"] 这类写法。
4. 单步工具执行包 try/except，单个工具报错不会中断整个循环。
"""

import re
from typing import Optional, Tuple

from ..core.agent import Agent
from ..core.config import Config
from ..core.exceptions import LLMError, MyAgentError
from ..core.llm_client import MyAgentLLM
from ..tools.registry import ToolRegistry

REACT_PROMPT_TEMPLATE = """请注意，你是一个有能力调用外部工具的智能助手。

可用工具如下:
{tools}

请严格按照以下格式进行回应:

Thought: 你的思考过程，用于分析问题、拆解任务和规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一:
- `工具名[工具输入]`: 调用一个可用工具。
- `Finish[最终答案]`: 当你收集到足够的信息能够回答问题时，必须使用它输出最终答案。

每次回应只能包含一个 Thought 和一个 Action。

现在，请开始解决以下问题:
Question: {question}
History:
{history}
"""


class ReActAgent(Agent):
    """ReAct 智能体。"""

    def __init__(
        self,
        llm: MyAgentLLM,
        tool_registry: ToolRegistry,
        max_steps: int = 5,
        name: str = "ReActAgent",
        config: Optional[Config] = None,
        prompt_template: str = REACT_PROMPT_TEMPLATE,
    ):
        super().__init__(name=name, llm=llm, config=config)
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.prompt_template = prompt_template
        self._trace: list[str] = []

    def run(self, input_text: str, **kwargs) -> Optional[str]:
        """运行 ReAct 循环来回答问题。"""
        self._trace = []  # 每次运行重置思考-行动轨迹

        for step in range(1, self.max_steps + 1):
            print(f"--- 第 {step} 步 ---")

            prompt = self.prompt_template.format(
                tools=self.tool_registry.get_available_tools(),
                question=input_text,
                history="\n".join(self._trace) if self._trace else "（暂无）",
            )

            # 1. 调用 LLM 思考（流式打印）
            try:
                response_text = self.llm.think([{"role": "user", "content": prompt}])
            except LLMError as e:
                print(f"\n错误：LLM 调用失败，流程终止。{e}")
                return None

            if not response_text:
                print("错误：LLM 未返回有效响应，流程终止。")
                return None

            # 2. 解析 Thought / Action
            thought, action = self._parse_output(response_text)
            if thought:
                print(f"思考: {thought}")

            if not action:
                print("警告：未能解析出有效的 Action，流程终止。")
                return None

            # 3. Finish -> 返回最终答案
            cleaned_action = self._clean_action(action)
            if cleaned_action.startswith("Finish"):
                final_answer = self._parse_action_input(cleaned_action)
                print(f"🎉 最终答案: {final_answer}")
                return final_answer

            # 4. 解析并执行工具
            tool_name, tool_input = self._parse_action(cleaned_action)
            if not tool_name:
                # Action 格式非法，记录后让模型在下一轮自我修正
                print("警告：Action 格式无效。")
                self._trace.append(f"Action: {action}")
                self._trace.append("Observation: 无效的 Action 格式，请使用 工具名[输入] 或 Finish[答案]。")
                continue

            print(f"🎬 行动: {tool_name}[{tool_input}]")
            try:
                observation = self.tool_registry.execute_tool(tool_name, tool_input)
            except MyAgentError as e:
                observation = f"错误: {e}"
            except Exception as e:
                observation = f"工具执行异常: {e}"

            print(f"👀 观察: {observation}")
            self._trace.append(f"Action: {action}")
            self._trace.append(f"Observation: {observation}")

        # 正常跑满步数仍未 Finish
        print("已达到最大步数，流程终止。")
        return None

    def _parse_output(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """从模型输出中解析 Thought 与 Action。"""
        thought_match = re.search(
            r"Thought:\s*(.*?)(?=\nAction:|\Z)", text, re.DOTALL
        )
        # Action 取到下一关键字或文本结尾，避免非贪婪匹配到空串
        action_match = re.search(
            r"Action:\s*(.+?)(?=\nThought:|\nObservation:|\Z)", text, re.DOTALL
        )
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    @staticmethod
    def _clean_action(action_text: str) -> str:
        """去除模型可能附加的反引号/代码块包裹，便于解析。"""
        return action_text.strip().strip("`").strip()

    def _parse_action(self, action_text: str) -> Tuple[Optional[str], Optional[str]]:
        """解析 工具名[输入]，并去除输入首尾引号。"""
        match = re.match(r"(\w+)\s*\[(.*)\]\s*$", self._clean_action(action_text), re.DOTALL)
        if not match:
            return None, None
        name = match.group(1).strip()
        arg = match.group(2).strip().strip('"').strip("'")
        return name, arg

    def _parse_action_input(self, action_text: str) -> str:
        """提取 Finish[...] 中括号内的最终答案。"""
        match = re.match(r"\w+\s*\[(.*)\]\s*$", self._clean_action(action_text), re.DOTALL)
        return match.group(1).strip() if match else ""
