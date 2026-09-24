# 常用命令

本项目使用 [uv](https://docs.astral.sh/uv/) 管理依赖与执行命令。Python 版本要求 `>=3.12`（见 `.python-version`）。

## 环境准备

```bash
# 安装依赖（含 dev 组：ruff / mypy / pytest）
uv sync

# 配置环境变量
cp .env.example .env
```

## CLI 运行

CLI 入口为 `data-platform-analysis`（见 `pyproject.toml` 的 `[project.scripts]`），也可用 `python -m data_platform_analysis`。

```bash
# 查看帮助
uv run data-platform-analysis --help

# 查看当前生效的非敏感配置
uv run data-platform-analysis config

# 同时采集 DataWorks 和 MaxCompute
uv run data-platform-analysis export

# 只采集指定 Workspace 的 DataWorks（id 必须已在配置中）
uv run data-platform-analysis export --workspace 123456

# 只采集 DataWorks
uv run data-platform-analysis dataworks
uv run data-platform-analysis dataworks --workspace 123456

# 只采集 MaxCompute
uv run data-platform-analysis maxcompute

# 调整日志级别（DEBUG / INFO / WARNING / ERROR，默认 INFO）
uv run data-platform-analysis --log-level DEBUG export
```

等价的模块方式：

```bash
uv run python -m data_platform_analysis export
```

## 代码质量

```bash
# Lint（配置见 pyproject.toml [tool.ruff]）
uv run ruff check .

# 自动修复可修复问题
uv run ruff check --fix .

# 格式化
uv run ruff format .

# 类型检查（只检查 src/）
uv run mypy

# 运行测试（testpaths = tests）
uv run pytest

# 只跑某个测试文件
uv run pytest tests/test_cli_smoke.py -q
```

## 退出码约定

CLI 在存在 Workspace / 节点级采集失败时以退出码 `1` 结束；用户中断为 `130`；配置或未知命令错误亦为非零。
