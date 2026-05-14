# HouseInsight Agent — 功能指标与性能基线

本文档定义可量化指标（**FC-** 功能、**PF-** 性能），与 [SPEC.md §13 成功标准](SPEC.md#13-success-criteria) 的对应关系，以及自动化测试入口。

## 与 SPEC §13 的映射

| SPEC §13 | 指标覆盖 |
|-----------|----------|
| 13.1 自主性（清洗 + 聚合 + 结论） | FC-01、FC-03 |
| 13.2 适应性（策略变化可追溯） | 仍以 `test_spec_success_criteria` 为主；可加 FC-02 细化 |
| 13.3 准确性（行与源 CSV 一致） | `test_spec_success_criteria.test_row_fingerprint_*` |
| 13.4 可解释性（plan/execute 可追溯） | FC-02 |
| 13.5 护栏（低 MAX_ITER 安全停止） | FC-01（`stop_reason` 枚举） |

## 功能指标（FC）

| ID | 名称 | 定义 | 验证 |
|----|------|------|------|
| **FC-01** | 运行可完成 | `final_answer` 非空；`stop_reason` ∈ `{completed, max_iterations, error}` | `tests/test_functional_metrics.py` |
| **FC-02** | 执行历史可追溯 | `execution_history` 每条含 `tool`、`arguments`、`summary` | `tests/test_spec_success_criteria.py`（及 `assert_execution_history_shape` helper） |
| **FC-03** | 工具覆盖（温江 fixture） | mock 下工具名集合包含 `get_basic_stats`、`parse_numeric_column`、`group_by_summary` 等 | `tests/test_spec_success_criteria.py` |
| **FC-04** | REST `/run` 与直接 `run_agent` 一致 | 相同 `session_id`、相同 DataFrame 快照、相同 `goal`/`max_iterations` 时，两侧 `execution_history` 中 **tool 名多重集**一致（数据重置后各跑一次） | `tests/test_functional_metrics.py` |
| **FC-05** | WebSocket 事件完整性 | 连接后依次为 `schema`、`ready`；`cmd:run` 后存在 `tool_result`、`final`，且以 `done` 结束 | `tests/test_functional_metrics.py` |

## 性能指标（PF）

在 **mock LLM**、固定 CSV 规模下测量，用于本地回归对比；**默认 CI 不跑**（`pytest` 带 `-m "not perf"`）。

| ID | 名称 | 定义 | 验证 |
|----|------|------|------|
| **PF-01** | `run_agent` 墙钟时间 | `time.perf_counter()` 包裹单次 `run_agent` | `tests/perf/test_perf_baseline.py`；仅记录/宽松上界，避免 flaky |
| **PF-02** | HTTP `POST .../run` 总耗时 | `TestClient` 同步 POST 耗时 | 同上 |
| **PF-03** | WS 首包延迟 | 自 `cmd:run` 发送至首个 `tool_result` 的间隔（可选） | 同上（标记 `slow` 时可跳过阈值） |
| **PF-04** | 大表可上传（可选） | 行数阶梯或配置 `max_csv_rows` 下不 413 | 文档化；未强制自动化 |

## 如何运行

```bash
# 默认（不含 perf）
pytest

# 仅性能基线
pytest -m perf tests/perf/

# 全部包含 perf
pytest -m "" --override-ini="addopts="
# 或临时去掉 addopts 后 pytest tests/perf/
```

指标测试入口：`tests/test_functional_metrics.py`、`tests/test_spec_success_criteria.py`、`tests/perf/test_perf_baseline.py`。
