"""my_agents：一个分层、可扩展的轻量级 Agent 框架。

分层：
- core       ：基础设施（Agent 基类、LLM、Message、Config、异常、记忆、上下文）
- tools      ：工具系统（Tool 基类、注册表、内置工具：搜索/计算/记忆/RAG/笔记/终端/ANP）
- agents     ：范式实现（ReAct / Simple / PlanSolve / Reflection）
- protocols  ：通信协议（ANP 纯内存 / MCP 适配器骨架）
- evaluation ：性能评估（多种评估器 + AgentEvaluator）
- training   ：第11章轻量衔接（轨迹导出 + 奖励函数，无训练重依赖）
"""

from .core.agent import Agent
from .core.config import Config
from .core.context import ContextBuilder, ContextConfig, ContextPacket
from .core.llm_client import MyAgentLLM
from .core.memory import MemoryItem, WorkingMemory
from .core.message import Message

from .agents.react_agent import ReActAgent
from .agents.simple_agent import SimpleAgent
from .agents.plan_solve_agent import PlanAndSolveAgent
from .agents.reflection_agent import ReflectionAgent

from .tools.base import Tool, ToolParameter
from .tools.registry import ToolRegistry
from .tools.builtin import (
    ANPTool,
    CalculatorTool,
    MemoryTool,
    NoteTool,
    RAGTool,
    SearchTool,
    TerminalTool,
)

from .protocols.anp import ANPNetwork, ANPRegistry
from .evaluation.evaluator import (
    AgentEvaluator,
    ASTMatchEvaluator,
    EvalSample,
    ExactMatchEvaluator,
    LLMJudgeEvaluator,
)
from .training.trajectory_exporter import TrajectoryExporter

__all__ = [
    # core
    "Agent",
    "Config",
    "MyAgentLLM",
    "Message",
    "WorkingMemory",
    "MemoryItem",
    "ContextBuilder",
    "ContextConfig",
    "ContextPacket",
    # agents
    "ReActAgent",
    "SimpleAgent",
    "PlanAndSolveAgent",
    "ReflectionAgent",
    # tools
    "Tool",
    "ToolParameter",
    "ToolRegistry",
    "SearchTool",
    "CalculatorTool",
    "MemoryTool",
    "RAGTool",
    "NoteTool",
    "TerminalTool",
    "ANPTool",
    # protocols
    "ANPNetwork",
    "ANPRegistry",
    # evaluation
    "AgentEvaluator",
    "ASTMatchEvaluator",
    "ExactMatchEvaluator",
    "LLMJudgeEvaluator",
    "EvalSample",
    # training
    "TrajectoryExporter",
]
