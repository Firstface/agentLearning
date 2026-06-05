"""
Stage 1: A Minimal Agent Loop
=============================

一个最小但完整的 Agent 循环，覆盖 README Stage 1 的全部 6 项能力：
  1. 用 LLM API 完成普通对话
  2. 让模型输出结构化 JSON（response_format）
  3. 定义工具函数：calculator / search / read_file
  4. 解析模型的 tool_calls
  5. 执行工具并把结果回喂模型
  6. 加最大步数、超时和错误处理

后端：本地 Ollama（OpenAI 兼容协议）。
"""

import os
import json
import math
import time
import httpx
from openai import OpenAI, APITimeoutError, APIConnectionError, APIStatusError

# ---------- 0. 基础配置 ----------
BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
MODEL = os.getenv(
    "OLLAMA_MODEL",
    "modelscope2ollama-registry.azurewebsites.net/qwen/Qwen2.5-1.5B-Instruct-gguf:latest",
)
MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "8"))         # 最大循环步数
REQUEST_TIMEOUT = float(os.getenv("AGENT_TIMEOUT", "30"))  # 单次 LLM 调用超时（秒）

# 客户端：带超时与一次重试
client = OpenAI(
    base_url=BASE_URL,
    api_key="ollama",  # Ollama 不校验
    timeout=httpx.Timeout(REQUEST_TIMEOUT, connect=5.0),
    max_retries=1,
)


# ---------- 1. 工具定义（真实可执行） ----------
def tool_calculator(expression: str) -> str:
    """安全地计算一个算术表达式。"""
    allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
    try:
        # 仅允许 math 名称，禁用 builtins，防止任意代码执行
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def tool_search(query: str) -> str:
    """模拟搜索（真实场景接 SerpAPI / Bing / Tavily）。"""
    fake_db = {
        "python": "Python 是一门高级动态类型解释型编程语言。",
        "agent": "Agent 是能自主规划、调用工具并完成多步任务的 LLM 系统。",
    }
    for k, v in fake_db.items():
        if k in query.lower():
            return v
    return f"未找到关于 '{query}' 的结果（mock）。"


def tool_read_file(path: str) -> str:
    """读取本地文件前 2000 字符。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(2000)
    except FileNotFoundError:
        return f"ERROR: 文件不存在: {path}"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


# 工具注册表：name -> (callable, 提取参数的 key 列表)
TOOL_REGISTRY = {
    "calculator": (tool_calculator, ["expression"]),
    "search":     (tool_search,     ["query"]),
    "read_file":  (tool_read_file,  ["path"]),
}

# 暴露给 LLM 的 tools schema（OpenAI 标准格式）
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算一个算术表达式，例如 '3*3' 或 'sqrt(16)+1'。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "要计算的表达式"}
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "搜索一个关键词的解释（模拟搜索）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取一个本地文件的前 2000 字符。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件绝对路径"}
                },
                "required": ["path"],
            },
        },
    },
]


# ---------- 2. 系统 Prompt：要求最终答案用结构化 JSON ----------
SYSTEM_PROMPT = """你是一个会调用工具解决问题的 AI 助手。

工作流程：
1. 如果需要计算/搜索/读文件，请调用对应工具（tool_calls）。
2. 拿到工具结果后继续推理，可继续调用其它工具。
3. 当你已经得到最终答案时，必须仅以如下 JSON 格式回复（不要再调用工具）：
   {"answer": "<给用户的最终答案>", "end": true}

注意：
- end=true 表示任务完成；end=false 表示还在思考，但此时应优先调用工具而非纯文本。
- JSON 必须是合法的，不要附加任何前后缀。
"""


# ---------- 3. 工具调用解析 + 执行 ----------
def execute_tool_call(tool_call) -> str:
    """根据模型给出的 tool_call，执行对应函数并返回结果字符串。"""
    name = tool_call.function.name
    raw_args = tool_call.function.arguments or "{}"
    try:
        args = json.loads(raw_args)
    except json.JSONDecodeError:
        return f"ERROR: 参数不是合法 JSON: {raw_args}"

    if name not in TOOL_REGISTRY:
        return f"ERROR: 未知工具 {name}"

    func, _ = TOOL_REGISTRY[name]
    try:
        return func(**args)
    except TypeError as e:
        return f"ERROR: 参数错误: {e}"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


# ---------- 4. 解析最终结构化 JSON ----------
def parse_final_answer(content: str):
    """尝试从 content 中提取 {answer, end:true}。返回 (is_final, answer 或 None)。"""
    if not content:
        return False, None
    text = content.strip()
    # 兼容模型在 JSON 外多写解释：截取第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return False, None
    candidate = text[start : end + 1]
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return False, None
    if str(data.get("end", "")).lower() == "true":
        return True, data.get("answer", "")
    return False, None


# ---------- 5. 主循环 ----------
def run_agent(user_query: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    for step in range(1, MAX_STEPS + 1):
        print(f"\n========== Step {step}/{MAX_STEPS} ==========")

        # ---- 5.1 调 LLM（带超时/错误处理）----
        try:
            t0 = time.time()
            resp = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
            )
            print(f"[LLM 调用耗时] {time.time() - t0:.2f}s")
        except APITimeoutError:
            print("[ERROR] LLM 调用超时，终止循环。")
            return "(超时)"
        except APIConnectionError as e:
            print(f"[ERROR] LLM 连接失败：{e}")
            return "(连接失败)"
        except APIStatusError as e:
            print(f"[ERROR] LLM 返回非 2xx：{e.status_code} {e.message}")
            return "(API 错误)"
        except Exception as e:
            print(f"[ERROR] 未预期异常：{type(e).__name__}: {e}")
            return "(未知错误)"

        msg = resp.choices[0].message
        # 把 assistant 消息原样写回上下文（包含 tool_calls）
        messages.append(msg.model_dump(exclude_none=True))
  
        # ---- 5.2 处理工具调用 ----
        if msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"[Tool Call] {tc.function.name}({tc.function.arguments})")
                result = execute_tool_call(tc)
                print(f"[Tool Result] {result[:200]}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.function.name,
                    "content": result,
                })
            continue  # 工具结果回喂后继续下一轮

        # ---- 5.3 处理最终答案 ----
        content = msg.content or ""
        print(f"[Assistant] {content}")
        is_final, answer = parse_final_answer(content)
        if is_final:
            print("\n========== ✅ 任务完成 ==========")
            return answer or content

        # 既没工具调用又不是最终 JSON → 让它再试
        messages.append({
            "role": "user",
            "content": '请按要求继续：要么调用工具，要么以 {"answer": "...", "end": true} 收尾。',
        })

    print("\n========== ⚠️ 达到最大步数 ==========")
    return "(达到最大步数仍未完成)"


# ---------- 6. 入口 ----------
if __name__ == "__main__":
    query = "请先计算 sqrt(64)+2 等于多少，再告诉我搜索 'agent' 的结果，最后总结成一句话。"
    final = run_agent(query)
    print("\n=== 最终答案 ===")
    print(final)
