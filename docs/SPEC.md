# HouseInsight Agent — 产品与技术规格（SPEC v0.1）

> **文档性质**：本 SPEC 为「实现前」的单一事实来源（SSOT），与仓库内 `.cursor/rules/spec-driven-development/SKILL.md` 对齐。  
> **当前仓库状态**：业务代码以 `server/` 为根包；本文件为 v0.1 定稿基线。

---

## ASSUMPTIONS（v0.1 已采纳）

1. **单用户会话优先**：首版以「单次上传 CSV + 单次分析会话」为主；多租户/持久化用户账号非 v0.1 必选项。  
2. **数据驻留**：分析在服务端进程内完成；CSV 以会话级临时存储（磁盘或内存映射）为主，不强制引入独立 OLAP 引擎。  
3. **`search_listings` v0.1 行为**：采用「LLM 将自然语言解析为结构化筛选条件 → 校验后调用 `filter_rows` / 等价逻辑」；**不做向量检索与独立全文搜索引擎**（可作为后续增强）。另见 **`search_text`**：多列字面子串匹配（OR/AND 组合由参数表达），仍属受控工具而非任意代码。  
4. **DashScope**：通过 OpenAI 兼容客户端调用 Qwen；API Key 来自环境变量，可切换任意 OpenAI 兼容 Base URL。  
5. **前端**：v0.1 允许「CLI 或最小 API + curl」先跑通闭环；React 为 v0.2+ 可选增量。

---

## Resolved Decisions（原 §14 Open Questions）

| 议题 | 决议 |
|------|------|
| 达到 `max_iterations` 时 | 仍进入 `answer` 节点生成 `final_answer`，并设置 `stop_reason=max_iterations`；HTTP 层仍返回成功与会话状态（**不**用 429）。正文中说明未完成任务与建议下一步。 |
| 房源唯一标识 | 若 CSV 无 `id` 列，在 `explore` 阶段注入只读列 `_hi_row_fp`（对行内容稳定 SHA256 截断），供引用与校验；若已有 `id` 则保留。 |
| 默认语言 | 系统与 Agent 面向用户的分析结论、时间线说明默认 **简体中文**；代码与日志标识符可为英文。 |

---

## 1. Objective（目标）

### 1.1 一句话定位

一个能**自主**分析二手房 CSV 数据的智能体：像人类分析师一样**探索 → 规划 → 执行工具 → 观察 → 反思调整**，最终输出**有洞察的结论**，并能在数据范围内**准确回答具体房源查询**。

### 1.2 用户与成功画面

- **用户**：有 CSV、希望快速得到分析结论与可追问的「数据分析师替身」。  
- **成功**：用户给出高层目标（如「分析这个数据集」）后，Agent 在**无人介入**下完成探索、清洗决策、分析、总结；全过程**可追溯**；房源级回答与 CSV **一致**（可引用行标识或关键字段）。

### 1.3 非目标（v0.1 明确不做）

- 不抓取外网实时房源、不保证「市场实时性」。  
- 不执行任意用户/模型生成的 Python 代码（**仅允许注册工具**）。  
- 不承诺跨会话长期记忆（除非后续单独 SPEC）。

---

## 2. Principles（核心原则）

| 编号 | 原则 | 实现含义 |
|------|------|----------|
| P1 | LLM 决策，代码执行 | 计划、选工具、反思由 LLM；数值与表变换由 pandas + 工具函数完成。 |
| P2 | 工具是唯一行动方式 | Agent 输出经 schema 校验的「工具调用」；禁止 `exec` / 动态 `eval` 用户数据相关代码。 |
| P3 | 完全自主 | 默认无需逐步确认；提供「最大迭代次数」与超时作为安全阀。 |
| P4 | 状态可追溯 | 思考摘要、计划、每次工具入参/出参摘要、错误与迭代计数持久化到会话日志（见 §8）。 |

---

## 3. Scope & Phasing（范围与分期）

### 3.1 MVP

- LangGraph 闭环：`explore → plan → execute → observe` 循环，终止于 `answer`。  
- FastAPI：**上传 CSV、启动一次分析、查询会话状态/日志**；WebSocket 提供 **LangGraph 对齐的实时事件流**（§7.2）；最小 React 前端见仓库 `web/`。  
- 工具集：§6 所列契约；实现可分两批：**探索+清洗+基础分析** 先于 **反思+复杂 NL 查询**。  
- DataFrame **不**完整序列化进 checkpoint；见 §4.2。

### 3.2 v0.2+

- WebSocket 与 `run` 的深度集成（取消/回放）、会话持久化、配额、鉴权。  
- `search_listings` 的语义检索/embedding。  
- 会话持久化、配额、鉴权。

---

## 4. Architecture（架构）

### 4.1 技术栈

