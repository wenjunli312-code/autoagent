# Parking Agent Design Doc — 模板框架

> 目标：设计在 Thor-U 上运行的自然语言泊车 Agent

---

## 1. 项目概述

### 1.1 背景
- 北京车展已验证 MDC510 + 8775 + 云端大模型链路
- 第一阶段：云端车位判断大模型部署到 Thor 端
- **我们的工作重点：Agent 框架设计，模型相关由其他团队跟进**

### 1.2 目标
- 用户通过自然语言指令触发自主泊车
- Agent 理解指令、感知环境、规划执行、处理异常

### 1.3 非目标（明确不做）
- 模型训练 / fine-tune
- 云端服务
- 座舱 MasterAgent 的全量设计

---

## 2. 系统上下文

### 2.1 硬件拓扑

```
┌──────────────┐          ┌──────────────┐
│  8775        │          │ Thor-U       │
│ MasterAgent  │◄─state──►│ Parking      │
│ Cockpit      │  summary │ Agent        │
└──────────────┘          └──────────────┘
```

### 2.2 与外部的接口
| 接口 | 对端 | 内容 |
|------|------|------|
| 用户指令 | MasterAgent → Parking Agent | 自然语言泊车需求 |
| 状态同步 | Parking Agent ↔ MasterAgent | 进度、失败、完成 |
| 感知输入 | Thor 感知栈 → Parking Agent | 环视/前视图像 |
| 控制输出 | Parking Agent → 规控模块 | waypoints 或规划约束 |

---

## 3. Agent 设计

### 3.1 Agent 循环（ReAct 模式）

```
用户输入
    │
    ▼
┌─────────────┐
│ LLM 推理     │───思考(Thought)──┐
│ (Qwen/其他) │                  │
└─────────────┘                  │
    │  需要工具调用?               │ 不需要
    ▼ 是                          ▼
┌─────────────┐             ┌──────────┐
│ 执行工具     │──观察结果──→│ 输出应答  │
│ (感知/规划等)│             │ (轨迹/    │
└─────────────┘             │  指令)    │
    │                       └──────────┘
    └──→ 回到 LLM 推理 ────→ 循环直到完成或失败
```

### 3.2 Tool 定义（需要设计的核心）

每个 Tool 需要定义：
- **名称**：如 `detect_parking_slots`
- **输入参数**：JSON Schema
- **输出格式**：JSON
- **失败模式**：什么情况下返回 error，Agent 如何处理

**候选 Tool 清单（待讨论）：**

| Tool | 功能 | 输入 | 输出 |
|------|------|------|------|
| `detect_slots` | 检测可用车位 | 图像帧（前视+环视） | 车位列表[slot_id, pos, type, occupied] |
| `check_charger` | 检查车位是否有充电桩 | slot_id | bool |
| `classify_floor` | 判断当前楼层（B1/B2/B3...） | 图像帧 | floor_label |
| `plan_trajectory` | 规划泊车轨迹 | target_slot_id, ego_state | waypoints[] |
| `check_clearance` | 检查路径是否畅通 | waypoints | bool + 障碍物信息 |
| `inform_user` | 向用户/座舱输出信息 | message | ok |
| `retry_or_abort` | 放弃或重试 | reason | decision |

### 3.3 Memory 策略

| 层级 | 存储位置 | 内容 | 生命周期 |
|------|----------|------|----------|
| L1（短期） | Thor 本地内存 | 当前泊车任务的上下文（前N轮推理） | 泊车完成后清除 |
| L2（共享） | 跨芯片同步 | 当前状态+结果摘要 | 同步给 MasterAgent |
| L3（长期） | 8775 持久化 | 泊车统计、失败模式学习 | 持久化 |

### 3.4 异常处理策略

需要考虑的异常场景：

| 场景 | Agent 行为 |
|------|-----------|
| 目标车位被占 | 重新检测可用车位 → 推荐替代选项 |
| 路径被阻挡 | 等待 + 重试 → 超时后告知用户 |
| 感知失败（脏污/低光） | 请求用户确认或换车位 |
| Agent 推理超时 | fallback 到保守安全策略（刹车等待） |
| 跨芯片通信异常 | Thor 本地自治完成泊车或安全停止 |

---

## 4. 跨芯片同步协议

### 4.1 State Summary 格式（初步）

```json
{
  "status": "in_progress | completed | failed | aborted",
  "current_step": "slot_detection | trajectory_planning | executing | retrying",
  "target_slot": "B4-03",
  "progress_pct": 60,
  "error": null | "obstacle_detected",
  "eta_seconds": 15
}
```

### 4.2 同步频率
- 正常执行：每步完成后同步
- 异常：立即同步
- 心跳：5 秒一次

---

## 5. 第一阶段边界

第一阶段（验证链路）的简化原则：

- Agent 使用**简单循环**（不引入子图/并行）
- Tool 先实现**核心 3-4 个**（slot 检测、车位定位、轨迹规划反馈）
- Memory 只做 L1（不急于 L3 持久化）
- 异常处理先只做最基本的 2-3 种场景

---

## 6. 技术选型（待定）

| 组件 | 选项 | 推荐 |
|------|------|------|
| Agent 框架 | LangGraph / smolagents / 自定义 | 待讨论 |
| LLM 推理引擎 | TensorRT-LLM / llama.cpp / ... | 模型团队决定 |
| IPC 通信 | DDS / SOME/IP / 共享内存 | 沿用现有 |
| 仿真验证 | 已有仿真环境 / 实车 | 待确认 |

---

## 7. 风险和未知

1. Thor 上 LLM 推理延迟能否满足泊车实时性要求？
2. Agent 循环多步推理的端到端 Latency 是多少？
3. 跨芯片同步对 8775 和 Thor 的负载影响？
4. Agent 异常的覆盖率——什么样的情况算「Agent 解决不了」？

---

> 下一步：逐节讨论填充内容，先确定 Agent 循环和 Tool 清单。
