import os
import json
from openai import OpenAI

BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
MODEL = os.getenv(
    "OLLAMA_MODEL",
    "modelscope2ollama-registry.azurewebsites.net/qwen/Qwen2.5-1.5B-Instruct-gguf:latest",
)


# OpenAI Chat Completions 的标准工具格式：外层 type=function，function 内嵌套 name/parameters
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "A simple calculator that can evaluate expressions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The expression to evaluate",
                    },
                },
                "required": ["expression"],
            },
        },
    },
]

# 注意：OpenAI() 客户端构造里没有 tools 参数，tools 只在 chat.completions.create 里传
client = OpenAI(
    base_url=BASE_URL,
    api_key="ollama",  # 占位符，Ollama 不会校验
)


# 系统提示：要求模型用结构化 JSON 回复，得到最终答案时 end=true
SYSTEM_PROMPT = (
    "你是一个 AI 助手。"
    "请始终以 JSON 格式回复，严格遵守如下 schema："
    '{"回答":"<你的答案或思考>", "end":"true 或 false"}。'
    "当你已经得到用户问题的最终答案时，将 end 设置为 \"true\"；"
    "否则保持 \"false\"。"
    "整个回复中只输出这一段 JSON，不要任何额外的解释或前后缀文字。"
)

# 上下文消息列表（首次输入：先算 3*3，再数 1 到结果之间有多少质数）
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {
        "role": "user",
        "content": "请先计算 3*3 等于多少，然后告诉我从 1 到这个结果之间有多少个质数。",
    },
]


def is_finished(content: str) -> bool:
    """解析模型返回的字符串，判断 end 字段是否为 true。

    1. 优先用 json.loads 严格解析。
    2. 兜底：从字符串尾部抓取 "end":"true" 子串。
    """
    if not content:
        return False

    text = content.strip()

    # 第 1 步：严格 JSON 解析
    try:
        data = json.loads(text)
        return str(data.get("end", "")).lower() == "true"
    except json.JSONDecodeError:
        pass

    # 第 2 步：兜底——去除空白后看尾部是否含 "end":"true"
    compact = "".join(text.split()).lower()
    return '"end":"true"' in compact


# 用 bool 控制的主循环
finished = False
turn = 0
while not finished:
    turn += 1
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
    )
    assistant_content = response.choices[0].message.content or ""
    print(f"\n--- Turn {turn} ---")
    print("Assistant:", assistant_content)

    # 把模型回复追加到上下文，形成多轮对话
    messages.append({"role": "assistant", "content": assistant_content})

    # 判断是否得到最终答案
    if is_finished(assistant_content):
        finished = True
        break

    # 还没结束 → 追加一条 user 提示，催它继续
    follow_up = "请继续推理，给出最终答案后把 end 设为 \"true\"。"
    messages.append({"role": "user", "content": follow_up})

print("\n=== 对话结束 ===")
print(f"总轮数：{turn}，消息条数：{len(messages)}")
