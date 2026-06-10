"""奖励函数（第11章轻量衔接）：纯 Python 评分，无 torch/trl 依赖。

这些 reward 既可用于离线 RL 训练数据打分，也可在运行时做 self-check /
best-of-N 选择。剥离了所有训练框架依赖，只保留纯算法评分逻辑。
"""

import re
from typing import Optional


def extract_final_number(text: str) -> Optional[float]:
    """从文本中抽取最后一个数字（常用于数学题答案对比）。"""
    nums = re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if not nums:
        return None
    try:
        return float(nums[-1])
    except ValueError:
        return None


def math_reward(prediction: str, expected: str, tol: float = 1e-6) -> float:
    """数学答案奖励：抽取双方最后一个数字比较，命中得 1.0，否则 0.0。"""
    p = extract_final_number(prediction)
    e = extract_final_number(expected)
    if p is None or e is None:
        return 0.0
    return 1.0 if abs(p - e) <= tol else 0.0


def format_reward(text: str, required_markers: list[str]) -> float:
    """格式奖励：检查输出是否包含全部要求的标记（如 'Thought:'、'Action:'）。

    返回命中比例 0~1，可用于鼓励模型遵循结构化输出格式。
    """
    if not required_markers:
        return 1.0
    hit = sum(1 for m in required_markers if m in text)
    return hit / len(required_markers)


def length_penalty(text: str, max_len: int = 2000) -> float:
    """长度惩罚：超长时线性扣分，鼓励简洁。返回 0~1 的奖励系数。"""
    if len(text) <= max_len:
        return 1.0
    over = len(text) - max_len
    return max(0.0, 1.0 - over / max_len)


def combined_reward(prediction: str, expected: str, markers: Optional[list[str]] = None) -> float:
    """综合奖励：正确性为主，格式为辅。"""
    correctness = math_reward(prediction, expected)
    fmt = format_reward(prediction, markers or [])
    # 正确性权重 0.8，格式 0.2
    return 0.8 * correctness + 0.2 * fmt
