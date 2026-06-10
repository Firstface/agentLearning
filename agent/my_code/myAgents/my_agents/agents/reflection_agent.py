"""Reflection 范式 Agent：执行 -> 反思 -> 优化 的自我修正循环。

适合对输出质量要求高、可迭代打磨的任务（如写代码、写文案）。
内部用 Memory 记录每轮的产出（execution）和评审反馈（reflection）。
"""

from typing import Any, Dict, List, Optional

from ..core.agent import Agent
from ..core.config import Config
from ..core.exceptions import LLMError
from ..core.llm_client import MyAgentLLM

INITIAL_PROMPT_TEMPLATE = """你是一位资深的 Python 程序员。请根据以下要求编写一个 Python 函数。
代码必须包含完整的函数签名、文档字符串，并遵循 PEP 8 规范。

要求: {task}

请直接输出代码，不要包含任何额外解释。
"""

REFLECT_PROMPT_TEMPLATE = """你是一位极其严格的代码评审专家和资深算法工程师，对性能有极致要求。
请审查以下代码，专注找出它在**算法效率**上的主要瓶颈。

# 原始任务:
{task}

# 待审查的代码:
```python
{code}
```

请分析其时间复杂度，并思考是否存在算法上更优的方案。
如果存在，请明确指出不足并给出具体改进建议；如果已是最优，请只回答"无需改进"。
请直接输出反馈，不要包含额外解释。
"""

REFINE_PROMPT_TEMPLATE = """你是一位资深的 Python 程序员，正在根据评审反馈优化代码。

# 原始任务:
{task}

# 上一轮代码:
{last_code}

# 评审反馈:
{feedback}

请根据反馈生成优化后的新版本代码，包含完整签名、文档字符串并遵循 PEP 8。
请直接输出优化后的代码，不要包含额外解释。
"""


class Memory:
    """反思过程的短期记忆：记录每轮产出与反馈。"""

    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def add_record(self, record_type: str, content: str) -> None:
        # record_type: 'execution'（代码） 或 'reflection'（反馈）
        self.records.append({"type": record_type, "content": content})

    def get_last_execution(self) -> Optional[str]:
        for record in reversed(self.records):
            if record["type"] == "execution":
                return record["content"]
        return None


class ReflectionAgent(Agent):
    """带自我反思与修正的智能体。"""

    def __init__(
        self,
        llm: MyAgentLLM,
        max_iterations: int = 3,
        name: str = "ReflectionAgent",
        config: Optional[Config] = None,
    ):
        super().__init__(name=name, llm=llm, config=config)
        self.max_iterations = max_iterations
        self.memory = Memory()

    def run(self, input_text: str, **kwargs) -> Optional[str]:
        self.memory = Memory()  # 每次运行重置记忆

        # 1. 初始执行
        print("--- 初始执行 ---")
        initial = self._call(INITIAL_PROMPT_TEMPLATE.format(task=input_text))
        if not initial:
            return None
        self.memory.add_record("execution", initial)

        # 2. 反思 -> 优化 循环
        for i in range(1, self.max_iterations + 1):
            print(f"\n--- 第 {i} 轮反思 ---")
            last_code = self.memory.get_last_execution()
            feedback = self._call(
                REFLECT_PROMPT_TEMPLATE.format(task=input_text, code=last_code)
            )
            if not feedback:
                break
            self.memory.add_record("reflection", feedback)

            # 终止条件：评审认为无需改进
            if "无需改进" in feedback or "no need for improvement" in feedback.lower():
                print("评审认为无需改进，提前结束。")
                break

            print(f"\n--- 第 {i} 轮优化 ---")
            refined = self._call(
                REFINE_PROMPT_TEMPLATE.format(
                    task=input_text, last_code=last_code, feedback=feedback
                )
            )
            if not refined:
                break
            self.memory.add_record("execution", refined)

        return self.memory.get_last_execution()

    def _call(self, prompt: str) -> str:
        """统一的 LLM 调用，失败返回空串。"""
        try:
            return self.llm.think([{"role": "user", "content": prompt}])
        except LLMError as e:
            print(f"\nLLM 调用失败: {e}")
            return ""
