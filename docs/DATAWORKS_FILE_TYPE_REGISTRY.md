# DataWorks FileType 类型注册表

`src/data_platform_analysis/dataworks_types.py` 中的 `FILE_TYPE_REGISTRY` 把 DataWorks
ListFiles / GetFile 返回的 `FileType` 编号映射为语义信息（名称、任务类型、类别、Content 形态、
导出扩展名）。本文记录注册表的依据、字段约定、UNKNOWN 兜底机制，以及已核实的映射。

## 1. 依据

- **编号与节点类型**：以官方《节点类型说明》为准
  <https://help.aliyun.com/zh/dataworks/user-guide/dataworks-nodes>（表中「节点编码」即
  `FileType`，「TaskType」为官方任务类型代号）。该对应关系已与注册表中 20+ 个既有条目
  （23 / 900 / 10 / 11 / 24 / 221 / 1221 / 225 / 227–230 / 257 / 259 / 260 / 267 /
  239 / 1093 / 1301 / 6 / 1100 / 1330 等）交叉验证一致。
- **Content 形态**：官方文档不描述 GetFile `Content` 的结构，`content_format` 与
  `extension` 一律以当前 Snapshot 中的实际 GetFile 样本为准，写法沿用注册表
  「当前 Workspace 实际验证的任务类型」一节的既有风格。
- **无法确认的编号**：保持未注册（UNKNOWN 兜底），不凭经验写入注册表。

## 2. `FileTypeInfo` 字段约定

| 字段 | 含义 | 约定 |
| --- | --- | --- |
| `file_type` | DataWorks FileType 编码 | 必须与注册表 key 一致，不重复注册 |
| `name` | 项目内部使用的 FileType 名称 | 大写语义名（如 `VIRTUAL`、`BRANCH`），全表唯一 |
| `task_type` | 分析层任务类型 | 复用 `TASK_TYPE_*` 常量 |
| `category` | 数据类别 | 复用 `CATEGORY_TASK` / `CATEGORY_RESOURCE` / `CATEGORY_UNKNOWN` |
| `content_format` | GetFile Content 的语义格式 | 复用 `CONTENT_*` 常量 |
| `extension` | 导出 Content 时的文件扩展名 | 必须是字符串（`export.py` 直接 `extension.lstrip(".")`） |
| `description` | FileType 说明 | 可选，说明依据与实测形态 |

不适用字段的处理方式（沿用既有条目，不为消除 UNKNOWN 而强行赋值）：

- `Content` 实测为空 → `content_format=CONTENT_NONE`，`extension="txt"`
  （参照 1026 TASK_FLOW、239 OSS_OBJECT_CHECK）。
- `Content` 形态没有官方定义也没有本地样本 → `content_format=CONTENT_UNKNOWN`，
  `extension="txt"`（参照 11 ODPS_MR、1091 HOLOGRES_DEVELOPMENT）。
- 只有官方定义与实际样本都支持时，才写具体的 `content_format` / `extension`。

## 3. UNKNOWN 兜底机制

- `get_file_type(...)` / `get_file_type_info(...)` 对未注册编号与 `None` 返回
  `UNKNOWN_FILE_TYPE`，不抛异常、不阻断采集（见模块 docstring 设计原则 7）。
- **不引入通用默认映射**：未核实的编号必须继续落入 UNKNOWN，否则会掩盖真实的类型缺口。
- Inventory 报告 8.1 节把 `content_format = UNKNOWN` 的文件按 `file_type` 分组，
  用 `registered` 区分「已登记类型但内容格式未识别」与「类型映射缺口候选」两类初步判断。

## 4. 已核实映射（2026-10-09 本次新增）

