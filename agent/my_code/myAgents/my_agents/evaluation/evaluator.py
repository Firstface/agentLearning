"""评估框架：统一的数据集 / 评估器抽象与若干离线评估器。

- EvalSample / EvalResult ：数据结构
- Evaluator(ABC)          ：评估器基类
- ExactMatchEvaluator     ：精确/准精确匹配（纯算法，离线）
- ASTMatchEvaluator       ：函数调用匹配（BFCL 风格，纯算法，离线）
- LLMJudgeEvaluator       ：用 LLM 当裁判打分（复用 MyAgentLLM，需联网）
- AgentEvaluator          ：在数据集上批量跑 Agent 并汇总指标
"""

import ast
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class EvalSample:
    """单条评估样本。"""

    input: str
    expected: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    """评估汇总结果。"""

    total: int
    correct: int
    details: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    def summary(self) -> str:
        return f"准确率: {self.accuracy:.2%} ({self.correct}/{self.total})"


class Evaluator(ABC):
    """评估器基类：给定预测与期望，判断是否正确。"""

    @abstractmethod
    def score_one(self, prediction: Any, expected: Any) -> bool:
        raise NotImplementedError

    def evaluate(self, predictions: List[Any], samples: List[EvalSample]) -> EvalResult:
        correct = 0
        details = []
        for pred, sample in zip(predictions, samples):
            ok = self.score_one(pred, sample.expected)
            correct += int(ok)
            details.append({"input": sample.input, "expected": sample.expected, "prediction": pred, "correct": ok})
        return EvalResult(total=len(samples), correct=correct, details=details)


class ExactMatchEvaluator(Evaluator):
    """准精确匹配：忽略大小写与首尾空白；可选子串包含。"""

    def __init__(self, contains: bool = False):
        self.contains = contains

    def score_one(self, prediction: Any, expected: Any) -> bool:
        p = str(prediction).strip().lower()
        e = str(expected).strip().lower()
        return (e in p) if self.contains else (p == e)


class ASTMatchEvaluator(Evaluator):
    """函数调用匹配（BFCL 风格）。

    期望与预测都形如 'func(a=1, b="x")'，解析成 (函数名, 参数字典) 后比较。
    纯算法，无外部依赖。
    """

    @staticmethod
    def _parse_call(text: str) -> Optional[tuple]:
        text = text.strip()
        # 容错：去掉可能的反引号/代码块包裹
        text = text.strip("`").strip()
        m = re.search(r"(\w+)\s*\((.*)\)\s*$", text, re.DOTALL)
        if not m:
            return None
        name = m.group(1)
        args_src = m.group(2).strip()
        kwargs: Dict[str, Any] = {}
        if args_src:
            try:
                # 用 ast 安全解析关键字参数
                call = ast.parse(f"_f({args_src})", mode="eval").body
                for kw in call.keywords:
                    kwargs[kw.arg] = ast.literal_eval(kw.value)
            except Exception:
                return None
        return name, kwargs

    def score_one(self, prediction: Any, expected: Any) -> bool:
        p = self._parse_call(str(prediction))
        e = self._parse_call(str(expected))
        if p is None or e is None:
            return False
        return p[0] == e[0] and p[1] == e[1]


class LLMJudgeEvaluator(Evaluator):
    """用 LLM 作为裁判判断预测是否满足期望（需要可用的 LLM 客户端）。"""

    def __init__(self, llm, criteria: str = "预测是否正确回答了问题且与参考答案一致"):
        self.llm = llm
        self.criteria = criteria

    def score_one(self, prediction: Any, expected: Any) -> bool:
        prompt = (
            f"你是严格的评审。判断标准：{self.criteria}。\n"
            f"参考答案：{expected}\n预测答案：{prediction}\n"
            f"只回答 '正确' 或 '错误'。"
        )
        try:
            verdict = self.llm.invoke([{"role": "user", "content": prompt}])
        except Exception as e:
            print(f"LLM 裁判调用失败: {e}")
            return False
        return "正确" in verdict and "错误" not in verdict


class AgentEvaluator:
    """在数据集上批量运行一个 Agent 并用指定评估器汇总指标。"""

    def __init__(self, evaluator: Evaluator):
        self.evaluator = evaluator

    def run(self, agent_run: Callable[[str], Any], samples: List[EvalSample]) -> EvalResult:
        """agent_run: 接收 input 字符串、返回预测的可调用（如 agent.run）。"""
        predictions = []
        for s in samples:
            try:
                predictions.append(agent_run(s.input))
            except Exception as e:
                predictions.append(f"ERROR: {e}")
        return self.evaluator.evaluate(predictions, samples)
