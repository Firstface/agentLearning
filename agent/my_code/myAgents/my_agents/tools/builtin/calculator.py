"""内置计算器工具：基于 AST 的安全表达式求值。

不使用 eval，避免任意代码执行；仅允许四则运算、幂、取负与少量数学函数。
"""

import ast
import math
import operator
from typing import Any, Dict, List

from ..base import Tool, ToolParameter

# 允许的二元运算符
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
# 允许的一元运算符
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
# 允许的函数与常量
_FUNCS = {"sqrt": math.sqrt, "abs": abs, "round": round, "pow": pow}
_CONSTS = {"pi": math.pi, "e": math.e}


def _eval_node(node: ast.AST) -> float:
    """递归求值 AST 节点，仅允许白名单内的运算。"""
    if isinstance(node, ast.Constant):  # 数字字面量
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"不支持的常量: {node.value!r}")
    if isinstance(node, ast.Name):  # pi / e
        if node.id in _CONSTS:
            return _CONSTS[node.id]
        raise ValueError(f"未知标识符: {node.id}")
    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise ValueError("不支持的二元运算符")
        return op(_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise ValueError("不支持的一元运算符")
        return op(_eval_node(node.operand))
    if isinstance(node, ast.Call):  # sqrt(...) 等
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            raise ValueError("不支持的函数调用")
        args = [_eval_node(a) for a in node.args]
        return _FUNCS[node.func.id](*args)
    raise ValueError(f"不支持的表达式节点: {type(node).__name__}")


def calculate(expression: str) -> str:
    """计算算术表达式并返回字符串结果。"""
    if not expression or not expression.strip():
        return "错误：表达式为空。"
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_node(tree.body)
        return str(result)
    except ZeroDivisionError:
        return "计算错误：除数为零。"
    except Exception as e:
        return f"计算失败: {e}"


class CalculatorTool(Tool):
    """计算器工具的 Tool 封装。"""

    def __init__(self):
        super().__init__(
            name="Calculator",
            description="一个计算器，支持四则运算、幂、sqrt 等。例如 '3*3' 或 'sqrt(16)+1'。",
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        return calculate(parameters.get("expression", ""))

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="expression", type="string", description="要计算的算术表达式"
            )
        ]