- Python **3.10+**  
- **LangGraph**、**LangChain**  
- **pandas**  
- **FastAPI** + **uvicorn**  
- LLM：**DashScope / Qwen**（OpenAI 兼容），配置：`BASE_URL`、`API_KEY`、`MODEL`

### 4.2 状态与数据持有

| 字段 | 类型 | 说明 |
|------|------|------|
| `session_id` | str | 会话标识 |
| `messages` | List[Message] | 对话与系统摘要 |
| `artifact_uri` / runtime store | str | 会话级 DataFrame 存放在进程内 `SessionStore`，**不**写入图 checkpoint 全表 |
| `data_profile` | Dict | 列名、dtype、缺失率、样例行、行数 |
| `plan` | List[PlanStep] | `tool_name`、`arguments`、`rationale`（可选） |
| `plan_generation_error` | str \| null | 非 mock 下 `plan` 节点 LLM 结构化输出失败时写入；`execute` 将其记入失败记录并通常触发 `stop_reason=error` |
| `execution_history` | List[ExecutionRecord] | 工具名、参数摘要、结果摘要、错误、耗时 |
| `iteration` | int | 自增；硬上限见环境变量 `MAX_ITERATIONS`（默认 **10**）；清洗阶段另受 `MAX_CLEANING_ITERATIONS` 与 `phase` 约束（见 §7.2） |
| `stop_reason` | str | `max_iterations` / `completed` / `error` / `user_abort` |
| `final_answer` | str | 最终用户可见回复 |
| `prior_transcript` | str | **会话内多轮**：由上一轮 `messages` 格式化的节选，仅写入本轮 `initial`，供 LLM prompt；不写入 checkpoint 全表 |

### 4.2.1 会话内多轮（非持久化）

- 同一 `session_id` 下多次 `POST /sessions/{id}/run` 或 WebSocket `cmd:run`：从 `last_state.messages` 生成 `prior_transcript`（「用户：/助手：」文本，**尾部**截断，上限见环境变量 `MAX_PRIOR_TRANSCRIPT_CHARS`，默认 4000）；`plan` / `observe` / `answer` 的 prompt 均携带该节选；**每轮** `execution_history` 与迭代仍从空/零开始，与上一轮工具轨迹不混用。  
- `answer` 节点将本轮 `final_answer` 追加为 `AIMessage`，以便下一轮持久化到 `last_state`。  
- **不**跨进程：服务重启后无对话历史；与 §1.3「不承诺跨会话长期记忆」一致，此处为同会话多轮而非账号级记忆。

---

## 5. Agent Graph（LangGraph）

### 5.1 节点

| 节点 | 职责 |
|------|------|
| `explore` | 刷新 `data_profile`；必要时注入 `_hi_row_fp` |
| `plan` | 生成下一步计划（建议每次执行只消费一步） |
| `execute` | 校验并调用工具，更新 DataFrame 与 `execution_history` |
| `observe` | 判断是否继续规划或结束 |
| `answer` | 生成 `final_answer` |

### 5.2 路由与终止

- `iteration >= MAX_ITER` → `answer`，`stop_reason=max_iterations`。  
- 工具失败：记录错误；`observe` 决定重试、换工具或降级。  
- **`plan` 结构化生成失败**（存在 `plan_generation_error` 或最近一步 `execution_history` 中 `ok=false` 且为计划/未知工具错误）：`observe` 应结束循环并 `stop_reason=error`（真实 LLM 路径下 `observe` 对工具失败有硬兜底）。

### 5.3 提示词

各节点独立模板；`plan` / `observe` 优先结构化（JSON / Pydantic）解析。

---

## 6. Tools（工具契约）

**通用约束**：纯函数风格；返回 LLM 的行默认截断（如 50 行）并标记 `truncated`；列名校验；默认不写用户磁盘。

| 类别 | 工具名 | 职责 |
|------|--------|------|
| 探索 | `get_data_profile` | 列、dtype、缺失率、样例、行数 |
| 探索 | `get_basic_stats` | 数值列描述统计 |
| 清洗 | `remove_duplicates` | 按列集合去重 |
| 清洗 | `filter_outliers` | IQR 或上下界 |
| 清洗 | `fill_missing` | 均值/中位数/众数/常数 |
| 清洗 | `parse_numeric_column` | 文本房价等 → float |
| 清洗 | `parse_house_info_column` | 解析「房屋信息」管道串，生成 `hi_室`、`hi_厅`、`hi_建面` 等列 |
| 分析 | `group_by_summary` | 分组聚合 |
| 分析 | `filter_rows` | 结构化条件筛选（有限深度 AND/OR） |
| 分析 | `search_text` | 多文本列、多关键词的字面 `contains` 检索（`any_term_any_column` / `all_terms_concat`）；用于卖点/交通等非结构化表述 |
| 分析 | `correlation_analysis` | 两列相关系数 |
| 分析 | `top_k_values` | Top-K 频次 |
| 查询 | `search_listings` | 入参为 **已由 LLM 解析好的** 结构化条件，校验后走 `filter_rows` |
| 反思 | `compare_cleaning_results` | 对比两次 profile / 指标 |

