行，先把 **Planner + Agent** 做出来（不带 EEG 也能用），做成一个能放简历的“可交付系统”。下面是一个 **10 天可执行**、每天有明确产物的计划（你照做就能跑通）。

---

## 目标（MVP）

一个语音/文本输入的智能 planner：

* 你说一句：“我今天要做 A/B/C”
* Agent 输出：**任务拆解 + 时间块 + 依赖/材料 + 风险点 + 今日可执行版本**
* 支持：一键生成日程、动态调整、执行记录、复盘总结（后面再接 EEG 做 gating）

---

## 技术栈（推荐最稳组合）

* 前端：Next.js（或 React + Vite）
* 后端：FastAPI（Python）
* Agent：OpenAI API（function calling / tools）
* 数据库：Postgres（本地 docker）
* 语音：Whisper（先用文件/浏览器录音上传转文字；后期再做实时）
* 日历：先导出 `.ics` 文件（后面再做 Google Calendar OAuth）

---

## 定义“数据结构”和 MVP 边界（最重要）

**产物：`schema.md` + `prompts.md`**

1. 定义核心对象（必须固定格式，避免 agent 胡写）

* Goal（目标）
* Task（任务：名称、估时、能量等级、依赖、材料、截止）
* Plan（时间块：start/end，task_id，mode：deep/light/admin）
* Log（执行：开始/结束/完成度/阻塞原因）

2. 定义 MVP 必须功能：

* 输入目标（文本）
* 自动拆解任务
* 自动排今天的时间块（比如 9:00–18:00）
* 生成“今日计划”页面
* 每个时间块支持：完成/跳过/延后，并自动重排剩余计划

---

## 搭后端骨架 + 数据库

**产物：FastAPI 项目可跑 + Postgres 表**

* Docker compose 起 Postgres
* FastAPI：/goals, /plans, /logs 基础 CRUD
* 表结构：goals, tasks, plans, logs

---

## 写“拆解 Agent”（Planner 的核心能力 1）

**产物：`/agent/decompose` 可用**
输入：用户一句话目标 + 偏好（工作时间、截止、优先级）
输出（JSON）：tasks[]，每个 task 有：

* title
* estimate_minutes
* energy (low/med/high)
* dependencies (ids or titles)
* required_materials
* acceptance_criteria（完成标准，避免空转）
* risk_blockers（可能卡点）

关键：让 agent **只能输出 JSON**（后端做严格校验，不合法就重试一次）。

---

## 写“排程 Agent”（核心能力 2）

**产物：`/agent/schedule` 可用**
输入：tasks + 今日可用时间段（比如 9-12, 13-18）+ 偏好（番茄 50/10、午饭 1h）
输出：time_blocks[]
规则先写死也行：

* 高能量任务放上午
* 深度任务块 50-90min
* 任务拆分到多个块（长任务）
* 必须插休息

---

## 前端 MVP 页面（能用就行）

**产物：能从浏览器完成完整流程**
页面：

1. 输入目标（文本）
2. 点击生成 → 显示任务列表（可编辑估时/优先级）
3. 点击排程 → 显示今日时间表（时间轴/列表）
4. 每个 block 有按钮：Done / Skip / Delay 15m / Move to tomorrow

---

## 动态重排（核心能力 3）

**产物：你点“Delay/Skip”后剩余计划自动更新**
做法：

* 前端操作 → 写入 log
* 调用 `/agent/reschedule`：输入剩余 blocks + 当前时间 + 未完成任务
* 输出新的 blocks（只改未来，不动过去）
  这一步会让产品从“生成一次就死”变成“真的能用”。

---

## 语音输入（先别追求实时）

**产物：录音上传→转文字→生成计划**

* 浏览器录音（WebAudio）上传到后端
* 后端用 Whisper（本地或 API）转文字
* 文字丢给 decompose agent

---

## 复盘总结（核心能力 4）

**产物：每日总结页**
输入：当天 logs + 计划 vs 实际
输出：

* 完成率、最常见阻塞原因
* 明天 3 个优先事项
* “可改进建议”（例如：估时总偏短、上午安排太重）
  这也是你未来接 EEG 的接口：EEG=状态；复盘=策略优化。

---

## 导出与展示（让它像产品）

**产物：导出 `.ics` + 演示数据**

* 一键导出今日计划到 iCalendar 文件
* 加一个 demo 模式：一键生成“求职日程/学习日程/健身日程”样例

---

## Day 10：包装成作品集（简历杀伤力）

**产物：GitHub README + 2 分钟录屏**
README 结构：

* Problem：计划难执行、易拖延、频繁变化
* Solution：Agent 拆解 + 自动排程 + 动态重排 + 复盘闭环
* Architecture：前后端图 + 数据结构
* Limitations：估时偏差、个人偏好需学习
* Next：EEG gating（疲劳/分心）接入重排策略

---

## 你马上能开干的“第一步任务清单”（今天就做）

1. 写 `Task` JSON schema（字段固定）
2. 写 decompose prompt（强制输出 JSON）
3. FastAPI 起一个 `/agent/decompose` 接口（先不接 DB 都行）
4. 用 Postman/curl 测 10 条输入，看输出稳定不稳定

---

## 接 EEG 的位置（先预留，不做）

在 reschedule policy 里预留一个字段：`state_signal`
以后 EEG 给你：

* fatigue_risk 0-1
* restlessness 0-1
  然后 policy 规则：
* fatigue 高：把 high-energy tasks 后移 + 插入恢复块
* restlessness 高：把 deep block 切成短块 + 插入 2min reset

---
用 **Python FastAPI**\
