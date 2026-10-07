# SQL Analysis Limitation Report

## 问题描述

在分析真实生产 SQL 文件 `504340625__dwd_o2o_platform_sale_info.sql` 时发现：

- **Statement A (CREATE TABLE AS SELECT)**：被解析为 `Command`，不是 `Create`
- **Statement B (INSERT OVERWRITE)**：成功解析为 `Insert`

## 根本原因

### SQL 结构
```sql
CREATE TABLE ${dme_cdm}.temp01 AS
SELECT ... FROM (
    SELECT ... WHERE ds=max_pt(...) 
    LATERAL VIEW explode(col) c AS item
) x
LEFT JOIN ...
UNION ALL
SELECT ... FROM s2
```

### sqlglot 限制

**sqlglot 30.20.0 的 Hive 方言无法解析这种复杂组合：**
- LATERAL VIEW 在子查询中
- 子查询后有 JOIN
- 整个语句有 UNION ALL

### 测试结果

| SQL 结构 | 解析类型 |
|---------|---------|
| CTAS only | ✅ Create |
| CTAS + LATERAL VIEW (simple) | ✅ Create |
| CTAS + UNION ALL | ✅ Create |
| CTAS + LATERAL VIEW in subquery + JOIN + UNION ALL | ❌ Command |

## 影响范围

### 问题文件
- `504340625__dwd_o2o_platform_sale_info.sql` (statement 2)

### 影响的表引用
- ❌ `dwd_o2o_platform_sale_info_temp01` (target) - 无法提取
- ❌ `s_o2o_platform_sale_info` (source) - 无法提取  
- ❌ `dwd_master_data_product_pos_bu` (source) - 无法提取
- ❌ `s_tmkt_o2o_k1k2_mapping` (source) - 无法提取
- ❌ `s_o2o_dmall_sale_info_all` (source) - 无法提取

### 可用的证据
- ✅ Statement B (INSERT OVERWRITE) 正常工作
- ✅ 可以从 INSERT 语句中提取 `dwd_o2o_platform_sale_info` 的 target

## 建议方案

### 方案 1：CTAS fallback（✅ 已实施）

AST 解析为 unsupported（`exp.Command`）且语句具备 CTAS 特征时，
交给 token scanner 提取 target 与 source：

- 门槛：`is_ctas_statement(fragment)`（`CREATE TABLE ... AS <select|with>`）；
- 提取：`extract_ctas_references(fragment)`，单向前扫描，每轮游标严格前进；
- 结果：提取成功按 `parse_status=success` + `extraction_method=fallback` 记录，
  scanner 无结果时保持 `unsupported`（`SQL_UNSUPPORTED_STATEMENT`）；
- 溯源：`statements.json` / `table-references.json` / `table-lineage.json` 的
  evidence 都带 `extraction_method` 字段，可区分 ast 与 fallback。

实现位置：`src/data_platform_analysis/analysis/sql/fallback.py`，
测试：`tests/test_ctas_fallback.py`（含 Golden Case 与死循环看门狗）。

**优点：**
- 不依赖 parser，只依赖 tokenizer；
- 结果带提取方式标记，血缘证据可区分来源。

**缺点：**
- 只覆盖 CTAS 形态；其他 unsupported 语句仍按原样记录；
- 复杂语法（函数当表、未闭合参数等）按保守策略丢弃，宁可少报不误报。

### 方案 2：记录为已知限制

在文档中说明：
> 复杂的 CTAS 语句（LATERAL VIEW + 子查询 + JOIN + UNION ALL）可能无法被 sqlglot 完全解析

### 方案 3：升级 sqlglot 版本

尝试更高版本的 sqlglot 是否支持该语法。

## 立即行动

1. ✅ 确认问题：SQL 结构和 sqlglot 版本
2. ✅ 验证限制：测试不同组合
3. ✅ 实施方案：CTAS token scanner fallback（`analysis/fallback.py`）
4. ✅ 更新测试：Golden Case + scanner 单元测试（`tests/test_ctas_fallback.py`）

## 结论

**这不是代码 bug，而是 sqlglot 的已知限制。**

已实施 **方案 1（CTAS token scanner fallback）**：
Golden Case `504340625` statement 2 不再记为 `SQL_UNSUPPORTED_STATEMENT`，
按 `success` + `extraction_method=fallback` 产出 1 个 target 与 4 个 source，
血缘多出 4 条边，`analysis/errors.json` 归零。
