"""综合示例：串起第8-12章能力的「带记忆/上下文/笔记/检索」智能体。

演示一个 ContextAwareAgent：
- 用 RAGTool 检索知识（第8章）
- 用 MemoryTool 记住对话要点（第8章）
- 用 ContextBuilder 把记忆+检索+历史组织成上下文（第9章）
- 用 NoteTool 把结论写进笔记（第9章）
- 用 ReActAgent + 计算器/ANP 工具完成行动（第4/10章）
- 用 AgentEvaluator 评估输出（第12章）
- 用 TrajectoryExporter 导出训练数据（第11章衔接）

需要本地 Ollama（或任何 .env 配置的 OpenAI 兼容服务）。
"""

import tempfile

from my_agents import (
    MyAgentLLM,
    ContextBuilder,
    ContextConfig,
    MemoryTool,
    RAGTool,
    NoteTool,
    TrajectoryExporter,
    EvalSample,
    ExactMatchEvaluator,
    AgentEvaluator,
)


class ContextAwareAgent:
    """整合记忆、检索、上下文工程、笔记的对话智能体。"""

    def __init__(self, llm: MyAgentLLM, workspace: str):
        self.llm = llm
        self.memory = MemoryTool()
        self.rag = RAGTool()
        self.note = NoteTool(workspace=workspace)
        self.context_builder = ContextBuilder(
            memory_tool=self.memory,
            rag_tool=self.rag,
            config=ContextConfig(max_tokens=800),
        )
        self.history = []
        self.exporter = TrajectoryExporter()

    def learn(self, knowledge: str):
        """把知识灌入 RAG 知识库。"""
        self.rag.add_text(knowledge)

    def chat(self, user_input: str) -> str:
        # 1. 用上下文工程组织上下文（自动注入记忆+检索+历史）
        context = self.context_builder.build(
            user_query=user_input,
            conversation_history=self.history[-4:],
            system_instructions="你是一个简洁的中文助手，基于提供的上下文回答。",
        )
        messages = [
            {"role": "system", "content": context},
            {"role": "user", "content": user_input},
        ]
        # 2. 调用 LLM
        answer = self.llm.invoke(messages)

        # 3. 记录记忆、历史、轨迹
        self.memory.run({"action": "add", "content": f"问:{user_input} 答:{answer}", "importance": 0.6})
        self.history.append(f"用户: {user_input}")
        self.history.append(f"助手: {answer}")
        self.exporter.add_step("user", user_input)
        self.exporter.add_step("assistant", answer, reward=1.0)
        return answer


def main():
    llm = MyAgentLLM()
    with tempfile.TemporaryDirectory() as tmp:
        agent = ContextAwareAgent(llm, workspace=tmp)

        # 灌入知识（第8章 RAG）
        agent.learn(
            "新加坡国立大学（NUS）成立于1905年，是新加坡顶尖的综合研究型大学。"
            "它在 QS 世界大学排名中常年位居亚洲前列。"
        )

        print("===== 第一轮对话 =====")
        a1 = agent.chat("NUS 是什么时候成立的？")
        print("\n[回答]", a1)

        print("\n===== 第二轮对话（依赖记忆+上下文）=====")
        a2 = agent.chat("它在亚洲排名怎么样？")
        print("\n[回答]", a2)

        # 把结论写进笔记（第9章）
        agent.note.run({"action": "create", "title": "NUS调研", "content": f"{a1}\n{a2}"})
        print("\n===== 笔记内容 =====")
        print(agent.note.run({"action": "read", "title": "NUS调研"}))

        # 评估（第12章）
        print("\n===== 评估 =====")
        samples = [EvalSample(input="NUS 哪年成立", expected="1905")]
        result = AgentEvaluator(ExactMatchEvaluator(contains=True)).run(agent.chat, samples)
        print(result.summary())

        # 导出训练数据（第11章衔接）
        print("\n===== 训练数据导出 =====")
        rl = agent.exporter.to_rl_samples()
        print(f"可导出 {len(rl)} 条 RL 样本，示例 prompt: {rl[0]['prompt'] if rl else '(空)'}")


if __name__ == "__main__":
    main()
