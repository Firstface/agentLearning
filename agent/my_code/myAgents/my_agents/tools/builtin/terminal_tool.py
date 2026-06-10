"""终端工具（TerminalTool）：受限的本地命令执行。

四层安全防护：
1. 命令白名单：只允许只读类命令（ls/cat/grep/find/wc/head/tail/echo/pwd…），禁止 rm/mv/sudo 等。
2. workspace 沙箱：禁止 `..` 路径穿越，限制在工作目录内。
3. 超时：防止命令挂死。
4. 输出截断：防止超大输出撑爆上下文。
"""

import os
import subprocess
from typing import Any, Dict, List

from ..base import Tool, ToolParameter

# 只读命令白名单（取每条命令的第一个 token 校验）
ALLOWED_COMMANDS = {
    "ls", "cat", "grep", "find", "wc", "head", "tail",
    "echo", "pwd", "tree", "awk", "sed", "sort", "uniq", "diff", "stat",
}
# 明确禁止的危险关键字（即便混在管道里也拦）
FORBIDDEN = {"rm", "mv", "cp", "sudo", "chmod", "chown", "dd", "mkfs", "kill", ">", ">>", "curl", "wget"}


class TerminalTool(Tool):
    """受限终端工具：仅允许在 workspace 内执行只读命令。"""

    def __init__(self, workspace: str = ".", timeout: int = 30, max_output: int = 10000):
        super().__init__(
            name="Terminal",
            description=(
                "在受限沙箱内执行只读 shell 命令（仅 ls/cat/grep/find 等）。"
                "参数 command。禁止 rm/mv/sudo 等危险命令与路径穿越。"
            ),
        )
        self.workspace = os.path.abspath(workspace)
        self.timeout = timeout
        self.max_output = max_output

    def _is_safe(self, command: str) -> tuple[bool, str]:
        if not command.strip():
            return False, "空命令"
        # 路径穿越
        if ".." in command:
            return False, "禁止使用 '..' 进行路径穿越"
        tokens = command.split()
        # 危险关键字
        for tok in tokens:
            if tok in FORBIDDEN:
                return False, f"禁止的命令/操作符: {tok}"
        # 第一个命令必须在白名单
        first = tokens[0]
        if first not in ALLOWED_COMMANDS:
            return False, f"命令 '{first}' 不在白名单内"
        # 管道里的每段命令也校验首词
        if "|" in command:
            for seg in command.split("|"):
                seg = seg.strip()
                if seg and seg.split()[0] not in ALLOWED_COMMANDS:
                    return False, f"管道中命令 '{seg.split()[0]}' 不在白名单内"
        return True, ""

    def run(self, parameters: Dict[str, Any]) -> str:
        command = parameters.get("command", "")
        ok, reason = self._is_safe(command)
        if not ok:
            return f"已拒绝执行：{reason}"
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            output = result.stdout or result.stderr or "(无输出)"
            if len(output) > self.max_output:
                output = output[: self.max_output] + "\n...(输出已截断)"
            return output
        except subprocess.TimeoutExpired:
            return f"命令执行超时（>{self.timeout}s）。"
        except Exception as e:
            return f"命令执行失败: {e}"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="command", type="string", description="要执行的只读 shell 命令"),
        ]
