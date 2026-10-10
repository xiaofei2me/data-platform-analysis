# Source 数据安全规则

`source/` 是本仓库中最脆弱、最昂贵的资产。它是一次性采集回来的真实 DataWorks / MaxCompute Snapshot，无法通过代码或测试重新生成，只能重新调用采集接口（需要凭据、配额与人工确认）才可能恢复。

本文件定义 Agent 在开发、测试、重构、Analysis、文档与 CLI 工作中必须遵守的数据边界。

## 1. 数据边界

```text
source/     = 不可变的原始 Snapshot 输入
src/        = 程序代码
tests/      = 测试代码
analysis/   = Analysis 生成结果
```

## 2. source/ 的定位

`source/` 是：

```text
Immutable Snapshot Input
```

它**不是**：

- 临时目录
- 测试输出目录
- Analysis 输出目录
- 构建目录
- cache
- 可以随便清理的数据目录
- 测试沙盒

曾经发生过的真实事故：Analysis 测试与重构过程中 `source/` 被意外删除，导致整个 Snapshot 需要重新采集。本规则存在的唯一目的，就是让这个事故不再重演。

## 3. source/ 必须只读

任何 Agent、开发任务、重构任务、测试任务、Analysis 任务都**不得**：

- 删除 `source/`
- 删除 `source/` 下文件
- 修改 `source/` 文件内容
- 覆盖 `source/` 文件
- 重命名文件
- 移动文件
- 清理文件
- 使用 `source/` 作为临时目录
- 使用 `source/` 作为测试输出目录

特别禁止下列命令及任何等价操作：

```bash
rm -rf source
rm -rf source/*
find source -delete
```

也禁止 Python 层面的等价操作：

```python
shutil.rmtree("source")
shutil.rmtree(Path("source"))
Path("source/...").unlink()
path.write_text(...)  # 目标落在真实 source/ 时
path.write_bytes(...)  # 目标落在真实 source/ 时
```

**读取 `source/` 永远是允许的。** 只有修改、删除、覆盖、移动才是禁止的。

## 4. Analysis 数据流

```text
source/
   │
   │ read-only
   ▼
inventory ──► scope
   │
   ▼
evidence
   │
   ▼
understanding
   │
   ▼
review
   │
   ▼
analysis/
```

其中：

```text
source/    只读输入
analysis/  生成输出
```

Analysis 阶段的所有产物一律写入 `analysis/`，**不允许反向写入 `source/`**。

代码层面的对应关系：

| 模块 | 对 `source/` 的访问 | 对外写入 |
| --- | --- | --- |
| `analysis/snapshot.py`（`SnapshotReader`） | 只读 | 无 |
| `analysis/pipeline.py` | 只读 | `analysis/` |
| `analysis/inventory`、`analysis/scope`、`evidence`、`understanding`、`review` | 只读（多数阶段甚至不读 `source/`） | `analysis/` |

`analysis/` 整体可用 `analyze` 重建（gitignore），但其中 5 份 `*-review-checklist.md`
的 `human_status` / `human_name` / `note` 三列是**唯一的人工回填数据**（全仓库只有人能写），
清场时由 `pipeline.PRESERVED_CHECKLIST_FILES` 快照保留——重跑前仍应备份，不要依赖实现细节。

## 5. 测试规则

**这是本文件最重要的部分。**

测试绝对不能直接修改真实 `source/`。

如果测试需要创建 Snapshot、修改 Snapshot、删除 Snapshot 或模拟 Snapshot 变化，必须使用：

- `pytest` 的 `tmp_path`
- `tests/fixtures/`
- 或其他独立临时目录

例如：

```python
def test_something(tmp_path):
    source_dir = tmp_path / "source"
```

而不是：

```python
source_dir = Path("source")
```

如果测试存在 `shutil.rmtree(...)`、`Path(...).unlink()`、`Path(...).write_text(...)`，并且目标**可能**落到真实 `source/`，必须修改为隔离实现。

### 5.1 需要修改输入时的标准做法

测试可以**读取**真实 `source/`，但**不能修改**真实 `source/`。如果必须修改输入数据：

1. 先把需要的子集复制到 `tmp_path`
2. 测试只修改副本

```text
source/
   ↓ read only
tmp_path/source/
   ↓ writable
test
```

### 5.2 本仓库当前的隔离机制

`tests/conftest.py` 中的 `cli_env` fixture 提供隔离：

```python
monkeypatch.chdir(tmp_path)
...
"SOURCE_DIR": str(tmp_path / "source"),
"ANALYSIS_DIR": str(tmp_path / "analysis"),
```

因此测试中出现的 `Path("source")` 实际解析为 `tmp_path/source`，不是仓库根目录的 `source/`。

**注意这个保护是隐式的**：它完全依赖 `cli_env` 生效时的 `chdir`。任何调用 `write_snapshot(Path("source"))`、`shutil.rmtree(Path("source"))` 等写操作的测试函数，都**必须**声明 `cli_env` fixture；模块级 helper（如 `_broken_snapshot()`、`prepare_snapshot()`）自身不带 fixture，只能由带 `cli_env` 的测试调用。

不要在未声明 `cli_env` 的上下文中调用任何写 `source/` 的 helper。`tests/helpers.py` 中的 `assert_sandbox()` 是这道防线的最后一道闸门。

## 6. Collection / Export 是唯一例外

DataWorks / MaxCompute 的采集流程可以生成或覆盖 `source/`。

**只有用户明确要求「重新采集」「重新生成 Snapshot」「重新导出」时**，才允许执行会修改 `source/` 的 collection/export 流程。

以下任务**绝对不能自动修改 `source/`**：

```text
Analysis
测试
重构
代码修改
Bug 修复
Lint
pytest
文档修改
CLI 修改
Pipeline 修改
```

已知的、由用户主动触发的写入入口（均需显式 CLI 子命令，不属于自动行为）：

- `data-platform-analysis export` —— 采集并写入 `source/`
- `data-platform-analysis summary` —— 重写 `source/Summary.md`

如果某个任务确实需要修改 `source/`，**必须先停止并向用户请求明确确认**。

## 7. Git 安全

`source/` 在 `.gitignore` 中被忽略（`/source/*`，仅保留 `/source/.gitkeep`）。这意味着：

- `git status` **看不到** `source/` 的任何变化
- Git **不能**用来恢复误删的 `source/`

因此：

**不要**随意执行：

```bash
git clean -fd
git clean -fdx
```

`git clean` 会直接删除未被 Git 跟踪的文件，等于清空 `source/`。

**也不要在没有确认的情况下**执行：

```bash
git reset --hard
```

它可能导致 Snapshot 数据丢失，且无法通过 Git 找回。

### 7.1 基线校验

因为 Git 看不到 `source/`，只能用文件清单与校验和判断它是否被动过：

```bash
find source -type f | sort > /tmp/source-files.txt
find source -type f -print0 | sort -z | xargs -0 shasum > /tmp/source-checksums.txt
```

在改动涉及 `source/` 的代码后，用它确认没有意外修改：

```bash
find source -type f | sort | diff - /tmp/source-files.txt
find source -type f -print0 | sort -z | xargs -0 shasum | diff - /tmp/source-checksums.txt
```

## 8. 违反规则时的行为

如果发现自己（或其他任务）即将对 `source/` 执行写、删、改、移动操作：

1. **立即停止**
2. 说明打算做什么
3. 向用户请求明确确认

得到确认之前，不得执行。
