"""training：第11章 Agentic RL 的轻量衔接层。

重要：本层不引入 torch/trl/transformers/deepspeed 等训练重型依赖，也不在框架内训练模型。
它只负责「运行时」与「离线训练管线」之间的衔接：
- TrajectoryExporter：把运行时交互轨迹导出为 SFT / RL 训练数据格式
- reward：纯 Python 奖励函数，既可给训练数据打分，也可在运行时做 self-check

真正的 SFT/GRPO/LoRA 训练属于框架外的离线管线（见 code/chapter11），
与运行时是「生产者-消费者」关系。
"""

from .reward import (
    combined_reward,
    extract_final_number,
    format_reward,
    length_penalty,
    math_reward,
)
from .trajectory_exporter import TrajectoryExporter

__all__ = [
    "TrajectoryExporter",
    "math_reward",
    "format_reward",
    "length_penalty",
    "combined_reward",
    "extract_final_number",
]
