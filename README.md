# data-platform-analysis

基于 Alibaba Cloud DataWorks + MaxCompute 的数据平台现状分析项目。

## 1. 项目目标

本项目用于对现有数据仓库进行反向分析，为后续 DWS 和 Semantic Layer 设计提供数据基础。

当前整体目标：

DataWorks + MaxCompute
        ↓
    数据资产采集
        ↓
   本地 Snapshot
        ↓
    数据仓库现状分析
        ↓
       DWS 设计
        ↓
  Semantic Layer 设计

当前阶段只负责：

- DataWorks 数据采集
- MaxCompute 数据采集
- 原始数据保存
- SQL 保存
- 基础任务关系保存

暂时不负责：

- QuickBI
- LLM 分析
- AI Agent
- DWS 自动生成
- Semantic Layer 实现
- 数据迁移

---

## 2. 当前采集范围

### DataWorks

采集：

- DataWorks Project
- 数据开发节点
- 节点 ID
- 节点名称
- 节点类型
- 节点详情
- SQL / Script
- 节点原始 JSON
- 基础任务依赖信息

### MaxCompute

采集：

- Project
- Schema
- Table
- Table Comment
- Column
- Column Type
- Column Comment
- Partition Column
- Table Size
- Lifecycle
- Create Time
- Last Modified Time

默认不采集实际分区实例。

---

## 3. 项目结构

```text
data-platform-analysis/
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
│
├── src/
│   └── data_platform_analysis/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── logging_utils.py
│       ├── io_utils.py
│       ├── dataworks.py
│       ├── maxcompute.py
│       └── export.py
│
├── source/
│   └── .gitkeep
│
├── analysis/
│   └── .gitkeep
│
├── output/
│   └── .gitkeep
│
└── tests/
    └── .gitkeep
```

