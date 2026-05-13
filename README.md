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

## CLI

```bash
python -m server.cli run --csv path/to.csv --goal "分析这个数据集"
```

## 配置

复制 [.env.example](.env.example) 为 `.env` 并按需填写。