| file_type | 官方节点类型（节点编码 / TaskType） | name | task_type | category | content_format | extension | 依据 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 99 | 虚拟节点 / VIRTUAL | VIRTUAL | VIRTUAL | TASK | NONE | txt | 官方编号 + Snapshot 样本 Content 为空（个别仅注释） |
| 241 | Check 节点 / CHECK_NODE | CHECK | CHECK | TASK | JSON | json | 官方编号 + 样本 Content 为检查配置 JSON |
| 1101 | 分支节点 / CONTROLLER_BRANCH | BRANCH | BRANCH | TASK | JSON | json | 官方编号 + 样本 Content 为分支条件 JSON |
| 1103 | do-while 节点 / CONTROLLER_CYCLE | DO_WHILE | DO_WHILE | TASK | NONE | txt | 官方编号 + 样本 Content 为空（循环参数在 NodeConfiguration） |
| 1106 | for-each 节点 / CONTROLLER_TRAVERSE | FOR_EACH | FOR_EACH | TASK | NONE | txt | 官方编号 + 样本 Content 为空（遍历参数在 NodeConfiguration） |
| 1115 | 参数节点 / PARAM_HUB | PARAM_HUB | PARAM_HUB | TASK | NONE | txt | 官方编号 + 样本 Content 为空 |
| 1102 | 归并节点 / CONTROLLER_JOIN | MERGE | MERGE | TASK | UNKNOWN | txt | 官方编号已确认；当前 Snapshot 无样本，Content 待确认 |
| 1114 | HTTP 触发器节点 / SCHEDULER_TRIGGER | HTTP_TRIGGER | HTTP_TRIGGER | TASK | UNKNOWN | txt | 同上（官方注明其替代跨租户节点 1089） |
| 1331 | 数据对比节点 / DATA_SYNCHRONIZATION_QUALITY_CHECK | DATA_COMPARISON | DATA_COMPARISON | TASK | UNKNOWN | txt | 同上 |
| 1333 | 数据质量监控节点 / DATA_QUALITY_MONITOR | DATA_QUALITY_MONITOR | DATA_QUALITY_MONITOR | TASK | UNKNOWN | txt | 同上 |

## 5. 核实结论与差异记录

- 6 个 Inventory 报告中的 UNKNOWN 编号（99 / 241 / 1101 / 1103 / 1106 / 1115）与官方
  节点定义**完全一致**，无编号差异。
- `file_type=23` 官方为「离线同步节点」（TaskType `DI`），项目内既有 name 沿用
  `OFFLINE_SYNC`，本次未改动。
- 官方文档正文提到「数据集成主站的任务通常 Code 为 `24`」，与节点编码表中
  24 = ODPS Script 并存；本次以节点编码表为准，未改动 24 的既有语义。
- 当前官方文档未列出既有注册条目 258（EMR Spark Shell）、1091（Hologres 开发）、
  1026（Task Flow）等；按「不修改已有类型语义」原则保持原样，标记为待确认。

## 6. 官方已定义、当前未注册（本次不添加）

以下编号在官方文档中有明确定义，但不在本次注册范围（当前 Workspace 无样本、
缺乏 Content 形态证据，或属于注册表尚未覆盖的引擎/数据库族），保持 UNKNOWN：

- MaxCompute：1010 SQL 组件节点
- EMR：231 EMR JAR、232 EMR File、264 EMR Spark Streaming、268 EMR Kyuubi
- CDH：270 / 271 / 272 / 273 / 278 / 279
- Hologres：1094 一键 MaxCompute 表结构同步、1095 一键 MaxCompute 数据同步
- 算法：1117 PAI Designer、1119 PAI DLC
- 其他通用节点：1320 FTP Check、1332 数据推送
- 数据库类节点：1000125、10001–100018、1000126、1000023

需要登记时，先在 Snapshot 中取得该类型的实际 GetFile 样本，再按第 2 节约定补条目。

## 7. 测试

- `tests/test_dataworks_types.py`：新增映射字段、既有映射（含 23）不回归、
  注册表无重复 `file_type`、未注册类型仍返回 UNKNOWN。
- `tests/test_inventory_summary.py`：8.1 节「未注册类型」用例使用未注册编号 `999`
  （`99` 已注册为虚拟节点，不再代表缺口）。

```bash
uv run pytest tests/test_dataworks_types.py tests/test_inventory_summary.py
```
