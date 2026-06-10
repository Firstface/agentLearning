"""离线冒烟测试（第8-12章整合）：不依赖网络/LLM，验证新增模块。"""

import os
import sys
import tempfile

from my_agents import (
    WorkingMemory,
    ContextBuilder,
    ContextConfig,
    MemoryTool,
    RAGTool,
    NoteTool,
    TerminalTool,
    ANPTool,
    ANPNetwork,
    ASTMatchEvaluator,
    ExactMatchEvaluator,
    EvalSample,
    AgentEvaluator,
    TrajectoryExporter,
)
from my_agents.training.reward import math_reward, format_reward, combined_reward

failures = []


def check(name, cond):
    print(f"{'✅' if cond else '❌'} {name}")
    if not cond:
        failures.append(name)


# ===== 第8章：记忆 =====
print("\n--- 第8章 记忆 ---")
wm = WorkingMemory(capacity=3, ttl_seconds=3600)
wm.add("用户喜欢吃辣", importance=0.9)
wm.add("用户住在北京", importance=0.5)
wm.add("今天天气晴", importance=0.2)
hits = wm.retrieve("用户 喜欢 什么", limit=2)
check("WorkingMemory 检索命中", any("辣" in h.content for h in hits))
wm.add("第四条", importance=0.1)  # 触发容量淘汰
check("WorkingMemory 容量上限=3", len(wm) == 3)

mt = MemoryTool()
mt.run({"action": "add", "content": "项目截止日是周五", "importance": 0.8})
res = mt.run({"action": "search", "query": "项目 截止"})
check("MemoryTool add+search", "周五" in res)

rag = RAGTool()
rag.add_text("Python 是一门解释型语言。它支持面向对象。Agent 是能自主调用工具的系统。")
r = rag.run({"action": "search", "query": "什么是 Agent", "limit": 1})
check("RAGTool TF-IDF 检索", "Agent" in r)

# ===== 第9章：上下文工程 =====
print("\n--- 第9章 上下文工程 ---")
cb = ContextBuilder(memory_tool=mt, rag_tool=rag, config=ContextConfig(max_tokens=500))
ctx = cb.build(
    user_query="Agent 项目什么时候截止",
    conversation_history=["上一轮：你好", "上一轮：在讨论项目"],
    system_instructions="你是项目助手。",
)
check("ContextBuilder 含系统指令", "系统指令" in ctx)
check("ContextBuilder 注入记忆", "周五" in ctx)

with tempfile.TemporaryDirectory() as tmp:
    nt = NoteTool(workspace=tmp)
    nt.run({"action": "create", "title": "会议", "content": "讨论了 A 方案"})
    nt.run({"action": "update", "title": "会议", "content": "补充 B 方案"})
    body = nt.run({"action": "read", "title": "会议"})
    check("NoteTool create+update+read", "A 方案" in body and "B 方案" in body)
    found = nt.run({"action": "search", "query": "B 方案"})
    check("NoteTool search", "会议" in found)

tt = TerminalTool(workspace=".")
out = tt.run({"command": "echo hello"})
check("TerminalTool 白名单命令执行", "hello" in out)
denied = tt.run({"command": "rm -rf /"})
check("TerminalTool 拒绝危险命令", "拒绝" in denied)
denied2 = tt.run({"command": "cat ../secret"})
check("TerminalTool 拒绝路径穿越", "拒绝" in denied2)

# ===== 第10章：通信协议 =====
print("\n--- 第10章 通信协议 ---")
net = ANPNetwork()
net.register_service("greet", lambda s: f"你好，{s}", meta={"lang": "zh"})
anp = ANPTool(network=net)
check("ANPTool 列出服务", "greet" in anp.run({"action": "list"}))
check("ANPTool 调用服务", "你好，张三" == anp.run({"action": "invoke", "service": "greet", "payload": "张三"}))

# ===== 第12章：评估 =====
print("\n--- 第12章 评估 ---")
ast_eval = ASTMatchEvaluator()
check("ASTMatch 相同调用判正确", ast_eval.score_one('add(a=1, b=2)', 'add(b=2, a=1)'))
check("ASTMatch 不同参数判错误", not ast_eval.score_one('add(a=1, b=3)', 'add(a=1, b=2)'))

em = ExactMatchEvaluator(contains=True)
samples = [EvalSample(input="1+1", expected="2"), EvalSample(input="首都", expected="北京")]
result = AgentEvaluator(em).run(lambda q: "答案是2" if q == "1+1" else "上海", samples)
check("AgentEvaluator 准确率计算", abs(result.accuracy - 0.5) < 1e-9)

# ===== 第11章：轻量衔接 =====
print("\n--- 第11章 轻量衔接 ---")
check("math_reward 命中", math_reward("最终答案是 42", "42") == 1.0)
check("math_reward 未命中", math_reward("答案是 41", "42") == 0.0)
check("format_reward 比例", abs(format_reward("Thought: x\nAction: y", ["Thought:", "Action:"]) - 1.0) < 1e-9)

exporter = TrajectoryExporter()
exporter.add_step("user", "1+1=?")
exporter.add_step("assistant", "2", reward=1.0)
sft = exporter.to_sft_messages(system_prompt="你是助手")
check("TrajectoryExporter SFT 格式", sft["messages"][0]["role"] == "system" and len(sft["messages"]) == 3)
rl = exporter.to_rl_samples()
check("TrajectoryExporter RL 样本", rl and rl[0]["prompt"] == "1+1=?" and rl[0]["reward"] == 1.0)

print("\n==== 第8-12章整合冒烟测试 ====")
if failures:
    print(f"失败 {len(failures)} 项: {failures}")
    sys.exit(1)
print("全部通过 ✅")
