# 已知事实与业务确认清单

本清单只登记当前有来源的事实、技术观察、机器候选及待确认事项。它不修改 `source/` Snapshot，也不授权把技术推导提升为业务定义。

## 已确认业务事实

目前本项目尚未登记由业务责任方确认的业务事实。这里表示“尚无确认记录”，不表示企业不存在正式定义。

## 技术观察事实

| ID | 观察 | 来源 | 边界 |
| --- | --- | --- | --- |
| TECH-001 | 当前 Analysis Snapshot 提供 DataWorks File / SQL 内容与 MaxCompute 表字段元数据；Profiling 产物为 `metadata_only`，不包含业务行数据统计。 | `source/` Snapshot；`analysis/inventory/`；`analysis/evidence/profiling/` | 只能证明采集到的元数据与 SQL 原文，不能证明业务定义、行级质量或实际指标口径。 |
| TECH-002 | Inventory File 身份使用 Workspace 与 File 标识，Table 使用 `table_key`；Scope 资格不会删除 Inventory 登记对象。 | `analysis/inventory/`；`analysis/scope/` | 技术身份与分析范围，不是业务实体身份。 |

## 规则推导候选

| ID | 候选 | 来源 | 边界 |
| --- | --- | --- | --- |
| CAND-001 | Business Understanding 当前按配置词典识别 Domain / Object 候选；词条如 sales、customer、product、order 不是正式业务域或对象定义。 | `config/business-rules.yaml` v1.0 | 仅供候选识别，可由业务确认后修订；不可据此宣称企业正式口径。 |
| CAND-002 | Process 阶段当前用字段词汇匹配事务标识、度量、事件时间和状态信号。 | `config/process-rules.yaml` v1.0 | 字段信号不等于正式业务过程、业务粒度或指标定义。 |
| CAND-003 | Layer、SQL 引用、表关系及 Grain / Model 输出是技术规则推导或机器候选。 | `config/layer-rules.yaml`；`analysis/evidence/`；`analysis/understanding/` | 需按各阶段边界和证据链核验；不得作为业务方确认的事实。 |

## 尚待业务确认的假设与输入

- 尚未收到正式业务域、业务对象 / 过程定义、业务粒度、指标口径、排除条件或经业务确认的例外清单。
- 需要业务责任方提供事实来源、适用范围、生效日期 / 版本，并确认与现有机器候选的冲突。
- 本清单不推测具体企业流程、表的业务含义或指标口径。

## 配置接入边界

- 只有明确需要机器候选识别、且已由业务确认的稳定词汇 / 别名，才考虑加入 `config/business-rules.yaml` 或 `config/process-rules.yaml`；配置仍表达候选识别规则，不替代事实来源和确认记录。
- 正式定义、适用范围、粒度、指标公式、排除条件、业务例外及冲突裁决，先留在本目录供人工评审；当前 Understanding 没有这些事实的配置输入契约，不扩展新配置引擎。
- Scope 只管理技术分析资格，不消费或反向修改业务事实；所有变更都不得写入、改写或覆盖 `source/` Snapshot。
