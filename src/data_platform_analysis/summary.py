"""生成 source/Summary.md 快照说明文档。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    """返回当前 UTC 时间。"""
    return datetime.now(UTC).isoformat()


class SnapshotSummaryGenerator:
    """
    Snapshot Summary 生成器。

    Summary.md 的定位：

    1. 向人说明 source/ 目录是什么。
    2. 说明各个目录和文件的用途。
    3. 说明 DataWorks 和 MaxCompute Snapshot 的组织方式。
    4. 说明 FileId、NodeId、Table 等核心概念。
    5. 说明 Snapshot 的数据来源和使用方式。
    6. 提供当前 Snapshot 的基本统计信息。

    注意：

    - Summary.md 不是 Source of Truth。
    - 不直接调用 DataWorks / MaxCompute API。
    - 只读取已经落盘的 Snapshot。
    - Index 文件用于生成导航和统计信息。
    """

    def __init__(self, source_dir: Path) -> None:
        """初始化 Summary 生成器。"""
        self.source_dir = source_dir

    def generate(self) -> Path:
        """
        生成 source/Summary.md。

        Returns:
            生成后的 Summary.md 路径。
        """
        self.source_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        summary_path = self.source_dir / "Summary.md"

        summary = self._build_summary()

        summary_path.write_text(
            summary,
            encoding="utf-8",
        )

        return summary_path

    def _build_summary(self) -> str:
        """构建完整的 Summary Markdown 内容。"""
        dataworks = self._collect_dataworks_summary()
        maxcompute = self._collect_maxcompute_summary()

        lines: list[str] = []

        self._append_overview(
            lines,
            dataworks=dataworks,
            maxcompute=maxcompute,
        )

        self._append_directory_structure(lines)

        self._append_dataworks_section(
            lines,
            dataworks=dataworks,
        )

        self._append_maxcompute_section(
            lines,
            maxcompute=maxcompute,
        )

        self._append_relationship_section(lines)

        self._append_source_of_truth_section(lines)

        self._append_snapshot_rules_section(lines)

        self._append_analysis_section(lines)

        self._append_current_snapshot_section(
            lines,
            dataworks=dataworks,
            maxcompute=maxcompute,
        )

        return "\n".join(lines)

    # ==========================================================
    # Overview
    # ==========================================================

    def _append_overview(
        self,
        lines: list[str],
        *,
        dataworks: dict[str, Any],
        maxcompute: dict[str, Any],
    ) -> None:
        """添加 Snapshot 总体说明。"""
        lines.extend(
            [
                "# Source 快照目录说明",
                "",
                "## 1. 概述",
                "",
                "`source/` 目录用于保存从 DataWorks 和 MaxCompute "
                "采集得到的本地 Snapshot 数据。",
                "",
                "该目录是后续数据平台分析工作的输入数据源。",
                "",
                "当前阶段主要负责：",
                "",
                "- 采集 DataWorks Workspace 和 File 信息",
                "- 保存 DataWorks File 原始 API 数据",
                "- 保存 DataWorks File Content",
                "- 采集 MaxCompute Table 元数据",
                "- 按 Workspace 隔离保存 Snapshot",
                "- 建立用于快速定位的 Index",
                "",
                "当前阶段暂不进行数据仓库建模和业务语义推断。",
                "",
                "> **重要说明**",
                ">",
                "> `source/` 中保存的原始 Snapshot 是后续分析的数据基础。",
                "> `*-index.json` 主要用于导航和快速定位。",
                "> `Summary.md` 仅用于人工理解 Snapshot 结构，不参与事实判断。",
                "",
                "### 当前 Snapshot 概览",
                "",
                f"- DataWorks Workspace：{dataworks['workspace_count']} 个",
                f"- MaxCompute Workspace：{maxcompute['workspace_count']} 个",
                "",
            ]
        )

    # ==========================================================
    # Directory Structure
    # ==========================================================

    def _append_directory_structure(
        self,
        lines: list[str],
    ) -> None:
        """添加 source 目录结构说明。"""
        lines.extend(
            [
                "## 2. 目录结构",
                "",
                "当前 `source/` 的核心目录结构如下：",
                "",
                "```text",
                "source/",
                "├── Summary.md                         # 当前目录说明",
                "│",
                "├── manifest.json                      # 完整导出时生成的采集清单",
                "│",
                "├── dataworks/                         # DataWorks Snapshot",
                "│   ├── workspaces-index.json          # Workspace 索引",
                "│   │",
                "│   └── workspaces/",
                "│       └── <workspace_id>/",
                "│           ├── files-list.json        # File 清单",
                "│           ├── files-index.json       # File Snapshot 索引",
                "│           │",
                "│           ├── files/                 # GetFile 原始 JSON",
                "│           │   └── <file_id>__<file_name>.json",
                "│           │",
                "│           └── content/               # File 实际内容",
                "│               └── <file_id>__<file_name>.<ext>",
                "│",
                "└── maxcompute/                        # MaxCompute Snapshot",
                "    └── workspaces/",
                "        └── <workspace_id>/",
                "            ├── tables-index.json      # Table 索引",
                "            └── tables/",
                "                └── <table_name>.json",
                "```",
                "",
                "### 目录职责",
                "",
                "| 路径 | 作用 |",
                "|---|---|",
                "| `source/` | Snapshot 根目录 |",
                "| `Summary.md` | 当前 Snapshot 目录说明 |",
                "| `manifest.json` | 完整导出时生成的采集来源清单 |",
                "| `dataworks/` | DataWorks Snapshot |",
                "| `workspaces-index.json` | DataWorks Workspace 导航索引 |",
                "| `workspaces/<workspace_id>/` | 单个 Workspace 的 Snapshot |",
                "| `files-list.json` | DataWorks File Inventory |",
                "| `files-index.json` | 本地 File 导航索引 |",
                "| `files/` | GetFile 原始 API JSON |",
                "| `content/` | File 实际内容 |",
                "| `maxcompute/` | MaxCompute Snapshot |",
                "| `tables-index.json` | MaxCompute Table 导航索引 |",
                "| `tables/` | MaxCompute Table 元数据 |",
                "",
                "### `manifest.json` 说明",
                "",
                "`manifest.json` 不是每次导出都一定存在。",
                "",
                "当前实现中，只有完整 Workspace 导出时才生成该文件。",
                "指定 `--workspace` 时不会重新生成 `manifest.json`。",
                "",
                "它主要记录：",
                "",
                "- 工具名称和版本",
                "- DataWorks API 版本",
                "- DataWorks Region",
                "- DataWorks Workspace",
                "- MaxCompute Endpoint",
                "- MaxCompute Schema",
                "- MaxCompute Project",
                "",
                "它不保存具体 File 或 Table 的详细数据。",
                "",
            ]
        )

    # ==========================================================
    # DataWorks
    # ==========================================================

    def _append_dataworks_section(
        self,
        lines: list[str],
        *,
        dataworks: dict[str, Any],
    ) -> None:
        """添加 DataWorks Snapshot 说明。"""
        lines.extend(
            [
                "## 3. DataWorks 数据",
                "",
                "DataWorks 数据按照 Workspace 进行隔离保存。",
                "",
                "```text",
                "dataworks/",
                "├── workspaces-index.json",
                "└── workspaces/",
                "    └── <workspace_id>/",
                "        ├── files-list.json",
                "        ├── files-index.json",
                "        ├── files/",
                "        └── content/",
                "```",
                "",
                "### 3.1 Workspace",
                "",
                "Workspace 是 DataWorks Snapshot 的顶层边界。",
                "",
                "每个 Workspace 使用独立目录：",
                "",
                "```text",
                "dataworks/workspaces/<workspace_id>/",
                "```",
                "",
                "例如：",
                "",
                "```text",
                "dataworks/workspaces/466337/",
                "dataworks/workspaces/466338/",
                "```",
                "",
                "其中目录名称是 DataWorks Workspace ID。",
                "",
                "### 3.2 `workspaces-index.json`",
                "",
                "文件：",
                "",
                "```text",
                "dataworks/workspaces-index.json",
                "```",
                "",
                "用于记录已经采集过的 DataWorks Workspace。",
                "",
                "主要作用是：",
                "",
                "> 根据 Workspace ID 快速定位对应的 Snapshot 目录。",
                "",
                "该文件属于导航索引，不是原始 API 数据。",
                "",
                "### 3.3 `files-list.json`",
                "",
                "文件：",
                "",
                "```text",
                "dataworks/workspaces/<workspace_id>/files-list.json",
                "```",
                "",
                "该文件保存 DataWorks `ListFiles` 最终 File Inventory。",
                "",
                "它主要回答：",
                "",
                "> **当前 Workspace 中有哪些 File？**",
                "",
                "主要包含：",
                "",
                "- FileId",
                "- FileName",
                "- NodeId",
                "- FileType",
                "- UseType",
                "- DataWorks 返回的其他 File 信息",
                "",
                "当前 Snapshot 中，`FileId` 是 DataWorks File 的主要身份标识。",
                "",
                "`NodeId` 是与 File 关联的调度 / 任务节点 ID。",
                "",
                "> **不是所有 File 都一定存在 NodeId。**",
                ">",
                "> 没有 NodeId 的 File 仍然属于有效 Snapshot 数据。",
                "",
                "### 3.4 `files-index.json`",
                "",
                "文件：",
                "",
                "```text",
                "dataworks/workspaces/<workspace_id>/files-index.json",
                "```",
                "",
                "该文件是本地生成的 File 导航索引。",
                "",
                "它负责建立 File 元数据和本地 Snapshot 文件之间的关系：",
                "",
                "```text",
                "FileId",
                "  │",
                "  ├── FileName",
                "  ├── NodeId",
                "  ├── FileType",
                "  ├── TaskType",
                "  ├── Category",
                "  │",
                "  ├── files/<file>.json",
                "  │",
                "  └── content/<file>.<ext>",
                "```",
                "",
                "该文件属于派生索引。",
                "",
                "如果 Index 与原始 Snapshot 数据存在冲突，应以原始 Snapshot 为准。",
                "",
                "### 3.5 `files/`",
                "",
                "目录：",
                "",
                "```text",
                "dataworks/workspaces/<workspace_id>/files/",
                "```",
                "",
                "保存 DataWorks `GetFile` 返回的原始 File JSON。",
                "",
                "文件命名格式：",
                "",
                "```text",
                "<file_id>__<file_name>.json",
                "```",
                "",
                "例如：",
                "",
                "```text",
                "123456__dwd_sales_order.json",
                "```",
                "",
                "文件名前面的 `123456` 是 FileId。",
                "",
                "这些 JSON 是后续 DataWorks 元数据分析的重要输入。",
                "",
                "### 3.6 `content/`",
                "",
                "目录：",
                "",
                "```text",
                "dataworks/workspaces/<workspace_id>/content/",
                "```",
                "",
                "保存从 DataWorks `GetFile` 结果中提取出来的实际 File Content。",
                "",
                "例如：",
                "",
                "```text",
                "content/",
                "├── 123456__dwd_sales_order.sql",
                "├── 123457__dwd_customer.sql",
                "├── 123458__etl_customer.py",
                "└── ...",
                "```",
                "",
                "Content 主要用于后续分析：",
                "",
                "- SQL",
                "- 表引用",
                "- SELECT / INSERT",
                "- JOIN",
                "- WHERE",
                "- GROUP BY",
                "- ETL 处理逻辑",
                "- 后续血缘分析",
                "",
                "可以简单理解为：",
                "",
                "```text",
                "files/*.json",
                "    ↓",
                "这个 File 是什么",
                "",
                "content/*",
                "    ↓",
                "这个 File 实际做了什么",
                "```",
                "",
                "### 3.7 FileId 与 NodeId",
                "",
                "```text",
                "DataWorks File",
                "      │",
                "      ├── FileId  → File 身份标识",
                "      │",
                "      └── NodeId  → 调度 / 任务节点",
                "```",
                "",
                "两者不是同一个概念：",
                "",
                "```text",
                "FileId != NodeId",
                "```",
                "",
                "因此：",
                "",
                "- File 可以存在 FileId，但没有 NodeId",
                "- NodeId 主要用于后续任务和调度分析",
                "- 没有 NodeId 的 File 不能因此被认为是无效数据",
                "",
                "### 3.8 当前 DataWorks Snapshot",
                "",
                "| Workspace ID | Workspace 名称 | 状态 | File 数量 | 失败数量 |",
                "|---:|---|---|---:|---:|",
            ]
        )

        for workspace in dataworks["workspaces"]:
            lines.append(
                "| "
                f"{workspace.get('id', '')} | "
                f"{workspace.get('name', '')} | "
                f"{workspace.get('status', '')} | "
                f"{workspace.get('file_count', 0)} | "
                f"{workspace.get('failed_file_count', 0)} |"
            )

        lines.append("")

    # ==========================================================
    # MaxCompute
    # ==========================================================

    def _append_maxcompute_section(
        self,
        lines: list[str],
        *,
        maxcompute: dict[str, Any],
    ) -> None:
        """添加 MaxCompute Snapshot 说明。"""
        lines.extend(
            [
                "## 4. MaxCompute 数据",
                "",
                "MaxCompute 数据按照 Workspace 进行隔离保存。",
                "",
                "```text",
                "maxcompute/",
                "└── workspaces/",
                "    └── <workspace_id>/",
                "        ├── tables-index.json",
                "        └── tables/",
                "            └── <table_name>.json",
                "```",
                "",
                "### 4.1 Workspace 与 Project",
                "",
                "当前项目约定：",
                "",
                "```text",
                "DataWorks Workspace.name",
                "          ↓",
                "MaxCompute Project.name",
                "```",
                "",
                "也就是说，每个 Workspace 对应一个 MaxCompute Project。",
                "",
                "Snapshot 仍然使用 Workspace ID 进行物理隔离：",
                "",
                "```text",
                "maxcompute/workspaces/<workspace_id>/",
                "```",
                "",
                "### 4.2 `tables-index.json`",
                "",
                "文件：",
                "",
                "```text",
                "maxcompute/workspaces/<workspace_id>/tables-index.json",
                "```",
                "",
                "用于记录当前 Workspace 对应 MaxCompute Project 中已经成功采集的 Table。",
                "",
                "主要包含：",
                "",
                "- Workspace",
                "- Project",
                "- Schema",
                "- Table 数量",
                "- Table 索引",
                "- 失败 Table",
                "",
                "该文件属于导航索引。",
                "",
                "### 4.3 `tables/`",
                "",
                "目录：",
                "",
                "```text",
                "maxcompute/workspaces/<workspace_id>/tables/",
                "```",
                "",
                "每张 Table 对应一个 JSON 文件：",
                "",
                "```text",
                "<table_name>.json",
                "```",
                "",
                "例如：",
                "",
                "```text",
                "tables/",
                "├── dwd_sales_order.json",
                "├── dwd_customer.json",
                "├── dim_product.json",
                "└── ads_sales_summary.json",
                "```",
                "",
                "每个 Table JSON 当前主要包含：",
                "",
                "- Project",
                "- Schema",
                "- 表名",
                "- 表注释",
                "- 创建时间",
                "- 修改时间",
                "- 数据大小",
                "- 生命周期",
                "- 是否 Virtual View",
                "- 普通字段",
                "- 分区字段",
                "- 可选的实际分区实例",
                "",
                "这些数据是后续数据仓库模型分析的重要输入。",
                "",
                "### 4.4 当前 MaxCompute Snapshot",
                "",
                "| Workspace ID | Workspace 名称 | Project | Schema | Table 数量 | 失败数量 |",
                "|---:|---|---|---|---:|---:|",
            ]
        )

        for workspace in maxcompute["workspaces"]:
            lines.append(
                "| "
                f"{workspace.get('workspace_id', '')} | "
                f"{workspace.get('workspace_name', '')} | "
                f"{workspace.get('project', '')} | "
                f"{workspace.get('schema', '')} | "
                f"{workspace.get('count', 0)} | "
                f"{workspace.get('failed_count', 0)} |"
            )

        lines.append("")

    # ==========================================================
    # Relationship
    # ==========================================================

    def _append_relationship_section(
        self,
        lines: list[str],
    ) -> None:
        """添加 DataWorks 与 MaxCompute 的关系说明。"""
        lines.extend(
            [
                "## 5. DataWorks 与 MaxCompute 的关系",
                "",
                "当前 Snapshot 不会把 DataWorks 和 MaxCompute 强行合并成一套数据。",
                "",
                "两个系统分别保存自己的原始元数据。",
                "",
                "```text",
                "                    Workspace",
                "                        │",
                "             ┌──────────┴──────────┐",
                "             │                     │",
                "             ▼                     ▼",
                "         DataWorks             MaxCompute",
                "             │                     │",
                "           File                  Table",
                "             │                     │",
                "          Content               Column",
                "                                   │",
                "                                Partition",
                "```",
                "",
                "可以简单理解为：",
                "",
                "| 系统 | 主要回答的问题 |",
                "|---|---|",
                "| DataWorks | 数据是如何被开发、处理和调度的？ |",
                "| MaxCompute | 数据最终以什么表结构存在？ |",
                "",
                "后续 Analysis 阶段再将两部分信息结合起来。",
                "",
            ]
        )

    # ==========================================================
    # Source of Truth
    # ==========================================================

    def _append_source_of_truth_section(
        self,
        lines: list[str],
    ) -> None:
        """添加 Source of Truth 说明。"""
        lines.extend(
            [
                "## 6. Source of Truth",
                "",
                "Snapshot 中的数据使用优先级如下：",
                "",
                "```text",
                "原始 API Snapshot",
                "       │",
                "       ├── DataWorks files/*.json",
                "       ├── DataWorks content/*",
                "       └── MaxCompute tables/*.json",
                "              │",
                "              ▼",
                "          原始数据",
                "              │",
                "              ▼",
                "          Index 文件",
                "              │",
                "              ▼",
                "          Summary.md",
                "```",
                "",
                "### 第一层：原始 Snapshot",
                "",
                "包括：",
                "",
                "```text",
                "dataworks/.../files/*.json",
                "dataworks/.../content/*",
                "maxcompute/.../tables/*.json",
                "```",
                "",
                "这些文件是后续分析真正需要读取的数据。",
                "",
                "### 第二层：Index",
                "",
                "包括：",
                "",
                "```text",
                "workspaces-index.json",
                "files-list.json",
                "files-index.json",
                "tables-index.json",
                "```",
                "",
                "Index 用于快速定位数据、建立对象关系和辅助统计。",
                "",
                "### 第三层：Summary.md",
                "",
                "`Summary.md` 只用于说明 Snapshot 的结构和使用方法。",
                "",
                "它不是业务事实，也不是后续分析的数据来源。",
                "",
            ]
        )

    # ==========================================================
    # Snapshot Rules
    # ==========================================================

    def _append_snapshot_rules_section(
        self,
        lines: list[str],
    ) -> None:
        """添加 Snapshot 更新和清理规则。"""
        lines.extend(
            [
                "## 7. Snapshot 更新规则",
                "",
                "### 7.1 完整采集",
                "",
                "完整采集时，ListFiles / ListTables 返回的完整集合可以作为当前远端对象集合的依据。",
                "",
                "在成功获取对象详情的前提下，可以执行 Snapshot Cleanup。",
                "",
                "对于已经不存在的对象，可以删除对应的旧 Snapshot。",
                "",
                "### 7.2 限制模式",
                "",
                "例如：",
                "",
                "```bash",
                "uv run data-platform-analysis export --limit 10",
                "```",
                "",
                "限制模式只处理部分 File 和 Table。",
                "",
                "因此：",
                "",
                "> **限制模式下不能根据本次结果判断远端对象已经删除。**",
                "",
                "所以限制模式不会执行完整 Snapshot Cleanup。",
                "",
                "### 7.3 单个对象获取失败",
                "",
                "如果 DataWorks `GetFile` 或 MaxCompute `GetTable` 失败：",
                "",
                "- 不覆盖原有成功 Snapshot",
                "- 尽可能保留之前的 Snapshot",
                "- 在 Index 中记录失败信息",
                "",
                "这样可以避免临时 API 错误导致已有 Snapshot 被错误删除。",
                "",
            ]
        )

    # ==========================================================
    # Analysis
    # ==========================================================

    def _append_analysis_section(
        self,
        lines: list[str],
    ) -> None:
        """添加后续 Analysis 阶段说明。"""
        lines.extend(
            [
                "## 8. 当前阶段边界",
                "",
                "第一阶段的核心目标是：",
                "",
                "> **建立可靠、可重复、可追溯的 DataWorks + MaxCompute Snapshot。**",
                "",
                "当前阶段暂不进行以下分析：",
                "",
                "- ODS / DWD / ADS 自动判断",
                "- 业务过程识别",
                "- 事实表 / 维度表识别",
                "- DWS 建模",
                "- 表级血缘",
                "- 字段级血缘",
                "- SQL 语义分析",
                "- Semantic Layer",
                "- LLM / Agent 分析",
                "",
                "这些内容属于后续 Analysis 阶段。",
                "",
                "### 后续分析路径",
                "",
                "```text",
                "DataWorks",
                "├── File Metadata",
                "├── Node Metadata",
                "└── SQL / Code Content",
                "",
                "             +",
                "",
                "MaxCompute",
                "├── Table Metadata",
                "├── Column Metadata",
                "└── Partition Metadata",
                "",
                "             ↓",
                "",
                "        数据仓库分析",
                "",
                "             ↓",
                "",
                "        ODS / DWD / ADS",
                "",
                "             ↓",
                "",
                "        业务过程识别",
                "",
                "             ↓",
                "",
                "        事实 / 维度识别",
                "",
                "             ↓",
                "",
                "          DWS 建模",
                "",
                "             ↓",
                "",
                "       Semantic Layer",
                "```",
                "",
            ]
        )

    # ==========================================================
    # Current Snapshot
    # ==========================================================

    def _append_current_snapshot_section(
        self,
        lines: list[str],
        *,
        dataworks: dict[str, Any],
        maxcompute: dict[str, Any],
    ) -> None:
        """添加当前 Snapshot 的汇总信息。"""
        dataworks_file_count = sum(
            workspace.get("file_count", 0)
            for workspace in dataworks["workspaces"]
        )

        dataworks_failed_count = sum(
            workspace.get("failed_file_count", 0)
            for workspace in dataworks["workspaces"]
        )

        maxcompute_table_count = sum(
            workspace.get("count", 0)
            for workspace in maxcompute["workspaces"]
        )

        maxcompute_failed_count = sum(
            workspace.get("failed_count", 0)
            for workspace in maxcompute["workspaces"]
        )

        lines.extend(
            [
                "## 9. 当前 Snapshot 信息",
                "",
                f"- Summary 生成时间：`{utc_now()}`",
                f"- DataWorks Workspace：`{dataworks['workspace_count']}` 个",
                f"- DataWorks File：`{dataworks_file_count}` 个",
                f"- DataWorks File 获取失败：`{dataworks_failed_count}` 个",
                f"- MaxCompute Workspace：`{maxcompute['workspace_count']}` 个",
                f"- MaxCompute Table：`{maxcompute_table_count}` 张",
                f"- MaxCompute Table 获取失败：`{maxcompute_failed_count}` 张",
                "",
                "详细数据请查看对应 Workspace 下的 Index 和 Snapshot 文件。",
                "",
                "## 10. 总结",
                "",
                "`source/` 的核心职责是：",
                "",
                "> **保存一份可重复、可追溯、结构清晰的 DataWorks + MaxCompute 元数据快照。**",
                "",
                "可以简单理解为：",
                "",
                "```text",
                "DataWorks",
                "    → File / Node / Content",
                "",
                "MaxCompute",
                "    → Table / Column / Partition",
                "",
                "Index",
                "    → 快速定位",
                "",
                "Summary.md",
                "    → 解释整个 Snapshot",
                "",
                "manifest.json",
                "    → 完整导出时记录采集来源和运行信息",
                "```",
                "",
                "后续所有数据仓库建模和语义分析，都应该建立在这份 Snapshot 之上。",
                "",
            ]
        )

    # ==========================================================
    # DataWorks Snapshot 读取
    # ==========================================================

    def _collect_dataworks_summary(self) -> dict[str, Any]:
        """
        从 DataWorks Snapshot 中读取汇总信息。

        注意：
        不读取 DataWorks API，只读取已经落盘的
        workspaces-index.json。
        """
        path = (
            self.source_dir
            / "dataworks"
            / "workspaces-index.json"
        )

        data = self._read_json(path)

        workspaces = data.get(
            "workspaces",
            [],
        )

        if not isinstance(workspaces, list):
            workspaces = []

        valid_workspaces = [
            workspace
            for workspace in workspaces
            if isinstance(workspace, dict)
        ]

        return {
            "workspace_count": len(valid_workspaces),
            "workspaces": valid_workspaces,
        }

    # ==========================================================
    # MaxCompute Snapshot 读取
    # ==========================================================

    def _collect_maxcompute_summary(self) -> dict[str, Any]:
        """
        从 MaxCompute Snapshot 中读取汇总信息。

        MaxCompute 当前没有单独的 Workspace Index，
        因此直接遍历：

            maxcompute/workspaces/<workspace_id>/tables-index.json
        """
        root = (
            self.source_dir
            / "maxcompute"
            / "workspaces"
        )

        if not root.exists():
            return {
                "workspace_count": 0,
                "workspaces": [],
            }

        workspaces: list[dict[str, Any]] = []

        for workspace_dir in sorted(root.iterdir()):
            if not workspace_dir.is_dir():
                continue

            index_path = (
                workspace_dir
                / "tables-index.json"
            )

            data = self._read_json(index_path)

            if not data:
                continue

            workspace = data.get(
                "workspace",
                {},
            )

            if not isinstance(workspace, dict):
                workspace = {}

            failed_tables = data.get(
                "failed_tables",
                [],
            )

            if not isinstance(failed_tables, list):
                failed_tables = []

            workspaces.append(
                {
                    "workspace_id": workspace.get(
                        "id",
                        workspace_dir.name,
                    ),
                    "workspace_name": workspace.get(
                        "name",
                        "",
                    ),
                    "project": data.get(
                        "project",
                        "",
                    ),
                    "schema": data.get(
                        "schema",
                        "",
                    ),
                    "count": self._safe_int(
                        data.get(
                            "count",
                            0,
                        )
                    ),
                    "failed_count": len(
                        failed_tables
                    ),
                }
            )

        return {
            "workspace_count": len(workspaces),
            "workspaces": workspaces,
        }

    # ==========================================================
    # JSON 工具方法
    # ==========================================================

    @staticmethod
    def _read_json(
        path: Path,
    ) -> dict[str, Any]:
        """
        安全读取 JSON 文件。

        如果文件不存在、JSON 损坏或者内容不是对象，
        则返回空字典。

        Summary 不能因为某一个 Snapshot 文件异常
        而导致整个 Export 失败。
        """
        if not path.exists():
            return {}

        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8",
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return {}

        if not isinstance(data, dict):
            return {}

        return data

    @staticmethod
    def _safe_int(
        value: Any,
    ) -> int:
        """安全转换整数。"""
        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return 0