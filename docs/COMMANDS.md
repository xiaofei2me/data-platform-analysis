# 命令参考

```bash
uv run data-platform-analysis [--log-level LEVEL] <command> [options]
```

全局参数：

| 参数 | 说明 |
| --- | --- |
| `--log-level` | `DEBUG` / `INFO` / `WARNING` / `ERROR`，默认 `INFO`；须写在子命令之前 |

退出码：

| 退出码 | 含义 |
| --- | --- |
| 0 | 全部成功 |
| 1 | 存在 Workspace / File / Table 级失败，或命令执行失败（含配置错误、未配置的 `--workspace`） |
| 130 | 用户中断（Ctrl-C） |

## 子命令总览

| 命令 | 作用 |
| --- | --- |
| `dataworks` | 只采集 DataWorks（File → Raw GetFile → Content → files-index） |
| `maxcompute` | 只采集 MaxCompute（Table → Metadata → tables-index） |
| `export` | `dataworks` + `maxcompute` 组合；全量时额外写入 `manifest.json` |
| `summary` | 根据已有 Snapshot 重新生成 `Summary.md` |
| `config` | 打印当前生效的非敏感配置（不含密钥），不发起任何采集 |

分析命令（只读 Snapshot / 上一阶段产物，不发起任何采集）：

| 命令 | 作用 |
| --- | --- |
| `analyze` | 基于已有 Snapshot 生成 `analysis/` Evidence Chain（M2.1–M2.5）；可选 `--workspace <id>` |
| `analyze-layer` | 基于已有 `analysis/inventory` 执行 M2.2 Layer Assessment，不重跑 SQL / Lineage / Profiling |
| `analyze-business` | 基于已有 M2 产物执行 M3 Business Understanding（Domain / Object 候选 + 证据） |
| `analyze-business-quality` | 基于已有 M2 / M3 产物执行 M3.1 质量评估（只评估，不识别） |
| `analyze-business-objects` | 基于已有 M2 / M3 / M3.1 产物执行 M3.2 Object & Relationship 证据结构 |
| `analyze-business-processes` | 基于已有 M2 ~ M3.1 产物执行 M3.3 Process Candidate Analysis |
| `analyze-business-grain` | 基于已有 M2 ~ M3.2 产物执行 M3.4 Grain Candidate Analysis |
| `analyze-business-model` | 基于已有 M2 ~ M3.4 产物执行 M3.5 Fact / Dimension Candidate Analysis（candidate + 证据，不产出 DWD / DWS / Semantic Layer） |
| `analyze-current-state-model` | 基于已有 M2 ~ M3.5 产物执行 M3.6 Current-State Model Review（只评审：当前形态分类 + 18 类 finding + 人工清单），并附带 M3.6 v2 Problem Assessment（finding → problem candidate + 13 类 taxonomy + 证据 / 影响 / 根因 + 人工清单），一次写出 9 个产物，不设计 Target DWD、不改上游产物；方法论与人工裁决流程见 [M36_PROBLEM_ASSESSMENT.md](M36_PROBLEM_ASSESSMENT.md) |

分析命令共性：无参数、无专用配置，只读上游产物并写 `analysis/`；上游缺失或跨文件引用未知即退出码 1（不回退执行前置阶段）。等价入口：`uv run python -m data_platform_analysis.cli <子命令>`。

`dataworks` / `maxcompute` / `export` 都接受：

| 参数 | 说明 |
| --- | --- |
| `--workspace <id>` | 只采集该 Workspace；`id` 必须已在 `WORKSPACES` 中配置，否则直接报错退出（退出码 1）；缺省为全部 Workspace |
| `--limit <n>` | 采集限制模式；`n` 必须是大于 0 的整数，`0`、负数、非整数直接拒绝（退出码 1）；缺省为全量采集 |

## 示例

```bash
# 全部 Workspace 的 DataWorks 采集
uv run data-platform-analysis dataworks

# 指定 Workspace
uv run data-platform-analysis dataworks --workspace 123456

# 指定 Workspace + 限制模式
uv run data-platform-analysis dataworks --workspace 123456 --limit 10

# MaxCompute
uv run data-platform-analysis maxcompute
uv run data-platform-analysis maxcompute --workspace 123456
uv run data-platform-analysis maxcompute --limit 10

# DataWorks + MaxCompute
uv run data-platform-analysis export
uv run data-platform-analysis export --workspace 123456
uv run data-platform-analysis export --limit 10
uv run data-platform-analysis export --workspace 123456 --limit 10

# 查看配置
uv run data-platform-analysis config

# 根据已有 Snapshot 重新生成 Summary
uv run data-platform-analysis summary

# 分析链（按阶段，逐级只读上一阶段产物）
uv run data-platform-analysis analyze
uv run data-platform-analysis analyze-layer
uv run data-platform-analysis analyze-business
uv run data-platform-analysis analyze-business-quality
uv run data-platform-analysis analyze-business-objects
uv run data-platform-analysis analyze-business-processes
uv run data-platform-analysis analyze-business-grain
uv run data-platform-analysis analyze-business-model
uv run data-platform-analysis analyze-current-state-model
```

## `--limit` 语义

`--limit N` 表示**每个 Workspace** 最多处理 N 个对象：

- DataWorks：最多 N 个 File；分页过程中一旦达到 limit 立即停止后续分页，不会为了拿总数继续请求。
- MaxCompute：`ListTables` 正常获取完整表列表，然后只对前 N 张表执行 `GetTable`。
- 多 `UseType` 场景下，limit 是整个 Workspace 的总配额（A/B/C 三类合计 N 个），不是每类各 N 个。

## Cleanup 安全规则

```
limit is None     → 完整集合 → 允许 Cleanup
limit is not None → 部分集合 → 禁止 Cleanup（日志输出 Cleanup=SKIP）
```

- 成功的 `ListFiles` / `ListTables` 返回值是当前对象集合的权威来源，据此删除远端已不存在的本地 Snapshot。
- 单个对象获取失败：不覆盖旧 Snapshot，成功对象正常更新，失败对象记入 index（`failed_files` / `failed_tables`）。
- 整个 List API 失败或响应结构异常：不 Cleanup、不覆盖旧 index，Workspace 标记失败。
- 不提供 `--no-cleanup` 开关。

## 多 Workspace 行为

- 缺省 `--workspace` 时顺序采集全部已配置 Workspace。
- 每个 Workspace 独立落盘到 `source/<dataworks|maxcompute>/workspaces/<workspace_id>/`，互不覆盖。
- 单个 Workspace 失败不会阻断其他 Workspace；只要存在失败，最终退出码为 1。
- `dataworks` 的 `workspaces-index.json` 采用读-改-写 upsert：本次未采集的 Workspace 条目原样保留。
- `manifest.json` 仅由全量 `export`（不带 `--workspace`）写入。
