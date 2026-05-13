# HouseInsight Agent — 实现任务拆解（基于 SPEC v0.1）

垂直切片优先：每一任务交付可运行、可验证的一小条路径。

---

## Task 1: 工程基线与配置

**Description:** 建立 `pyproject.toml`、可安装包、`server.core.config` 从环境变量加载 DashScope/OpenAI 兼容配置；提供 `.env.example` 与 README 中的安装/测试命令。

**Acceptance criteria:**

- [ ] `pip install -e ".[dev]"` 后 `pytest` 可发现 `tests/`
- [ ] `Settings` 含 `base_url`, `api_key`, `model`, `max_iterations`, `log_llm_io`

**Verification:**

- [ ] `pytest -q` 通过（含 smoke）
- [ ] 无 key 时配置对象仍可实例化（用于 mock 模式）

**Dependencies:** None

**Files likely touched:** `pyproject.toml`, `server/core/config.py`, `.env.example`, `README.md`

---

## Task 2: 会话存储与 DataFrame 生命周期

**Description:** 实现进程内 `SessionStore`（`session_id` → `DataFrame`），与 SPEC §4.2 一致：图状态不持久化整表。

**Acceptance criteria:**

- [ ] 上传 CSV 后可按 `session_id` 取回同一引用
- [ ] 删除会话可释放内存（可选 v0.1）

**Verification:**

- [ ] 单元测试：放入/取出/覆盖 DataFrame

**Dependencies:** Task 1

**Files likely touched:** `server/core/session_store.py`, `tests/test_session_store.py`

---

## Task 3: 工具层（探索 + 清洗 + 分析 + 查询 + 反思）

**Description:** 按 §6 实现各工具纯函数 + Pydantic 模型 + `register.py` 注册表；统一截断与错误格式。

**Acceptance criteria:**

- [ ] 列不存在时返回结构化错误，不抛裸异常到上层
- [ ] `get_data_profile` / `get_basic_stats` / `filter_rows` / `parse_numeric_column`（含「万」）有单测

**Verification:**

- [ ] `pytest tests/tools/`

**Dependencies:** Task 1

**Files likely touched:** `server/tools/*.py`, `tests/tools/*.py`

---

## Task 4: Agent 状态与 LangGraph 骨架

**Description:** `state.py` 定义 `AgentState`（含 `add_messages` / `operator.add` 等 reducer）；`graph.py` 编译 `explore→plan→execute→observe` 条件边 + `answer`；`nodes.py` 实现节点逻辑；无 API key 时 `HI_MOCK_LLM=1` 或自动 mock 走通闭环。

**Acceptance criteria:**

- [ ] 单次 `invoke` 在无外网 key 的 CI 下完成并写入 `final_answer`
- [ ] `iteration` 与 `stop_reason` 符合上限语义

**Verification:**

- [ ] `tests/test_graph_smoke.py`

**Dependencies:** Task 2, Task 3

**Files likely touched:** `server/agent/state.py`, `graph.py`, `nodes.py`, `prompts.py`

---

## Task 5: FastAPI 最小 REST

**Description:** `POST /sessions`, `POST /sessions/{id}/upload`, `POST /sessions/{id}/run`, `GET /sessions/{id}/state`, `GET /health`；`run` 驱动同一套 graph。

**Acceptance criteria:**

- [ ] `httpx` 异步测试上传小 CSV 并 `run` 返回最终状态字段
- [ ] 上传大小/行数限制（合理默认值）

**Verification:**

- [ ] `pytest tests/test_api.py`（可使用 `TestClient`）

**Dependencies:** Task 4

**Files likely touched:** `server/api/routes.py`, `server/main.py`

---

## Task 6: WebSocket（可选 MVP）

**Description:** 在 `server/api/ws.py` 推送 `tool_call` / `final` 等事件；可与 REST 并行或延后。

**Acceptance criteria:**

- [ ] 文档说明事件 schema；无实现则标记 DEFERRED

**Verification:** 手动或轻量 async 测试

**Dependencies:** Task 5

**Files likely touched:** `server/api/ws.py`

---

## Task 7: 真实 LLM 路径与提示词硬化

**Description:** 有 `api_key` 时 `plan`/`observe`/`answer` 使用 `ChatOpenAI` + 结构化输出；`prompts.py` 固化中文系统约束。

**Acceptance criteria:**

- [ ] 结构化解析失败时降级为安全错误信息并 `stop_reason=error`

**Verification:** 本地有 key 时手跑一条；CI 跳过

**Dependencies:** Task 4

**Files likely touched:** `server/core/llm.py`, `server/agent/nodes.py`, `server/agent/prompts.py`

---

## Task 8: CLI

**Description:** `python -m server.cli run --csv ... --goal ...` 调用 graph 并打印 `final_answer`。

**Dependencies:** Task 4

**Files likely touched:** `server/cli.py`

---

## 建议实现顺序

`1 → 2 → 3 → 4 → 5 → 7 → 8 → 6`

当前仓库初始提交已覆盖 **1–5、7（基础）、8** 的骨架与可测子集；Task 6 可在后续迭代补全。
