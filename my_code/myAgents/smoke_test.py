"""离线冒烟测试：不依赖网络/LLM，验证框架结构、工具与解析逻辑。"""

import sys

# 1. 包导入
from my_agents import (
    Agent,
    Config,
    MyAgentLLM,
    Message,
    ReActAgent,
    SimpleAgent,
    PlanAndSolveAgent,
    ReflectionAgent,
    ToolRegistry,
    Tool,
    ToolParameter,
)
from my_agents.tools.builtin.calculator import calculate, CalculatorTool
from my_agents.tools.builtin.search import SearchTool
from my_agents.core.tool import ToolExecutor  # 兼容层

failures = []


def check(name, cond):
    print(f"{'✅' if cond else '❌'} {name}")
    if not cond:
        failures.append(name)


# 2. 计算器（AST 安全求值）
check("calculate('3*3') == '9'", calculate("3*3") == "9")
check("calculate('sqrt(16)+1') == '5.0'", calculate("sqrt(16)+1") == "5.0")
check("calculate('1/0') 含除数为零", "除数为零" in calculate("1/0"))
check("calculate('__import__(\"os\")') 被拦截", "失败" in calculate('__import__("os")'))

# 3. ToolRegistry：对象工具 + 函数工具统一执行
reg = ToolRegistry()
reg.register_tool(CalculatorTool())
reg.register_function("echo", "回显输入", lambda s: f"echo:{s}")
check("registry 执行对象工具", reg.execute_tool("Calculator", "2+2") == "4")
check("registry 执行函数工具", reg.execute_tool("echo", "hi") == "echo:hi")
check("registry 工具清单含两者", "Calculator" in reg.get_available_tools() and "echo" in reg.get_available_tools())

# 4. 兼容层 ToolExecutor：旧接口
te = ToolExecutor()
te.register_tool("echo", "回显", lambda s: f"E:{s}")
runner = te.getTool("echo")
check("ToolExecutor.getTool 返回可调用", callable(runner) and runner("x") == "E:x")
check("ToolExecutor.getTool 未知工具返回 None", te.getTool("nope") is None)
check("ToolExecutor.getAvailableTools", "echo" in te.getAvailableTools())

# 5. ReAct 解析逻辑（不调用 LLM，直接测私有方法）
#    用一个假的 llm 占位，绕过构造里的网络
class _FakeLLM:
    pass

ra = ReActAgent.__new__(ReActAgent)  # 不走 __init__，仅测解析方法
t, a = ra._parse_output("Thought: 我要搜索\nAction: Search[\"NUS\"]")
check("_parse_output 提取 Thought", t == "我要搜索")
check("_parse_output 提取 Action", a == 'Search["NUS"]')
name, arg = ra._parse_action('Search["NUS大学"]')
check("_parse_action 工具名", name == "Search")
check("_parse_action 去引号", arg == "NUS大学")
check("_parse_action_input(Finish[...])", ra._parse_action_input("Finish[答案是42]") == "答案是42")
nm, ag = ra._parse_action("乱写的内容")
check("_parse_action 非法格式返回 None", nm is None)

# 6. Message / Config
m = Message(role="user", content="hi")
check("Message.to_dict", m.to_dict() == {"role": "user", "content": "hi"})
check("Config 默认 timeout=60", Config().timeout == 60)

# 7. 抽象基类不可实例化
try:
    Agent(name="x", llm=None)
    check("Agent 抽象类应不可实例化", False)
except TypeError:
    check("Agent 抽象类不可实例化", True)

print("\n==== 冒烟测试结果 ====")
if failures:
    print(f"失败 {len(failures)} 项: {failures}")
    sys.exit(1)
print("全部通过 ✅")
