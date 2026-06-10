"""框架统一异常体系。

所有自定义异常都继承自 MyAgentError，便于调用方用一个 except 捕获
整个框架抛出的错误，同时保留细分类型用于精确处理。
"""


class MyAgentError(Exception):
    """框架所有异常的基类。"""


class ConfigError(MyAgentError):
    """配置缺失或非法时抛出（如缺少 API Key / model）。"""


class LLMError(MyAgentError):
    """与大模型交互失败时抛出（网络、超时、返回异常等）。"""


class ToolError(MyAgentError):
    """工具注册或执行过程中出错时抛出。"""


class ToolNotFoundError(ToolError):
    """请求的工具名未在注册表中找到。"""


class OutputParseError(MyAgentError):
    """无法从模型输出中解析出预期结构（如 Action / 计划）时抛出。"""
