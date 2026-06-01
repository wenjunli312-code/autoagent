# Agent 学习入门 —— 从零开始的实战代码

目录：`agent-learning/`

## 说明

三段渐进式代码，每段加一个新概念。建议按顺序跑，每跑完一段想一下它解决了什么问题、带来了什么新问题。

## 三段代码

| 文件 | 新概念 | 看完能回答的问题 |
|------|--------|-----------------|
| `step1-minimal-agent.py` | LLM + Tool + ReAct 循环 | Agent 核心是怎么转起来的？ |
| `step2-with-memory.py` | 多轮对话 + 记忆 | Agent 怎么记住之前做过什么？ |
| `step3-agent-as-tool.py` | Agent 嵌套（Agent as Tool） | MasterAgent 怎么把子 Agent 当 Tool 调？ |

## 环境准备

```bash
pip install openai
```

Step 1 里把 `api_key` 和 `base_url` 改成你用的模型服务就行（OpenAI / DeepSeek / Qwen 都行）。

## 学习路线建议

1. 先跑 `step1`，看输出的每一轮日志，理解 ReAct 循环
2. 修改 System Prompt 和 Tool 定义，看看 LLM 的行为怎么变
3. 再跑 `step2`，看加了记忆后 Agent 能多轮对话
4. 最后跑 `step3`，理解整个架构里 MasterAgent ↔ Parking Agent 的关系

---

有什么不懂的直接问，一行一行讲都可以。
