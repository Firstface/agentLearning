"""向后兼容入口：保留早期 core/llm.py 的对外符号与运行方式。

历史代码依赖以下符号：MyAgentLLM, search, ToolExecutor, ReActAgent，
并以脚本方式直接运行：
    python my_code/myAgents/my_agents/core/llm.py

为同时支持「作为包导入」和「作为脚本直接运行」两种方式，这里做了兼容处理：
- 作为包导入时（有父包），使用相对导入。
- 作为脚本运行时（无父包），把 myAgents 根目录加入 sys.path 后用绝对导入。
新代码建议直接 `from my_agents import MyAgentLLM, ReActAgent, ...`。
"""

if __package__ in (None, ""):
    # 直接以脚本运行：把 myAgents 根目录（含 my_agents 包）加入 sys.path
    import os
    import sys

    _pkg_root = os.path.dirname(  # .../my_agents
        os.path.dirname(os.path.abspath(__file__))  # .../my_agents/core -> .../my_agents
    )
    _proj_root = os.path.dirname(_pkg_root)  # .../myAgents
    if _proj_root not in sys.path:
        sys.path.insert(0, _proj_root)

    from my_agents.agents.react_agent import ReActAgent
    from my_agents.core.exceptions import ConfigError
    from my_agents.core.llm_client import MyAgentLLM
    from my_agents.core.tool import ToolExecutor
    from my_agents.tools.builtin.search import search
else:
    # 作为包的一部分被导入
    from ..agents.react_agent import ReActAgent
    from ..core.exceptions import ConfigError
    from ..tools.builtin.search import search
    from .llm_client import MyAgentLLM
    from .tool import ToolExecutor

__all__ = ["MyAgentLLM", "search", "ToolExecutor", "ReActAgent"]


if __name__ == "__main__":
    try:
        tool_executor = ToolExecutor()
        tool_executor.register_tool(
            "Search",
            "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。",
            search,
        )

        llm_client = MyAgentLLM()
        # 与旧接口一致：ReActAgent(llm, tool_registry, max_steps)
        agent = ReActAgent(llm_client, tool_executor, 10)
        result = agent.run("如果你是一个专业的文学作家，非常擅长润物无声的夸赞别人，你会如何夸赞V_E这个非常有才华的，非常有才华的人？如果查不到信息，就直接从其他角度例如名字来夸赞他")
        print("\n返回结果:", result)
    except ConfigError as e:
        print(e)
