"""my_agents 全功能演示。

逐模块演示框架的所有能力：
  [核心] Message / Config / 异常
  [第4章] 四种范式 Agent：Simple / ReAct / PlanAndSolve / Reflection
  [工具]  Calculator / Search / Memory / RAG / Note / Terminal / ANP
  [第8章] WorkingMemory 记忆
  [第9章] ContextBuilder 上下文工程
  [第10章] ANP 协议 / MCP 适配器探测
  [第12章] 评估器
  [第11章] 轨迹导出 + 奖励函数

离线能力直接跑；需要 LLM 的部分会调用本地 Ollama（按 .env 配置）。
用法：
  .venv/bin/python demo_all.py            # 全部
  .venv/bin/python demo_all.py --no-llm   # 只跑离线部分（不调用大模型）
"""

import sys
import tempfile

SEP = "=" * 60


def title(t):
    print(f"\n{SEP}\n{t}\n{SEP}")


def run_offline():
    # ---------- 核心数据结构 ----------
    title("【核心】Message / Config")
    from my_agents import Message, Config

    msg = Message(role="user", content="你好")
    print("Message.to_dict():", msg.to_dict())
    print("Config 默认:", Config().to_dict())
    print("Config.from_env():", Config.from_env().to_dict())

    # ---------- 工具：计算器 ----------
    title("【工具·第4章】CalculatorTool（AST 安全求值）")
    from my_agents.tools.builtin.calculator import CalculatorTool

    calc = CalculatorTool()
    for expr in ["3*3", "sqrt(16)+1", "2**10", "1/0", '__import__("os")']:
        print(f"  {expr:18} = {calc.run({'expression': expr})}")

    # ---------- 工具：记忆（第8章）----------
    title("【第8章】WorkingMemory + MemoryTool（容量/TTL/混合检索）")
    from my_agents import WorkingMemory, MemoryTool

    wm = WorkingMemory(capacity=3, ttl_seconds=3600)
    wm.add("用户喜欢吃辣", importance=0.9)
    wm.add("用户住在北京", importance=0.5)
    wm.add("今天天气晴朗", importance=0.2)
    print("  检索 '用户 喜欢':", [it.content for it in wm.retrieve("用户喜欢什么", limit=2)])
    wm.add("第四条触发淘汰", importance=0.1)
    print(f"  容量上限生效，当前条数: {len(wm)}（上限3）")

    mt = MemoryTool()
    print(" ", mt.run({"action": "add", "content": "项目周五截止", "importance": 0.8}))
    print("  检索结果:", mt.run({"action": "search", "query": "项目 截止"}))
    print("  统计:", mt.run({"action": "stats"}))

    # ---------- 工具：RAG（第8章）----------
    title("【第8章】RAGTool（纯 Python TF-IDF 检索）")
    from my_agents import RAGTool

    rag = RAGTool()
    n = rag.add_text(
        "Python 是一门解释型编程语言。它支持面向对象与函数式。"
        "Agent 是能自主调用工具完成多步任务的 LLM 系统。"
        "RAG 指检索增强生成，先检索再回答。"
    )
    print(f"  入库 {n} 块；检索 '什么是 Agent':")
    print("  →", rag.run({"action": "search", "query": "什么是 Agent", "limit": 1}))

    # ---------- 上下文工程（第9章）----------
    title("【第9章】ContextBuilder（GSSC 上下文组织）")
    from my_agents import ContextBuilder, ContextConfig

    cb = ContextBuilder(memory_tool=mt, rag_tool=rag, config=ContextConfig(max_tokens=600))
    ctx = cb.build(
        user_query="项目 Agent 什么时候截止",
        conversation_history=["用户: 你好", "助手: 在讨论项目"],
        system_instructions="你是项目助手。",
    )
    print(ctx)

    # ---------- 笔记工具（第9章）----------
    title("【第9章】NoteTool（文件+索引）")
    with tempfile.TemporaryDirectory() as tmp:
        from my_agents import NoteTool

        nt = NoteTool(workspace=tmp)
        print(" ", nt.run({"action": "create", "title": "会议纪要", "content": "讨论了 A 方案"}))
        print(" ", nt.run({"action": "update", "title": "会议纪要", "content": "补充 B 方案"}))
        print("  读取:\n", nt.run({"action": "read", "title": "会议纪要"}))
        print("  搜索 'B 方案':", nt.run({"action": "search", "query": "B 方案"}))

    # ---------- 终端工具（第9章）----------
    title("【第9章】TerminalTool（白名单+沙箱+超时）")
    from my_agents import TerminalTool

    tt = TerminalTool(workspace=".")
    print("  echo hello   →", tt.run({"command": "echo hello"}).strip())
    print("  rm -rf /     →", tt.run({"command": "rm -rf /"}))
    print("  cat ../x     →", tt.run({"command": "cat ../secret"}))

    # ---------- 通信协议（第10章）----------
    title("【第10章】ANP 协议（纯内存服务发现+轮询）")
    from my_agents import ANPNetwork, ANPTool

    net = ANPNetwork()
    net.register_service("greet", lambda s: f"你好，{s}！", meta={"lang": "zh"})
    net.register_service("greet", lambda s: f"Hi, {s}!", meta={"lang": "en"})
    anp = ANPTool(network=net)
    print("  可用服务:", anp.run({"action": "list"}))
    print("  调用1:", anp.run({"action": "invoke", "service": "greet", "payload": "张三"}))
    print("  调用2(轮询到另一提供者):", anp.run({"action": "invoke", "service": "greet", "payload": "张三"}))

    title("【第10章】MCP 适配器（可选依赖探测）")
    from my_agents.protocols import mcp_available, MCPToolAdapter

    print("  MCP SDK 是否安装:", mcp_available())
    adapter = MCPToolAdapter(server_command=["python", "server.py"])
    print("  connect() 结果:", adapter.connect())
    print("  未连接时调用:", adapter.call_tool("add", {"a": 1}))

    # ---------- 评估（第12章）----------
    title("【第12章】评估器（ExactMatch / ASTMatch / AgentEvaluator）")
    from my_agents import ASTMatchEvaluator, ExactMatchEvaluator, EvalSample, AgentEvaluator

    ast_eval = ASTMatchEvaluator()
    print("  AST: add(a=1,b=2) vs add(b=2,a=1) →", ast_eval.score_one("add(a=1, b=2)", "add(b=2, a=1)"))
    print("  AST: add(a=1,b=3) vs add(a=1,b=2) →", ast_eval.score_one("add(a=1, b=3)", "add(a=1, b=2)"))

    samples = [EvalSample(input="1+1", expected="2"), EvalSample(input="首都", expected="北京")]
    fake_agent = lambda q: "答案是2" if q == "1+1" else "上海"
    result = AgentEvaluator(ExactMatchEvaluator(contains=True)).run(fake_agent, samples)
    print(" ", result.summary())

    # ---------- 训练衔接（第11章）----------
    title("【第11章】奖励函数 + 轨迹导出（训练数据生产）")
    from my_agents.training.reward import math_reward, format_reward, combined_reward
    from my_agents import TrajectoryExporter

    print("  math_reward('答案42','42'):", math_reward("最终答案是 42", "42"))
    print("  format_reward(含Thought/Action):", format_reward("Thought:..\nAction:..", ["Thought:", "Action:"]))
    print("  combined_reward:", combined_reward("最终答案 42", "42", ["Thought:"]))

    exp = TrajectoryExporter()
    exp.add_step("user", "1+1=?")
    exp.add_step("assistant", "2", reward=1.0)
    print("  SFT 格式:", exp.to_sft_messages(system_prompt="你是助手"))
    print("  RL 样本:", exp.to_rl_samples())