每个工具：Pydantic 入参/出参模型 + 单元测试。

---

## 7. API / CLI

### 7.1 REST（最小集）

- `POST /sessions`  
- `POST /sessions/{id}/upload`  
- `POST /sessions/{id}/run` — body：`goal`，可选 `phase`（`clean` | `analyze`，默认 `analyze`），`options.max_iterations`  
- `GET /sessions/{id}/state`  
- `DELETE /sessions/{id}` — 删除会话元数据并释放 `SessionStore` 中对应 DataFrame  
- `GET /health`

### 7.2 WebSocket（实时事件流）

连接：`WS /sessions/{session_id}/ws`（[`server/api/ws.py`](../server/api/ws.py)）。与 REST `POST /sessions/{id}/run` **并存**：REST 仍为同步一次返回；WS 用于**长连接 + 流式事件**（[`run_agent_streaming`](../server/agent/graph.py) 基于 LangGraph `stream_mode=["updates","values"]`）。

**握手**（连接后立即推送，无需客户端先发消息）：

1. `{"event":"schema", "session_id": "...", "version": 1, "events": [...]}`  
2. `{"event":"ready", "session_id": "..."}`

**客户端命令**（JSON 文本帧）：

```json
{"cmd":"run","goal":"分析这个数据集","max_iterations":10,"phase":"analyze"}
```

- 可选 **`phase`**：`"clean"` 表示上传后**自动清洗**（服务端将 `observe` 迭代上限压至 `min(请求 max_iterations, MAX_CLEANING_ITERATIONS)`，且计划/观察提示偏向「基础画像即可」）；`"analyze"` 或省略表示**用户对话分析**（沿用 `MAX_ITERATIONS`）。前端「运行清洗」应发 `"phase":"clean"`。  
- 须已 `POST /sessions` 且 `POST .../upload` 成功；否则推送 `event:error`。  
- 同一会话并发第二次 `run`：在已有任务未完成时返回 `event:error`（已有任务运行中）。  

**运行期事件**（节选；均含 `session_id`，多数含 `ts`）：

| `event` | 说明 |
|---------|------|
| `node_enter` / `node_exit` | `node`：explore / plan / execute / observe / answer；`node_exit` 可含缩略 `payload` |
| `tool_call` | `tool`, `arguments` |
| `tool_result` | `tool`, `ok`, `summary`（截断）, `error` |
| `final` | `final_answer`, `stop_reason` |
| `error` | `message` |
| `done` | 本轮流结束标记 |

会话终态仍写入与 REST `run` 相同的内存元数据（`persist_session_state`），`GET /sessions/{id}/state` 可复查。

**前端**：见仓库 [`web/`](../web/)（Vite + React）；开发时 `npm run dev` 与 `uvicorn` 分端口，`vite.config.ts` 将 `/sessions` HTTP 与 WS 代理到后端。

### 7.3 CLI

`python -m server.cli run --csv path --goal "..."`（实现以 README 为准）

---

## 8. Observability

结构化日志字段：`session_id`, `iteration`, `node`, `tool`, `latency_ms`, `error_code`；`LOG_LLM_IO` 默认关闭。

---

## 9. Security

上传大小/行数限制；工具参数白名单；NL 仅映射到有限 DSL；密钥仅环境变量。

---

## 10. Testing

- `tests/tools/`：各工具单元测试  
- 图集成测试：mock LLM 固定输出  
- 可选 integration：真实 DashScope 冒烟（CI 跳过无 key）  
- **功能与性能指标**：[METRICS.md](METRICS.md)（FC/PF 与 §13 映射、perf 运行方式）

---

## 11. Project Structure

```
houseinsight-agent/
├── server/
│   ├── agent/
│   ├── tools/
│   ├── core/
│   ├── api/
│   ├── main.py
│   └── cli.py
├── docs/
│   ├── SPEC.md
│   └── TASKS.md
├── tests/
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 12. Commands

见 [README.md](../README.md)。

---

## 13. Success Criteria

自动化验收见 [`tests/test_spec_success_criteria.py`](../tests/test_spec_success_criteria.py)（`pytest tests/test_spec_success_criteria.py`）。

1. **自主性**：高层目标下完成 ≥1 清洗 + ≥1 聚合 + 结论。  
2. **适应性**：脏数据下 `execution_history` 体现策略变化。  
3. **准确性**：指定行/键与源 CSV 一致（自动化断言）。  
4. **可解释性**：plan/execute 可追溯。  
5. **护栏**：低 `MAX_ITER` 下安全停止。

---

## 14. Change Log

- **v0.1**：初版 SPEC + 开放问题决议（max iter、`_hi_row_fp`、中文默认）。
