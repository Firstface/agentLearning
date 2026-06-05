"""内置搜索工具：基于 SerpApi 的 Google 搜索。

沿用「分级降级解析」策略，优先返回最精炼的答案（answer_box / knowledge_graph），
兜底才返回前几条搜索摘要，给模型喂高密度证据。
既提供函数式 search()，也提供 Tool 子类 SearchTool。
"""

import os
from typing import Any, Dict, List

from dotenv import load_dotenv

from ..base import Tool, ToolParameter

load_dotenv()

# 兜底返回的搜索结果条数
MAX_SNIPPETS = 3


def search(query: str) -> str:
    """执行一次 Google 搜索并返回解析后的文本结果。"""
    print(f"🔍 正在执行 [SerpApi] 网页搜索: {query}")
    try:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "错误：SERPAPI_API_KEY 未在 .env 文件中配置。"

        # 延迟导入，未安装 serpapi 时也不影响其它工具
        from serpapi import GoogleSearch

        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "gl": "cn",  # 国家代码
            "hl": "zh-cn",  # 语言代码
        }
        results = GoogleSearch(params).get_dict()

        # 分级降级解析：优先最直接的答案
        if "answer_box_list" in results:
            return "\n".join(str(x) for x in results["answer_box_list"])
        if "answer_box" in results and "answer" in results["answer_box"]:
            return str(results["answer_box"]["answer"])
        if "knowledge_graph" in results and "description" in results["knowledge_graph"]:
            return str(results["knowledge_graph"]["description"])
        if results.get("organic_results"):
            snippets = [
                f"[{i + 1}] {res.get('title', '')}\n{res.get('snippet', '')}"
                for i, res in enumerate(results["organic_results"][:MAX_SNIPPETS])
            ]
            return "\n\n".join(snippets)

        return f"对不起，没有找到关于 '{query}' 的信息。"
    except Exception as e:
        return f"搜索时发生错误: {e}"


class SearchTool(Tool):
    """搜索工具的 Tool 封装。"""

    def __init__(self):
        super().__init__(
            name="Search",
            description=(
                "一个网页搜索引擎。当你需要回答关于时事、事实，"
                "以及在你的知识库中找不到的信息时，应使用此工具。"
            ),
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        query = parameters.get("query", "")
        return search(query)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query", type="string", description="要搜索的查询关键词"
            )
        ]
