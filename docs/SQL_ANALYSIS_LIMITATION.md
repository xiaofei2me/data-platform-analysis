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

### 方案 1：字符串匹配 fallback（推荐）

当 sqlglot 无法解析为 Create/Insert 时，使用简单规则从 SQL 文本中提取 table names：

```python
# 使用 regex 提取潜在的表名
import re

TABLE_PATTERN = r"\b(?:from|join|into|overwrite\s+table)\s+(?:\w+\.)?(\w+)"
tables = re.findall(TABLE_PATTERN, sql_text)
```

**优点：**
- 简单快速
- 不依赖 parser

**缺点：**
- 可能误匹配 CTE、子查询别名等
- 需要过滤非物理表

### 方案 2：记录为已知限制

在文档中说明：
> 复杂的 CTAS 语句（LATERAL VIEW + 子查询 + JOIN + UNION ALL）可能无法被 sqlglot 完全解析

### 方案 3：升级 sqlglot 版本

尝试更高版本的 sqlglot 是否支持该语法。

## 立即行动

1. ✅ 确认问题：SQL 结构和 sqlglot 版本
2. ✅ 验证限制：测试不同组合
3. ⏳ 实施方案：选择合适的 fallback 方法
4. ⏳ 更新测试：覆盖此场景

## 结论

**这不是代码 bug，而是 sqlglot 的已知限制。**

建议采用 **方案 1（字符串匹配 fallback）** 来处理无法解析的 SQL，确保数据流证据不丢失。
