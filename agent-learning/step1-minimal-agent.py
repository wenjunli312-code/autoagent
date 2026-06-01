# -*- coding: utf-8 -*-
"""
Step 1: 最简 Agent 骨架 —— LLM + 1个 Tool + ReAct 循环
跑完这段代码，你就理解了 Agent 的核心血液循环。

运行前提：有 openai 库 (pip install openai)
          有效的 API key（配置在环境变量 OPENAI_API_KEY 里，或者改成你的 key）

如果你用的是其他模型（Qwen/DeepSeek），改一下 base_url 和 model 就行。
"""

import json
from openai import OpenAI

# ── 配置 ──────────────────────────────────────────────
# 改成你的 API key 和 base_url
# 如果你用 DeepSeek/Qwen 等，改这里就行
client = OpenAI(
    api_key="your-api-key-here",          # <-- 改成你的 key
    base_url="https://api.openai.com/v1"  # <-- 改用 DeepSeek/Qwen 的 base_url
)

MODEL = "gpt-4o-mini"  # 便宜的模型就行，学习用


# ═══════════════════════════════════════════════════════
# 第一步：定义 Tool（Agent 的能力单元）
# ═══════════════════════════════════════════════════════

def detect_parking_slots(image_description):
    """模拟：检测可用车位"""
    # 真实场景这里会调用感知模块
    return {
        "slots": [
            {"id": "B4-01", "type": "charging", "occupied": True},
            {"id": "B4-02", "type": "charging", "occupied": False},
            {"id": "B4-03", "type": "normal", "occupied": False}
        ],
        "floor": "B4"
    }

def check_shadow(image_description):
    """模拟：判断车位是否有阴凉"""
    return {"slot_id": "B4-02", "has_shadow": True}

# Tool 注册表（Agent 会从这里知道有什么工具可用）
TOOLS = {
    "detect_parking_slots": {
        "fn": detect_parking_slots,
        "description": "检测当前楼层所有可用车位，返回车位列表",
        "parameters": {"type": "object", "properties": {
            "image_description": {"type": "string", "description": "当前图像描述"}
        }}
    },
    "check_shadow": {
        "fn": check_shadow,
        "description": "检查指定车位是否有阴凉遮挡",
        "parameters": {"type": "object", "properties": {
            "image_description": {"type": "string", "description": "当前图像描述"}
        }}
    }
}


# ═══════════════════════════════════════════════════════
# 第二步：构建 LLM 可理解的 Tool Schema
# ═══════════════════════════════════════════════════════

def build_tool_schemas():
    """把我们的 Tool 注册表转成 LLM API 需要的格式"""
    schemas = []
    for name, tool in TOOLS.items():
        schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
        })
    return schemas


# ═══════════════════════════════════════════════════════
# 第三步：执行 Tool 调用
# ═══════════════════════════════════════════════════════

def execute_tool_call(tool_call):
    """执行 LLM 要求的 Tool 调用，返回结果"""
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    
    print(f"  🛠 执行: {name}({args})")
    
    if name not in TOOLS:
        result = {"error": f"未知工具: {name}"}
    else:
        result = TOOLS[name]["fn"](**args)
    
    print(f"  ✅ 结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    return result


# ═══════════════════════════════════════════════════════
# 第四步：Agent 主循环（ReAct）
# ═══════════════════════════════════════════════════════

def run_agent(user_message, max_turns=5):
    """
    Agent 核心循环：
    LLM 推理 → 想调 Tool？→ 调 → 观察结果 → 再推理 → ...
                     ↓ 不调了
                 输出结果
    """
    messages = [
        {"role": "system", "content": "你是一个泊车助手。根据用户需求，使用可用工具找到合适的车位。"},
        {"role": "user", "content": user_message}
    ]
    
    turn = 0
    while turn < max_turns:
        turn += 1
        print(f"\n{'─'*50}")
        print(f"🔄 第 {turn} 轮推理")
        print(f"{'─'*50}")
        
        # 让 LLM 推理
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=build_tool_schemas(),
            tool_choice="auto"
        )
        
        assistant_msg = response.choices[0].message
        
        # LLM 说了什么
        if assistant_msg.content:
            print(f"  💬 LLM 思考: {assistant_msg.content}")
        
        # 检查有没有要调的工具
        if not assistant_msg.tool_calls:
            print(f"\n  ✅ Agent 完成！最终回答: {assistant_msg.content}")
            return assistant_msg.content
        
        # 有 Tool 调用
        messages.append(assistant_msg)
        
        for tool_call in assistant_msg.tool_calls:
            result = execute_tool_call(tool_call)
            # 把工具结果放回对话
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False)
            })
    
    print(f"\n⚠️ 达到最大轮数 {max_turns}，停止")
    return messages[-1]["content"]


# ═══════════════════════════════════════════════════════
# 运行！
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("="*50)
    print("🚀 最简 Agent 启动")
    print("="*50)
    
    result = run_agent("我想停在一个阴凉且有充电桩的车位")
    
    print(f"\n{'='*50}")
    print(f"🏁 最终结果: {result}")
    print(f"{'='*50}")
