"""轨迹导出（第11章轻量衔接）。

把运行时产生的交互轨迹（user/assistant/tool 消息）导出为训练管线常用的数据格式：
- SFT 格式：{"messages": [...]} 的 JSONL
- 偏好/RL 样本：{"prompt", "response", "reward"}

零重型依赖（不引入 torch/trl/transformers）。运行时与训练管线在此解耦衔接：
运行时只负责"生产"训练数据，真正的训练在框架外的离线管线完成。
"""

import json
from typing import Any, Dict, List, Optional


class TrajectoryExporter:
    """收集交互步骤并导出为训练数据。"""

    def __init__(self):
        self._steps: List[Dict[str, Any]] = []

    def add_step(self, role: str, content: str, reward: Optional[float] = None) -> None:
        step = {"role": role, "content": content}
        if reward is not None:
            step["reward"] = reward
        self._steps.append(step)

    def clear(self) -> None:
        self._steps = []

    def to_sft_messages(self, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """导出为 SFT 训练用的 messages 结构。"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        for s in self._steps:
            # 训练数据只保留 role/content
            messages.append({"role": s["role"], "content": s["content"]})
        return {"messages": messages}

    def to_rl_samples(self) -> List[Dict[str, Any]]:
        """导出为 RL/偏好样本：以 user 为 prompt，紧随的 assistant 为 response。"""
        samples = []
        for i in range(len(self._steps) - 1):
            cur, nxt = self._steps[i], self._steps[i + 1]
            if cur["role"] == "user" and nxt["role"] == "assistant":
                samples.append(
                    {
                        "prompt": cur["content"],
                        "response": nxt["content"],
                        "reward": nxt.get("reward", 0.0),
                    }
                )
        return samples

    def export_jsonl(self, path: str, fmt: str = "sft", system_prompt: Optional[str] = None) -> int:
        """写出 JSONL 文件，返回写出的行数。fmt: 'sft' | 'rl'。"""
        with open(path, "w", encoding="utf-8") as f:
            if fmt == "sft":
                f.write(json.dumps(self.to_sft_messages(system_prompt), ensure_ascii=False) + "\n")
                return 1
            if fmt == "rl":
                rows = self.to_rl_samples()
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                return len(rows)
        raise ValueError(f"未知格式: {fmt}")
