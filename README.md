# HouseInsight Agent

基于 LangGraph / LangChain 的二手房 CSV 自主分析智能体（SPEC 见 [docs/SPEC.md](docs/SPEC.md)）。

## 环境

- Python 3.10+
- 可选：阿里云 DashScope（OpenAI 兼容）。无 Key 时设置 `HI_MOCK_LLM=1` 可走通闭环。

## 安装

```bash
pip install -e ".[dev]"
```

## 常用命令

```bash
# 单元测试
pytest

# 静态检查（可选）
ruff check server tests
ruff format server tests

# 启动 API
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

## Web 前端（Vite + React）

```bash
cd web
npm install
npm run dev
```

默认将 `http://localhost:5173` 经代理访问 `http://127.0.0.1:8000` 的 `/sessions`（含 WebSocket）。后端需单独启动：

```bash
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

生产构建：`cd web && npm run build`，产物在 `web/dist`；若前后端不同域，设置 `web/.env` 中 `VITE_API_BASE` 为 API 根 URL。

## CLI

```bash
python -m server.cli run --csv path/to.csv --goal "分析这个数据集"
```

## 配置

复制 [.env.example](.env.example) 为 `.env` 并按需填写。可选：环境变量 `CORS_ORIGINS`（逗号分隔）供浏览器直连 API 时跨域。
