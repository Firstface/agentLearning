"""Plan-and-Solve 范式 Agent：先规划，后执行。

Planner 把复杂问题分解为有序子任务列表；Executor 逐步执行，
把已完成步骤的结果作为后续步骤的上下文。两者由本 Agent 编排（组合优于继承）。
"""

import ast
import re
from typing import List, Optional

from ..core.agent import Agent
from ..core.config import Config
from ..core.exceptions import LLMError
from ..core.llm_client import MyAgentLLM

PLANNER_PROMPT_TEMPLATE = """你是一个顶级的 AI 规划专家。请将用户的复杂问题分解为一个由多个简单步骤组成的行动计划。
每个步骤都应是独立、可执行的子任务，并按逻辑顺序排列。

问题: {question}

请严格按照以下格式输出计划，```python 与 ``` 前后缀是必要的:
```python
["步骤1", "步骤2", "步骤3"]
```
"""

EXECUTOR_PROMPT_TEMPLATE = """你是一位顶级的 AI 执行专家。请严格按照给定计划，一步步解决问题。
请专注于解决"当前步骤"，仅输出该步骤的最终答案，不要输出额外解释。

# 原始问题:
{question}

# 完整计划:
{plan}

# 历史步骤与结果:
{history}

# 当前步骤:
{current_step}

请仅输出针对"当前步骤"的回答:
"""


class PlanAndSolveAgent(Agent):
    """先规划后执行的智能体。"""

    def __init__(
        self,
        llm: MyAgentLLM,
        name: str = "PlanAndSolveAgent",
        config: Optional[Config] = None,
    ):
        super().__init__(name=name, llm=llm, config=config)

    def run(self, input_text: str, **kwargs) -> Optional[str]:
        plan = self._plan(input_text)
        if not plan:
            print("规划失败：未能生成有效计划。")
            return None
        print(f"📋 生成计划: {plan}")
        return self._execute(input_text, plan)

    def _plan(self, question: str) -> List[str]:
        """生成步骤列表。"""
        prompt = PLANNER_PROMPT_TEMPLATE.format(question=question)
        try:
            response = self.llm.think([{"role": "user", "content": prompt}])
        except LLMError as e:
            print(f"\n规划阶段 LLM 调用失败: {e}")
            return []
        return self._parse_plan(response)

    @staticmethod
    def _parse_plan(response: str) -> List[str]:
        """从模型输出中尽力解析出步骤列表，多重容错。"""
        # 1) 优先取 ```python 代码块；取不到就退回整段文本
        if "```python" in response:
            segment = response.split("```python", 1)[1].split("```", 1)[0]
        elif "```" in response:
            segment = response.split("```", 1)[1].split("```", 1)[0]
        else:
            segment = response

        # 2) 只截取第一个 [ ... ] 列表字面量，避免后续多余文本干扰
        l, r = segment.find("["), segment.rfind("]")
        if l != -1 and r != -1 and r > l:
            list_src = segment[l : r + 1]
            # 容错：中文逗号/引号归一化为英文
            normalized = (
                list_src.replace("，", ",").replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
            )
            try:
                plan = ast.literal_eval(normalized)
                if isinstance(plan, list) and plan:
                    return [str(x) for x in plan]
            except (ValueError, SyntaxError):
                # 3) 再退一步：用正则抽取引号内的字符串作为步骤
                items = re.findall(r'["\']([^"\']+)["\']', list_src)
                if items:
                    return items

        print("解析计划失败：模型未按要求输出 Python 列表。")
        return []

    def _execute(self, question: str, plan: List[str]) -> str:
        """逐步执行计划，返回最后一步的结果作为最终答案。"""
        history = ""
        final_answer = ""
        for i, step in enumerate(plan, 1):
            print(f"\n--- 执行步骤 {i}/{len(plan)}: {step} ---")
            prompt = EXECUTOR_PROMPT_TEMPLATE.format(
                question=question,
                plan=plan,
                history=history if history else "无",
                current_step=step,
            )
            try:
                result = self.llm.think([{"role": "user", "content": prompt}])
            except LLMError as e:
                print(f"\n执行阶段 LLM 调用失败: {e}")
                break
            history += f"步骤 {i}: {step}\n结果: {result}\n\n"
            final_answer = result
        return final_answer