def run_llm():
    title("【第4章】四种范式 Agent（调用本地 Ollama）")
    from my_agents import (
        MyAgentLLM,
        SimpleAgent,
        ReActAgent,
        PlanAndSolveAgent,
        ReflectionAgent,
        ToolRegistry,
    )
    from my_agents.tools.builtin.calculator import CalculatorTool

    try:
        llm = MyAgentLLM()
    except Exception as e:
        print(f"无法初始化 LLM（跳过 LLM 演示）：{e}")
        return

    print("\n>>> 1) SimpleAgent 单轮对话")
    print("最终:", SimpleAgent(llm).run("用一句话说明什么是质数"))

    print("\n>>> 2) ReActAgent + 计算器工具（推理-行动循环）")
    reg = ToolRegistry()
    reg.register_tool(CalculatorTool())
    print("最终:", ReActAgent(llm, reg, max_steps=5).run("请计算 25 * 4 等于多少"))

    print("\n>>> 3) PlanAndSolveAgent 先规划后执行")
    print("最终:", PlanAndSolveAgent(llm).run("小明有3个苹果，又买了2袋，每袋4个，一共多少个苹果？"))

    print("\n>>> 4) ReflectionAgent 反思优化（写代码）")
    code = ReflectionAgent(llm, max_iterations=1).run("写一个判断一个数是否为质数的 Python 函数")
    print("最终代码（前 200 字）:\n", (code or "")[:200])


if __name__ == "__main__":
    no_llm = "--no-llm" in sys.argv
    run_offline()
    if not no_llm:
        run_llm()
    title("演示结束 ✅")
