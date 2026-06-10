"""端到端测试：连接本地 Ollama，验证 SimpleAgent 与 ReActAgent（用计算器工具）。"""

from my_agents import MyAgentLLM, SimpleAgent, ReActAgent, ToolRegistry
from my_agents.tools.builtin.calculator import CalculatorTool

print("===== 1. SimpleAgent 单轮对话 =====")
llm = MyAgentLLM()
simple = SimpleAgent(llm)
ans = simple.run("用一句话介绍什么是质数")
print("\n[SimpleAgent 返回]", (ans or "")[:80])

print("\n===== 2. ReActAgent + 计算器工具 =====")
reg = ToolRegistry()
reg.register_tool(CalculatorTool())
react = ReActAgent(llm, reg, max_steps=5)
result = react.run("请计算 12 * 8 等于多少")
print("\n[ReActAgent 返回]", result)
