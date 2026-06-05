"""LLM 统一调用层。

MyAgentLLM 封装 OpenAI 兼容接口，对外暴露两个方法：
- think(messages, ...)  流式调用并实时打印，返回完整文本（兼容历史接口）
- invoke(messages, ...) 非流式调用，返回完整文本（供 Agent 内部使用）

相比早期版本，这里把凭证缺失抛成 ConfigError、把调用失败抛成 LLMError，
并支持空响应判断，便于上层做健壮处理。
"""

import os
from typing import Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from .config import Config
from .exceptions import ConfigError, LLMError

# 加载 .env 配置
load_dotenv()


class MyAgentLLM:
    """大模型统一调用客户端（OpenAI 兼容）。"""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        config: Optional[Config] = None,
    ):
        # 优先使用外部传参，否则回退到 .env
        self.model = model or os.getenv("LLM_MODEL_ID")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        self.config = config or Config()
        self.timeout = timeout or self.config.timeout

        # 必填项校验，缺失则报错
        if not self.model:
            raise ConfigError("缺少 model，请传参或在 .env 配置 LLM_MODEL_ID")
        if not self.api_key:
            raise ConfigError("缺少 api_key，请传参或在 .env 配置 LLM_API_KEY")
        if not self.base_url:
            raise ConfigError("缺少 base_url，请传参或在 .env 配置 LLM_BASE_URL")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def think(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
    ) -> str:
        """流式调用大模型，实时打印并返回完整回复。"""
        temperature = self.config.temperature if temperature is None else temperature
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )

            collected = []
            for chunk in response:
                # 跳过无 choices 的心跳/统计帧
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content or ""
                collected.append(content)
                print(content, end="", flush=True)

            print()
            return "".join(collected)
        except Exception as e:
            # 统一包装为 LLMError，由上层决定如何处理
            raise LLMError(f"LLM 流式调用失败: {e}") from e

    def invoke(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
    ) -> str:
        """非流式调用大模型，返回完整回复（不打印）。"""
        temperature = self.config.temperature if temperature is None else temperature
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=False,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMError(f"LLM 调用失败: {e}") from e
