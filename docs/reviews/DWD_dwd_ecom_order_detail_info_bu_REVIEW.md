# DWD 模型评审工作底稿：`dme_cdm.dwd_ecom_order_detail_info_bu`

> **用途**：将 [DWD 模型质量评估与整改规范](../DWD_MODEL_QUALITY_AND_REMEDIATION_STANDARD.md)转成一张可执行的评审工作单。\
> **当前状态**：证据盘点完成；业务定义、MaxCompute 只读数据验证、整改决策和业务验收均未完成。\
> **重要边界**：本底稿中的机器候选不是业务事实或已确认缺陷。下列 SQL 是经当前字段名/类型和原 SQL 条件核对后的**待执行模板**，没有在本轮执行。

## 1. 评审基线

| 项目 | 当前核对结果 | 来源 |
|---|---|---|
| Table Key | `dme_cdm.dwd_ecom_order_detail_info_bu` | [Inventory tables](../../analysis/inventory/tables.json)；[MaxCompute Snapshot metadata](../../source/maxcompute/workspaces/466337/tables/dwd_ecom_order_detail_info_bu.json) |
| Workspace / Project | Workspace ID `466337`，`dme_cdm` | [Snapshot manifest](../../source/manifest.json)；Inventory |
| 表列元数据 | 70 列；`ds` 为 `STRING` 分区列；Inventory 记 `partition_count=1` | [Inventory columns](../../analysis/inventory/columns.json)、[Inventory tables](../../analysis/inventory/tables.json)、Snapshot metadata |
| 表注释 | `ec订单明细表` | Snapshot metadata；这是技术元数据，不是正式业务定义 |
| Snapshot 时点 | `source/manifest.json` 的 `generated_at` 为 `2026-10-09T12:40:13.475581+00:00` | [Snapshot manifest](../../source/manifest.json) |
| SQL File 身份 | File `504340559`、Node `700006513464`；Scope 标记 `identity_eligible=true`、`overall_eligible=true`、`sql_eligible=true`、内容 `present` | [Scope SQL candidates](../../analysis/scope/inputs/sql-candidates.json) |
| 目标写入 | File `504340559` / Statement `7`；解析状态 `success`、提取方法 `ast` | [SQL statements](../../analysis/evidence/sql/statements.json)、[SQL references](../../analysis/evidence/sql/table-references.json) |
| 目标输出列 | Statement 7 的目标 SELECT 投影共 70 个表达式，含末尾分区值 `a.ds`；应在执行变更前再与当前 DDL 的列顺序核对 | Statement 7 与 Snapshot metadata |
| DDL 完整性 | 本地提供的是表/列元数据 JSON，不是可确认所有约束的建表 DDL；未观察到主键/唯一性约束定义 | [Snapshot metadata](../../source/maxcompute/workspaces/466337/tables/dwd_ecom_order_detail_info_bu.json) |
| 分析运行 provenance | 当前 `analysis/` 不提供可将每阶段产物绑定到同一代码版本和 Snapshot 内容哈希的 run manifest | [审查报告](ANALYSIS_RESULT_AUDIT.md) |
| 本轮执行 | 未运行 SQL、Pipeline、`analyze` 或测试；未改动 Snapshot、`analysis/`、代码、配置或人工清单 | 本次工作边界 |

Git 基线：`main`，HEAD `2d7edfe50a0b144553e31d38920395337dc374e0`。开始工作时已存在 `analysis/scope/summary.json` 的 staged deletion + untracked 状态，以及此前新增但未提交的规范和审查报告；本轮保留这些状态，仅新增本底稿。

## 2. 证据目录与证据分类

| 证据类别 | 已有来源 | 能支持什么 | 不能据此证明什么 |
|---|---|---|---|
| **Observed：资产与列元数据** | [Inventory table](../../analysis/inventory/tables.json)、[Inventory columns](../../analysis/inventory/columns.json)、[原始表元数据](../../source/maxcompute/workspaces/466337/tables/dwd_ecom_order_detail_info_bu.json) | 表身份、列名、类型、注释、分区标记和 Snapshot 时点 | 业务含义、物理行唯一性、全部 DDL 约束 |
| **Observed：资格和 SQL** | [Scope SQL candidates](../../analysis/scope/inputs/sql-candidates.json)、[Statements](../../analysis/evidence/sql/statements.json)、[Table References](../../analysis/evidence/sql/table-references.json)、[原始 DataWorks SQL](../../source/dataworks/workspaces/466337/content/504340559__dwd_ecom_order_detail_info_bu.sql) | File 是否进入 SQL 分析；解析出的语句身份、表引用；快照中的 SQL 逻辑文本 | SQL 实际运行成功、数据结果正确、字段级 lineage 或 JOIN 基数 |
| **Observed：Layer / Lineage / Profiling** | [Layer assessments](../../analysis/evidence/layer/assessments.json)、[Table lineage](../../analysis/evidence/lineage/table-lineage.json)、[Table profiles](../../analysis/evidence/profiling/tables.json)、[Column profiles](../../analysis/evidence/profiling/columns.json) | 规则层级状态、SQL 表级依赖及证据 File/Statement、元数据画像范围 | 层级职责已批准、调度 DAG 完整、行级数据质量已验证 |
| **Inferred：理解和 Review** | [Grain candidates](../../analysis/understanding/business/grain-candidates.json)、[Fact candidates](../../analysis/understanding/modeling/fact-candidates.json)、[Findings](../../analysis/review/current-state-findings.json)、[Problems](../../analysis/review/current-state-problems.json) | 当前机器候选及触发的结构信号，可用于安排评审 | 业务 grain、键唯一、重复模型、真实缺陷 |
| **Observed：Coverage 导航** | [Evidence coverage ledger](../../analysis/review/evidence-coverage.json) | 将表身份关联到 Layer、Profiling、SQL 引用、Lineage、Understanding、Review 和已知限制 | `problem_candidate` 是 FAIL，或“available”代表证据充分 |
| **Observed：人工状态入口** | [Problem review checklist](../../analysis/review/current-state-problem-review-checklist.md)、[Finding review checklist](../../analysis/review/current-state-review-checklist.md)、[Grain review checklist](../../analysis/understanding/business/grain-review-checklist.md) | 清单可见范围中的人工回填列与候选；须结合清单的分区/行数上限阅读 | 清单未展示某 ID 即该项未评审；截断清单不是全量评审账本 |

Problem Evidence 汇总当前显示 SQL 类型证据为 0；Review v2 不直接消费 SQL References 或 Profiling。因此本评审须由业务/技术评审者回到 SQL 和 Coverage 自行补全关联，不应把 Problem 记录说成已包含目标 Statement 证据。

## 3. 目标表 70 列清单

以下列名、类型、分区标记均取自当前 [Inventory columns](../../analysis/inventory/columns.json)；中文注释取自 Inventory / Snapshot metadata。注释仅是元数据事实。`ds` 是唯一标记为分区列的字段。

| # | 列 | 类型 | 分区 | # | 列 | 类型 | 分区 |
|---:|---|---|:---:|---:|---|---|:---:|
| 1 | `ec_code` | STRING |  | 36 | `shop_id` | STRING |  |
| 2 | `ec_name` | STRING |  | 37 | `shop_name` | STRING |  |
| 3 | `order_no` | STRING |  | 38 | `bu_1` | STRING |  |
| 4 | `sub_order_no` | STRING |  | 39 | `bu_2` | STRING |  |
| 5 | `commodity_sku` | STRING |  | 40 | `henkel_region_name` | STRING |  |
| 6 | `commodity_name` | STRING |  | 41 | `province_name` | STRING |  |
| 7 | `brand_code` | STRING |  | 42 | `city_name` | STRING |  |
| 8 | `brand_name` | STRING |  | 43 | `district_name` | STRING |  |
| 9 | `commodity_title` | STRING |  | 44 | `bu_3` | STRING |  |
| 10 | `quantity` | BIGINT |  | 45 | `num_iid` | STRING |  |
| 11 | `unit_price` | DECIMAL(28,6) |  | 46 | `tax_rate` | DECIMAL(28,6) |  |
| 12 | `total_price_tax` | DECIMAL(28,6) |  | 47 | `retail_price_untax` | DECIMAL(28,6) |  |
| 13 | `total_price_untax` | DECIMAL(28,6) |  | 48 | `base_price_tax` | DECIMAL(28,6) |  |
| 14 | `express_company_code` | STRING |  | 49 | `base_sale_amt_tax` | DECIMAL(28,6) |  |
| 15 | `express_company_name` | STRING |  | 50 | `retail_amt_untax` | DECIMAL(28,6) |  |
| 16 | `express_num` | STRING |  | 51 | `sales_channel` | STRING |  |
| 17 | `sub_order_state` | STRING |  | 52 | `customer_code` | STRING |  |
| 18 | `create_time` | DATETIME |  | 53 | `customer_name` | STRING |  |
| 19 | `base_price` | DECIMAL(28,6) |  | 54 | `ec` | STRING |  |
| 20 | `base_sale_amt` | DECIMAL(28,6) |  | 55 | `data_source_code` | STRING |  |
| 21 | `retail_price_tax` | DECIMAL(28,6) |  | 56 | `data_source_name` | STRING |  |
| 22 | `retail_tax_amt` | DECIMAL(28,6) |  | 57 | `shop_id_tp` | STRING |  |
| 23 | `henkel_item_barcode` | STRING |  | 58 | `shop_name_tp` | STRING |  |
| 24 | `henkel_idh_code` | STRING |  | 59 | `platform` | STRING |  |
| 25 | `henkel_brand_code` | STRING |  | 60 | `data_type` | STRING |  |
| 26 | `henkel_brand` | STRING |  | 61 | `channel_customer_permission` | STRING |  |
| 27 | `henkel_brand_en` | STRING |  | 62 | `region_customer_permission` | STRING |  |
| 28 | `henkel_category_code` | STRING |  | 63 | `channel_ka_permission` | STRING |  |
| 29 | `henkel_category` | STRING |  | 64 | `henkel_store_category` | STRING |  |
| 30 | `henkel_category_en` | STRING |  | 65 | `henkel_store_category_lv1` | STRING |  |
| 31 | `first_channel_id` | STRING |  | 66 | `henkel_store_category_lv2` | STRING |  |
| 32 | `first_channel_name` | STRING |  | 67 | `second_channel_name` | STRING |  |
| 33 | `unint_price_actual` | DECIMAL(28,6) |  | 68 | `third_channel_name` | STRING |  |
| 34 | `payment_actual` | DECIMAL(28,6) |  | 69 | `fourth_channel_name` | STRING |  |
| 35 | `untax_payment_actual` | DECIMAL(28,6) |  | 70 | `ds` | STRING | ✓ |

**需业务/模型 owner 确认的字段疑点（不是已确认缺陷）**：`unint_price_actual` 的拼写按当前 Metadata 保留；`shop_id_tp` 的 Snapshot 注释写“TP侧门店名称”，而 SQL 投影表达式是 `a.shop_id`（注释/字段名可能不一致）；`data_type` 的表注释写“数据类型”，SQL 某来源写常量 `'常规'`。确认其合同含义、兼容要求和消费者后再决定是否改名/改值。

## 4. SQL 加工链与可观察逻辑

### 4.1 Statement 关系

当前 SQL References 把同一 File 的以下语句连成目标加工链（Statement 均 `parse_status=success`，`extraction_method=ast`）：

| Statement | 当前 SQL 目标/作用 | Table References |
|---:|---|---|
| 2 | 创建 `dwd_ecom_order_detail_info_bu_temp_01`；TP POS 与迈志来源 `UNION ALL` | 来源包括 `dwd_ecom_order_detail_info_bu_mid`、`dwd_ka_pos_data_sales_daily_mid`、客户/区域/城市 mapping |
| 4 | 创建 `dwd_ecom_order_detail_info_bu_temp_02`；产品 BU 与店铺购物金 BU 映射 | 输入 `_temp_01`、`dwd_master_data_product_pos_bu`、`dwd_ecom_store_main_brand_mapping` |
| 6 | 创建 `dwd_ecom_order_detail_info_bu_temp_03`；对店铺及 BU 信息聚合/去重 | 输入 `_temp_02` |
| 7 | `INSERT OVERWRITE ... PARTITION(ds)` 写目标 DWD 表 | 输入 `_temp_02`、`_temp_03`、`dwd_master_data_store_bu`、`dwd_master_data_customer_bu` |

来源：File `504340559` 的 [SQL statements](../../analysis/evidence/sql/statements.json)、[SQL references](../../analysis/evidence/sql/table-references.json) 与 [原始 SQL 内容](../../source/dataworks/workspaces/466337/content/504340559__dwd_ecom_order_detail_info_bu.sql)。解析成功仅说明 Parser 识别，不说明逻辑或执行结果正确。

### 4.2 已观察到的转换

- Statement 2 的 TP 分支读取 `_bu_mid` 的 `MAX_PT` 分区，筛 `upper(store_category) in ('ECOM','OTHERS')`，将 `pay_time` 投影为 `ds`；随后与迈志路径 `UNION ALL`。
- Statement 2 的迈志路径从 `dwd_ka_pos_data_sales_daily_mid` 取 `MAX_PT` 分区并筛 `upper(first_channel_name)='ECOM'`。原 SQL 可见：
  - `quantity = sum(nvl(return_base_unit_qty,0)+nvl(base_unit_qty,0)`；
  - `total_price_tax = sum(dist_prod_price*dist_prod_qty*tax_rate)`；
  - `total_price_untax = sum(dist_prod_price*dist_prod_qty)`；
  - `payment_actual = sum(nvl(original_amt_tax,0)+nvl(return_original_amt_tax,0))`；
  - `untax_payment_actual = sum(nvl(original_amt_untax,0)+nvl(return_original_amt_untax,0))`；
  - 过滤 `nvl(quantity,0)<>0 OR nvl(payment_actual,0)<>0`；
  - `GROUP BY` 不仅包含 `order_no`、`sub_order_no`、`dist_prod_barcode`，还包含商品/价格/税率、客户、门店、BU、地区、来源、门店分类、渠道等字段。
- Statement 2 两来源用 `UNION ALL`；除非两来源不重叠或业务定义允许并行记录，否则不能仅凭这个语句判断重复或冲突。
- Statement 4 的产品匹配条件是 `a.henkel_item_barcode=b.product_barcode`，并在右表约束 `b.ds=MAX_PT(...)`；店铺购物金映射按 `a.store_code=d.shop_id`，右表亦取 `MAX_PT`。
- Statement 6 从 `_temp_02` 对 `shop_id` / `shop_name` / `bu_2` 分组，再按 `shop_id` 聚合 `COLLECT_SET(bu_2)`，产出 `bu_3` 组合并 `DISTINCT`。`DISTINCT(shop_id,bu_3)` 不必然保证 `shop_id` 唯一。
- Statement 7 无 WHERE 条件，从 `_temp_02` 读取全部行，LEFT JOIN 三个右侧对象；投影 `a.store_code AS shop_id` 和 `a.shop_id AS shop_id_tp`，对缺失匹配的若干字段用 `NVL(...,'Others')` / `'Others_Others'`，`bu_3` 只在 `bu_2 in ('SKP','SP')` 时取 `nvl(b.bu_3,'Others')`，最后将 `a.ds` 写入分区列。

**上述均为 SQL 文本的观察事实。** 业务语义、金额正负方向、税率单位、`ds` 含义、右表唯一性和是否会放大行数均未由当前文件证明。

### 4.3 每个实际 JOIN 的核查表

以下按 SQL 调用链列出 9 个 JOIN。表内“FAIL 条件”须同时有已确认的业务合同和可复现数据证据；否则先标为待确认/待验证。

| # | SQL / 右侧对象 | 实际 ON / 右侧过滤 | 核心验证 | FAIL 的必要条件 |
|---:|---|---|---|---|
| 1 | Statement 2 / `dwd_master_data_customer_bu b` | `a.customer_code=b.customer_code AND a.bu_2=b.bu_2 AND b.ds=MAX_PT(...)` | 在被用的 `ds` 下检查 `(customer_code,bu_2)` 多匹配；统计左侧未匹配/多匹配；验证同一目标行投影客户名的预期 | 业务合同要求该 scope 唯一/匹配，而查询发现未豁免的多匹配或错误缺配，并证明造成目标行扩张/错误字段或金额影响 |
| 2 | Statement 2 / `dim_area_trans d` | 子查询筛 `ds=MAX_PT(...) AND area_type='province'`；`a.order_province_name=d.area_ch` | 当前分区 + `area_type='province'` 下 `area_ch` 唯一性、空键和未匹配 | 已批准省份映射要求唯一/覆盖，实际多匹配/错误映射并影响地区或下游计算 |
| 3 | Statement 2 / `s_city_province_mapping e` | 子查询按 `(district_name,city_name)` 分组；`a.order_city_name=e.district_name` | 在实际 Snapshot 分区（SQL 中为 MAX_PT）下按 `district_name` 的不同 `city_name` 和行数统计；检查同名区县跨省情形 | 经业务确认 join key 应含更细范围/唯一，但实际同一 district 匹配多条并产生错误地区或影响目标行/消费 |
| 4 | Statement 2 / `dwd_province_region_change_mapping f` | `nvl(d.area_ch,'')=nvl(f.province_name,'') AND f.ds=MAX_PT(...)` | 在所用分区检查归一化后 `province_name` 多匹配，特别检查 NULL/空串都变成 `''`；并检查未匹配 | 区域 mapping 在业务定义下应唯一且空值不可合并，实际多匹配/错映射影响结果 |
| 5 | Statement 4 / `dwd_master_data_product_pos_bu b` | `a.henkel_item_barcode=b.product_barcode AND b.ds=MAX_PT(...)` | 当前右表分区 `product_barcode` 重复数、未匹配和一源多目标；按产品/BU/来源切片复核 | 业务要求 barcode 在此 join scope 唯一或多值已定义，但多匹配导致 BU 错配/事实重复或错误指标 |
| 6 | Statement 4 / `dwd_ecom_store_main_brand_mapping d` | 子查询筛 mapping 的 `ds=MAX_PT(...)`；`a.store_code=d.shop_id` | 当前分区 `shop_id` 多匹配/空值；核实 mapping 的业务有效粒度与 store_code 映射 | 已确认要求一店一 mapping 或特定唯一规则，实际冲突导致错误 BU 转换/扇出 |
| 7 | Statement 7 / `_temp_03 b` | `a.shop_id=b.shop_id`；当前 Schema 无 `ds` 列 | 每个 `shop_id` 对应行数/不同 `bu_3`；评估 `_temp_03` 的 DISTINCT 是否仍使 shop_id 多行 | 业务确认用于 BU3 补充的关系在目标行范围应为 0/1，但实际多匹配导致目标一行展开或 bu_3 不确定 |
| 8 | Statement 7 / `dwd_master_data_store_bu c` | 子查询筛 `ds=MAX_PT(...)`；`a.store_code=c.store_code` | 最新分区 `store_code` 重复、目标侧 store_code 未匹配/多匹配、`shop_name/platform` 值一致性 | 业务合同要求当前店铺映射唯一且匹配；实际违反并引发目标扩张或错误门店/平台属性 |
| 9 | Statement 7 / `dwd_master_data_customer_bu e` | `a.customer_code=e.customer_code AND a.bu_2=e.bu_2 AND e.ds=MAX_PT(...)` | 最新分区 composite key 重复、未匹配/多匹配；与 Statement 2 的同键 join 分开验证 | 已确认 customer/BU mapping 唯一/覆盖要求被违反且证明影响目标列或度量 |

**来源 Schema 限制**：Inventory 当前有上述静态表/列元数据；临时表列定义是 Snapshot 元数据，并不证明本次任务运行时物理内容/分区时点。Statement 2/4/7 使用的 `MAX_PT` 由任务运行时解析；执行查询时需记录实际取得的分区值，不能假定静态 Snapshot 证明它。

## 5. 粒度和候选键评审任务

### 5.1 机器候选

当前 [Grain Candidate JSON](../../analysis/understanding/business/grain-candidates.json) 中与目标关联的记录：

| ID | 机器候选键 | Pattern | Status / unresolved |
|---|---|---|---|
| `grain_candidate_419` | `customer_code + order_no` | transaction | candidate / `multiple_possible_keys` |
| `grain_candidate_420` | `customer_code + sub_order_no` | transaction | candidate / `multiple_possible_keys` |
| `grain_candidate_421` | `order_no` | transaction | candidate / `multiple_possible_keys` |
| `grain_candidate_422` | `sub_order_no` | transaction | candidate / `multiple_possible_keys` |

`strength=strong` 是候选算法的证据类型强度，不是数据唯一性证明。Grain Review checklist 当前对 `process_candidate_004` 仅展示有限行；未见目标 grain ID 不代表人工已确认或驳回。应由 Grain/业务 owner 在受控评审记录中明确回填并保留日期/版本。

### 5.2 业务确认先行

| 业务问题 | 必须回答的具体问题 | 建议确认角色 |
|---|---|---|
| 业务事件 | 一行描述订单、子订单、商品行、POS 交易、支付、退款/退货，还是某种 source-specific record？事件发生/生效时点是什么？ | 电商业务过程 owner；源系统 owner |
| TP / 迈志关系 | 两来源是否描述互斥范围、重叠范围或不同业务事件？`UNION ALL` 是否符合已批准口径？ | 各来源 owner；电商业务 owner |
| 唯一标识 | 四个候选键分别标识什么对象？是否需加 source、BU、商品行 ID、事件/版本或时间？哪些例外是合法的？ | 电商业务 owner；模型 owner |
| 记录重复/更正 | 重复投递、订单修改、部分退款、退货、拆分/合单、多次支付是否保留为多行、覆盖旧行或冲正？ | 电商业务、财务/指标 owner |
| GROUP BY 合同 | Statement 2 中一组分组字段是否与业务要表达的一行一致？哪些属性变化时应该拆成多行？ | 业务 owner；SQL owner |

### 5.3 待执行查询：候选键重复和缺失

**执行前置条件**：先由业务 owner 确认要检验的定义及 scope；取得可复现的目标分区列表；确认所有来源/状态/更正场景纳入。当前 `ds` 为 STRING，但具体格式和范围语义未确认，因此以下只用单个已确认分区的等值条件，不使用未经验证的日期字符串范围。

以下复合字段均在目标 Inventory 中存在且类型为 STRING。每组只是 candidate 检验，不预设其为合法业务键。

```sql
-- 针对一个经评审确认的分区执行；需要全历史时逐分区/定义范围执行。
SELECT 'customer_code+order_no' AS candidate_key,
       customer_code AS key_1,
       order_no AS key_2,
       COUNT(*) AS row_count
FROM dme_cdm.dwd_ecom_order_detail_info_bu
WHERE ds = '<已确认的分区值>'
GROUP BY customer_code, order_no
HAVING COUNT(*) > 1

UNION ALL

SELECT 'customer_code+sub_order_no',
       customer_code,
       sub_order_no,
       COUNT(*)
FROM dme_cdm.dwd_ecom_order_detail_info_bu
WHERE ds = '<已确认的分区值>'
GROUP BY customer_code, sub_order_no
HAVING COUNT(*) > 1

UNION ALL

SELECT 'order_no',
       order_no,
       CAST(NULL AS STRING),
       COUNT(*)
FROM dme_cdm.dwd_ecom_order_detail_info_bu
WHERE ds = '<已确认的分区值>'
GROUP BY order_no
HAVING COUNT(*) > 1

UNION ALL

SELECT 'sub_order_no',
       sub_order_no,
       CAST(NULL AS STRING),
       COUNT(*)
FROM dme_cdm.dwd_ecom_order_detail_info_bu
WHERE ds = '<已确认的分区值>'
GROUP BY sub_order_no
HAVING COUNT(*) > 1;
```

**语法/字段注意**：这是 MaxCompute 风格 `SELECT`/`GROUP BY`/`UNION ALL`；键成员在目标列清单中已核实为 STRING，`ds` 为 STRING 分区列。运行前仍须验证 `SHOW PARTITIONS` 返回值与访问权限；不要把占位符原样执行。若当前租户不接受 `CAST(NULL AS STRING)` 或 UNION 分支类型推导，应分开运行四个 SELECT，而不是改用拼接键。

NULL/空值检查模板（同样按已批准的分区分别执行；`TRIM` 只对这些 STRING 候选字段使用）：

```sql
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN customer_code IS NULL OR TRIM(customer_code) = '' THEN 1 ELSE 0 END)
        AS missing_customer_code,
    SUM(CASE WHEN order_no IS NULL OR TRIM(order_no) = '' THEN 1 ELSE 0 END)
        AS missing_order_no,
    SUM(CASE WHEN sub_order_no IS NULL OR TRIM(sub_order_no) = '' THEN 1 ELSE 0 END)
        AS missing_sub_order_no
FROM dme_cdm.dwd_ecom_order_detail_info_bu
WHERE ds = '<已确认的分区值>';
```

**解释规则**：查询返回重复或缺失只产生数据观察。只有业务合同规定该组合在所查范围内必须唯一/非空，且没有合法事件、多版本、来源或回补例外，才可能判该维度 FAIL。若 key 未获业务确认，应标 `NEEDS_BUSINESS_CONFIRMATION`；若定义已明确但查询尚未执行，标 `NEEDS_DATA_VALIDATION`。

## 6. 每个 JOIN 的验证查询模板

### 6.1 JOIN key 多匹配检查

先从任务运行参数/同一份数据快照记录各 `MAX_PT` 的实际输出，再填入 `<AS_OF_DS_...>`。查询右侧时必须复现原 SQL 中完全相同的过滤条件。`MAX_PT` 是原 SQL 使用的函数，但本底稿不调用或假设其当前返回值。

```sql
-- Statement 7: _temp_03 按 shop_id 关联；Inventory 有 shop_id STRING、bu_3 STRING，
-- 未发现 ds 列，所以不要附加 ds 条件。
SELECT shop_id, COUNT(*) AS right_rows
FROM dme_cdm.dwd_ecom_order_detail_info_bu_temp_03
GROUP BY shop_id
HAVING COUNT(*) > 1;

-- Statement 7: 店铺主数据，等价于原 SQL 当前分区的右表范围。
SELECT store_code, COUNT(*) AS right_rows
FROM dme_cdm.dwd_master_data_store_bu
WHERE ds = '<AS_OF_DS_STORE>'
GROUP BY store_code
HAVING COUNT(*) > 1;

-- Statement 7 和 Statement 2: 客户主数据 composite key。
SELECT customer_code, bu_2, COUNT(*) AS right_rows
FROM dme_cdm.dwd_master_data_customer_bu
WHERE ds = '<AS_OF_DS_CUSTOMER>'
GROUP BY customer_code, bu_2
HAVING COUNT(*) > 1;

-- Statement 4: 产品 BU 主数据。
SELECT product_barcode, COUNT(*) AS right_rows
FROM dme_cdm.dwd_master_data_product_pos_bu
WHERE ds = '<AS_OF_DS_PRODUCT>'
GROUP BY product_barcode
HAVING COUNT(*) > 1;

-- Statement 4: 店铺购物金 BU 映射。
SELECT store_code, COUNT(*) AS right_rows
FROM dme_cdm.dwd_ecom_store_main_brand_mapping
WHERE ds = '<AS_OF_DS_STORE_BRAND>'
GROUP BY store_code
HAVING COUNT(*) > 1;

-- Statement 2: 区域/省份映射；严格保留原子查询过滤。
SELECT area_ch, COUNT(*) AS right_rows
FROM dme_cdm.dim_area_trans
WHERE ds = '<AS_OF_DS_AREA>'
  AND area_type = 'province'
GROUP BY area_ch
HAVING COUNT(*) > 1;

-- Statement 2: 城市映射的 SQL 会先按 district_name,city_name 分组，
-- 但 JOIN 仅用 district_name；本查询检查过滤范围内每个 district 实际对应多少组。
SELECT district_name, COUNT(*) AS city_rows
FROM (
    SELECT district_name, city_name
    FROM dme_ods.s_city_province_mapping
    WHERE ds = '<AS_OF_DS_CITY>'
    GROUP BY district_name, city_name
) city_map
GROUP BY district_name
HAVING COUNT(*) > 1;

-- Statement 2: NULL 与空 province_name 在原 SQL 中都会经 NVL 归并为 ''。
SELECT
    CASE WHEN province_name IS NULL OR TRIM(province_name) = ''
         THEN '<NULL_OR_EMPTY>' ELSE province_name END AS normalized_province,
    COUNT(*) AS right_rows
FROM dme_cdm.dwd_province_region_change_mapping
WHERE ds = '<AS_OF_DS_REGION>'
GROUP BY CASE WHEN province_name IS NULL OR TRIM(province_name) = ''
              THEN '<NULL_OR_EMPTY>' ELSE province_name END
HAVING COUNT(*) > 1;
```

**覆盖缺口**：区域查询只是一个规范化键检查，需按原 SQL 的 `NVL(d.area_ch,'') = NVL(f.province_name,'')` 精确复现左/右 join key 后再算实际匹配数；占位标签 `<NULL_OR_EMPTY>` 也必须确认不与真实值冲突。若 engine 对 `CASE` `GROUP BY` 语法或占位 DS 表达式有差异，在只读查询控制台验证并记录，不要自行把未验证查询结果写作证据。

还应检查 `s_city_province_mapping` 在其选定分区每个 `district_name` 的省份覆盖；当前 JOIN 没有省份条件。是否需要补充省份键由业务确认，不能仅因 district 重名就直接判错。

### 6.2 左右键覆盖与分组扇出

当事实表没有已确认的稳定物理行标识时，不用未经验证的候选键模拟 row ID。先按 JOIN 键聚合左右表，计算连接的**键组级预期输出行数**；该值用于定位潜在扇出，不等同逐事实证明：

```sql
WITH left_keys AS (
    SELECT shop_id AS join_key, COUNT(*) AS left_rows
    FROM dme_cdm.dwd_ecom_order_detail_info_bu_temp_02
    GROUP BY shop_id
),
right_keys AS (
    SELECT shop_id AS join_key, COUNT(*) AS right_rows
    FROM dme_cdm.dwd_ecom_order_detail_info_bu_temp_03
    GROUP BY shop_id
)
SELECT
    SUM(l.left_rows) AS left_rows,
    SUM(CASE WHEN r.right_rows IS NULL THEN l.left_rows
             WHEN r.right_rows < 1 THEN l.left_rows
             ELSE l.left_rows * r.right_rows END) AS predicted_left_join_rows,
    SUM(CASE WHEN r.right_rows IS NULL THEN l.left_rows ELSE 0 END) AS unmatched_left_rows,
    SUM(CASE WHEN r.right_rows > 1 THEN l.left_rows ELSE 0 END) AS left_rows_with_multiple_matches
FROM left_keys l
LEFT JOIN right_keys r
  ON l.join_key = r.join_key;
```

将上述查询按真实 JOIN 逐个改写到：

1. Statement 7 `_temp_02.store_code` → 最新店铺分区 `store_code`；
2. Statement 7 `_temp_02.(customer_code,bu_2)` → 最新客户分区同键；
3. Statement 4 `_temp_01.henkel_item_barcode` → 最新产品分区 `product_barcode`；
4. Statement 4 `_temp_01.store_code` → 最新店铺映射分区 `shop_id`；
5. Statement 2 省、区县、区域 mapping joins。

执行时确保左、右两边均与生产语句使用相同分区和过滤；当前 `_temp_02`、`_temp_03` 是任务加工产物，需固定同一次生产运行/一致 Snapshot。LEFT JOIN 在右侧 0 行时保留左行，1 对多才有行数扩张；预测行数增加仍需业务合同判断是否非法。

### 6.3 Statement 7 实际三次 JOIN 的输出对比

对同一运行物化的 `_temp_02`、`_temp_03`、主数据分区与目标分区，按 `ds` 比较 source-side 和实际 target；先检查字段结构/列投影能否按目标列序对齐。以下只提供记录数、金额/数量总量诊断，不单独构成正确性证明：

```sql
SELECT
    a.ds,
    COUNT(*) AS joined_rows,
    SUM(a.quantity) AS joined_quantity,
    SUM(a.payment_actual) AS joined_payment_actual
FROM dme_cdm.dwd_ecom_order_detail_info_bu_temp_02 a
LEFT JOIN dme_cdm.dwd_ecom_order_detail_info_bu_temp_03 b
  ON a.shop_id = b.shop_id
LEFT JOIN dme_cdm.dwd_master_data_store_bu c
  ON a.store_code = c.store_code
 AND c.ds = '<AS_OF_DS_STORE>'
LEFT JOIN dme_cdm.dwd_master_data_customer_bu e
  ON a.customer_code = e.customer_code
 AND a.bu_2 = e.bu_2
 AND e.ds = '<AS_OF_DS_CUSTOMER>'
GROUP BY a.ds;
```

此 SQL 按 Statement 7 的 JOIN 条件复现，但要注意原语句的店铺 JOIN 是通过内联子查询先选 `store_code,store_name,chain_name,ec_store_code_tp`；如要复现完整投影，应保持完全相同子查询字段和条件。与 target 表按 `ds` 的 `COUNT(*)`、`SUM(quantity)`、`SUM(payment_actual)` 对照时，先确认 source `_temp_02` 与目标使用相同运行快照、写入成功、目标无并发重跑。结果差异需再定位 source/target 事件明细、未匹配、扇出、字段转换或合法过滤，不能直接判 FAIL。

## 7. 字段、金额、数量、状态和默认值任务

### 7.1 字段追踪任务

由 SQL owner 与字段 owner 按 70 个目标字段构建“源字段 → Statement/表达式 → 目标字段 → 单位/空值/状态 → 消费者”映射。先覆盖关键字段，再补全全部字段：

| 字段族 / 示例 | 当前 SQL 可见信息 | 必须确认 / 验证 |
|---|---|---|
| 订单标识：`order_no`、`sub_order_no`、`commodity_sku` | Statement 2 的 Maizhi 子查询按这些及更多字段分组；目标字段注释称订单/子订单/商品 SKU | 各来源字段映射等价性、事件关系、行标识合同 |
| 数量：`quantity` | TP 分支拷贝来源；Maizhi 表达式 sum 退货数量与基础数量 | 正负号、计量单位、退货是否净入 quantity、部分退款/取消 |
| 金额：`total_price_tax`、`total_price_untax`、`payment_actual`、`untax_payment_actual`、`base_sale_amt*`、`retail_*` | 原始 SQL 多个 `SUM`/乘法/CAST，两个来源计算并不完全同形 | 金额字段差异、税率比例/百分数、币种、舍入、含税/未税、退款/冲正与跨期口径 |
| 单价：`unit_price`、`unint_price_actual` | Maizhi `unint_price_actual` 按 `quantity=0` 返回 NULL，否则 `payment_actual/quantity` 后 CAST；其他来源字段映射需看 Statement 2 分支 | 单价究竟是商品标价还是实付均摊、数量为零/负数情形、精度容差 |
| 来源与类型：`data_source_code`、`data_source_name`、`data_type` | TP 分支有 `'TP POS'` 常量；另一个分支有来源字段；目标 Statement 投影这些值 | 来源枚举定义、跨来源重叠/优先级、`'常规'` 和“回流/常规”变更记录中的含义 |
| 门店/客户/地域属性 | 右表匹配缺失时多处回填 `Others` / `Others_Others`；`shop_id` 与 `shop_id_tp` 来源不同 | 未匹配、未知、不适用和真实“其他”是否可区分；权限字段用途/消费者；是否造成错误分组 |
| 状态与时间：`sub_order_state`、`create_time`、`ds` | Maizhi加工路径将部分字段置 NULL；部分路径用 `pay_time` 作为 ds；最终用 `a.ds` 分区 | 各来源缺省状态含义；业务发生时间/支付时间/处理分区；迟到和修正 |

### 7.2 数据诊断查询

查询只用于汇总观察，不会输出业务定义。执行前需批准数据访问、指定分区范围，并得到 SQL owner / 业务 owner 对切片维度的确认：

```sql
SELECT
    ds,
    data_source_code,
    data_type,
    COUNT(*) AS row_count,
    SUM(CASE WHEN order_no IS NULL OR TRIM(order_no) = '' THEN 1 ELSE 0 END)
        AS missing_order_no_rows,
    SUM(CASE WHEN sub_order_no IS NULL OR TRIM(sub_order_no) = '' THEN 1 ELSE 0 END)
        AS missing_sub_order_no_rows,
    SUM(CASE WHEN quantity IS NULL THEN 1 ELSE 0 END) AS null_quantity_rows,
    SUM(CASE WHEN payment_actual IS NULL THEN 1 ELSE 0 END) AS null_payment_rows,
    SUM(quantity) AS quantity_sum,
    SUM(payment_actual) AS payment_actual_sum,
    SUM(total_price_tax) AS total_price_tax_sum,
    SUM(total_price_untax) AS total_price_untax_sum,
    SUM(CASE WHEN shop_name IN ('Others', 'Others_Others') THEN 1 ELSE 0 END)
        AS rows_with_selected_fallback_values
FROM dme_cdm.dwd_ecom_order_detail_info_bu
WHERE ds = '<已批准分区值>'
GROUP BY ds, data_source_code, data_type;
```

`Others_Others` 当前映射到 `region_customer_permission`，并不是 `shop_name`；上面最后一个字段只检查 `shop_name` 两种字面值，此过滤并不代表检测所有 fallback。若要统计实际默认值，应按原 SQL 对每个投影字段单独检查，并查明 source 值/默认值的来源，不能把合法字符串 `Others` 自动当 NULL。对金额、数量需同时按来源、BU、状态、事件时间和业务批准的其他范围对账。

### 7.3 可能触发整改的口径证据

满足以下任一条件时，才将对应项目评为 FAIL 并进入方案评审：

- 已签认的指标口径明确规定公式/税/单位/退货方向，而复算 SQL 输出在代表性样例或批准阈值之外不一致；
- 同一事件在来源、临时表、目标或消费端的记录/金额/数量出现无法由批准的过滤、状态、舍入、时点规则解释的遗漏或重复；
- 默认值/空值合并违反已确认的数据合同，且证据证明将不同业务状态合并后影响下游筛选、分组、权限或指标；
- 类型/精度转换导致可复现截断、溢出或金额/数量错误。

若口径尚未确认，使用 `NEEDS_BUSINESS_CONFIRMATION`；口径确认而结果未跑，使用 `NEEDS_DATA_VALIDATION`。不要把发现 `NVL` 或多个金额列本身判作缺陷。

## 8. 时间、分区、迟到、重跑与历史更正

### 8.1 观察事实和未决问题

- Snapshot/Inventory 将目标列 `ds` 标记为 `STRING` partition，表 metadata 记录一个分区列。
- Statement 7 使用 `INSERT OVERWRITE ... PARTITION(ds)` 并把 `a.ds` 输出到分区；Statement 2 可见 TP 分支 `pay_time AS ds`、Maizhi分支 `bill_date AS ds`。
- 原始 SQL 其他语句读取输入表的 `MAX_PT` 分区。当前 SQL 文件没有说明 MAX_PT 是业务事件时间还是源表最近装载时间，也没有给出目标表实际调度参数/迟到回刷策略。

### 8.2 执行核对单

1. 数仓/业务 owner 定义目标 `ds` 是支付日、事件日、源业务日期还是装载分区；说明 TP `pay_time` 与 Maizhi `bill_date` 是否语义一致，时区及日界线是什么。
2. DataWorks 任务 owner 提供运行参数、目标实际分区列表、MAX_PT 输入分区日志、上游就绪时点及任务重跑记录。
3. 用同一组样例检查事件日期跨界、迟到到数、历史修正、重跑及最大分区回刷；确认任务 overwrite 的范围和覆盖/保留行为。
4. 对历史受影响分区做源→中间→目标事件/金额/数量对账，并检查目标分区是否漏写或覆盖非预期期间。
5. 业务 owner 签认可接受迟到 SLA、回刷窗口和更正规则。

### 8.3 分区检查模板（未执行）

```sql
SHOW PARTITIONS dme_cdm.dwd_ecom_order_detail_info_bu;

SELECT ds, COUNT(*) AS rows_in_partition
FROM dme_cdm.dwd_ecom_order_detail_info_bu
GROUP BY ds
ORDER BY ds;
```

MaxCompute 常用 `SHOW PARTITIONS` 形式与该表名/引擎匹配；本轮未在运行环境执行。执行前确认只读连接、权限和输出范围，完整分区列表不一定适合复制到公开工单。因为 `ds` 是 STRING，在确认具体编码为固定宽度可排序格式前，不用字符串 `BETWEEN` 代表日期范围；按实际分区值等值查询，或由任务 owner 明确经验证的日期映射。

## 9. Lineage、消费影响与职责

当前 [Coverage row](../../analysis/review/evidence-coverage.json) 对该表显示 `MATCH` / candidate layer `DWD`、Profiling `metadata_only`、SQL references 状态 `references_observed`；Review status `problem_candidate`。Lineage 是 SQL 表级引用。

### 9.1 Incoming 边（4）

| 上游表 | 证据 File / Statement | 对评审的用途 |
|---|---|---|
| `dme_cdm.dwd_ecom_order_detail_info_bu_temp_02` | File `504340559` / Statement `7` | 目标直接事实输入 |
| `dme_cdm.dwd_ecom_order_detail_info_bu_temp_03` | File `504340559` / Statement `7` | `shop_id` → `bu_3` 补充 |
| `dme_cdm.dwd_master_data_customer_bu` | File `504340559` / Statement `7` | 客户属性和权限字段来源 |
| `dme_cdm.dwd_master_data_store_bu` | File `504340559` / Statement `7` | 门店名称、平台等来源 |

完整源加工链另见同 File 的 Statements 2/4/6 和 References；上表仅是目标 INSERT Statement 7 的直接边。

### 9.2 Outgoing 边（27）

以下是当前 Lineage JSON 可追溯到的下游 SQL 表引用；不等于该表所有消费者或任务调度依赖。影响分析时需由下游 owner 核实运行 SQL、字段/指标使用和关键程度。

| 下游表 | File / Statement |
|---|---|
| `dme_cdm.dim_ec_douyin_product_mapping_temp_01` | `505061445` / 2 |
| `dme_cdm.dwd_ecom_order_return_info_bu` | `504340567` / 5 |
| `dme_ads.tb_controlling_reports_database_by_customer_mf_v2_tmp1` | `504347074` / 2 |
| `dme_ads.tb_ec_douyin_daily_report_order_analysis_temp_01` | `505059953` / 2 |
| `dme_ads.tb_ec_douyin_traded_detail_info` | `505071017` / 1 |
| `dme_ads.tb_ec_douyin_traded_sales_analysis_temp_01` | `505064877` / 2 |
| `dme_ads.tb_ecom_daily_report_traded_df_gmv_temp_01` | `504790737` / 2 |
| `dme_ads.tb_ecom_gtm_pl_cp_tmp0` | `505236743` / 4 |
| `dme_ads.tb_ecom_gtm_pl_cp_tmp00` | `505236743` / 2 |
| `dme_ads.tb_ecom_pos_data_source` | `505389037` / 1 |
| `dme_ads.tb_ecom_pos_sku_sales_summary_bu` | `504340799` / 1 |
| `dme_ads.tb_ecom_tm_daily_report_order_analysis_temp_01` | `504997049` / 2 |
| `dme_ads.tb_ecom_tm_store_order_detail_info` | `504993977` / 1 |
| `dme_ads.tb_ecom_tm_store_order_sales_analysis` | `504988183` / 1 |
| `dme_ads.tb_fcst_data_update_to_bts_v3_tmp03` | `505091491` / 6 |
| `dme_ads.tb_fcst_data_update_to_bts_v4_tmp03` | `505463994` / 6 |
| `dme_ads.tb_mediabb_pos_tracking_temp_01` | `505199473` / 2 |
| `dme_ads.tb_monitor_ecom_product_mapping_info` | `504340869` / 1 |
| `dme_ads.tb_monitor_ecom_store_pos_update` | `505523432` / 1 |
| `dme_ads.tb_monitor_ecom_store_product_others_ratio` | `505536883` / 1 |
| `dme_ads.tb_monitor_master_data_store_bu_loss_ecom_temp_01` | `505492202` / 2 |
| `dme_ads.tb_npd_pos_sku_sales_summary` | `504340895` / 1 |
| `dme_ads.tb_price_store_product_summary_data_v2` | `504340927` / 4 |
| `dme_ads.tb_sales_city_attack_summry_tmp0_pos` | `504340940` / 4 |
| `dme_ads.tb_sku_ecom_pos_tpm` | `504875455` / 1 |
| `dme_ads.tb_so_pos_data_bts_v3_tmp1` | `505318282` / 4 |

来源：[Table lineage](../../analysis/evidence/lineage/table-lineage.json)、[Coverage row](../../analysis/review/evidence-coverage.json)。边数为当前 Snapshot 的引用证据计数，不表示 27 个下游都运行成功、都直接消费所有 70 个字段或具有同一关键性。

## 10. 关联 Problem：去重、验证与处理建议

当前机器 JSON 对目标 Table Key 关联 8 个 Problem，状态均为 `candidate`。`priority` 和 classification 只是机器属性；集合有交叠，不应将 8 条当作 8 个已确认问题。Problem Evidence 中 SQL evidence 为 0，故每条需以下列的 SQL/Lineage/业务证据补齐后再裁决。

| Problem ID | 当前类型/机器属性 | 当前证据 | 合理替代解释 | 评审动作与 FAIL 触发 |
|---|---|---|---|---|
| `problem_0327` | `GRAIN_PROBLEM` / P0 / `candidate` / classification `confirmed_conflict` | `model_finding_1325`；4 个 Grain Candidate，10 条 Problem evidence；机器描述同表有 4 个不同候选键 | 4 组候选可能是同一事件的替代标识、来源差异、描述字段/商品行展开或算法候选；状态词 `confirmed_conflict` 不是人工 confirmed | 先确认事件与 grain，再按第 5 节验证候选键。仅当已签认的一行合同与实际记录/SQL 不一致，且影响可复现，才 FAIL；否则待确认/验证 |
| `problem_0877` | `MODEL_DUPLICATION` / P1 / `candidate` / `duplication_candidate` | 六表集合：非 BU 订单详情、BU 目标、mid、mid_temp_01、temp_01、temp_02；15 个 Finding（含 `model_finding_2020`–`2024` 与字段重合信号） | mid/temp/target 可是不同变换阶段；BU 与非 BU、TP/迈志来源或历史加工范围可能有实质差异 | 对六表来源、行粒度、过滤/计算、生命周期和消费者做矩阵比对。只有语义范围相同且逻辑重复导致明确维护/消费/指标损害才 FAIL；否则保留并补职责文档 |
| `problem_0992` | `MODEL_DUPLICATION` / P1 / `candidate` / `technical_copy_candidate` | Finding `model_finding_0588`；候选签名 `customer_code+order_no`，5 表 | 候选键由机器信号推出；表可能因处理阶段/来源/范围不同而共存 | 与 0993/1000/1003 作为一组去重评审；核对各表 SQL/消费。只有已确认同义且重复链造成损害时 FAIL |
| `problem_0993` | `MODEL_DUPLICATION` / P1 / `candidate` / `technical_copy_candidate` | Finding `model_finding_0591`；候选签名 `customer_code+sub_order_no`，5 表 | 子订单键不一定表示同一事件 grain；候选仍非业务键事实 | 同上；不得把键字符串相似当作复制证明 |
| `problem_1000` | `MODEL_DUPLICATION` / P1 / `candidate` / `technical_copy_candidate` | Finding `model_finding_0609`；候选签名 `order_no`；Finding 描述涉及 12 个 Fact Candidate | 订单号可能跨商品、子单、来源或重复业务事件 | 同上；以批准的 source/BU/事件/时态范围做逐记录对账 |
| `problem_1003` | `MODEL_DUPLICATION` / P1 / `candidate` / `technical_copy_candidate` | Finding `model_finding_0616`；候选签名 `sub_order_no`；Finding 描述涉及 11 个 Fact Candidate | 子订单号可能跨来源/订单或含多个明细事件 | 同上 |
| `problem_1159` | `MODEL_SELECTION_AMBIGUITY` / P1 / `candidate` | `process_candidate_004` 范围 151 表、298 Findings、455 evidence；覆盖目标表但聚合宽 | 一个候选 Process 聚合许多业务域/加工层表；可能是候选机制范围宽而非一个选择问题 | 不以该宽问题直接整改。拆出含目标表的具体相邻表簇，补 SQL 和下游使用；只有存在已确认无法选择权威契约并造成影响的子问题才 FAIL |
| `problem_1169` | `PROCESS_MODEL_ALIGNMENT` / P3 / `candidate` | Problem 范围 491 表、1 Finding、494 evidence；目标表是成员 | Process 候选范围极宽，目标成员关系不能证明目标表本身失配 | 仅当业务确认该过程范围后，定义该表在过程中的责任并核实消费；缺少具体合同或证据时维持 `INSUFFICIENT_EVIDENCE` |

### 10.1 处理顺序与去重策略

1. 将 `problem_0327` 作为**业务粒度问题登记项**，不要把 4 个候选键或 P0 自动升级为 4 个缺陷。
2. 将 `problem_0877` 作为订单加工链**模型职责/重叠主评审组**；对比 6 张表的语义和实际消费者。
3. 将 `problem_0992`、`0993`、`1000`、`1003` 关联为该主评审组的**四条键候选证据**，先统一确定事件/键再分别检查；不要重复开四条重复建模改造。
4. 将 `problem_1159`、`1169` 标为**范围过宽、需拆解**，不得将 151/491 表整组直接派发模型整改。
5. 若以后一个已验证根因覆盖多 Problem，维护一条主评审/整改条目，逐 ID 保留关联关系、各自证据和人工裁决；不得删除或合并机器原记录以隐藏追溯。

问题 FAIL 的通用门槛：明确适用要求 → 业务 owner 确认定义/例外 → 技术/数据证据可复现地违反定义 → 影响路径确认。否则以相应状态保留未决。

## 11. 可执行评审任务清单

负责人目前只确定角色，姓名、截止日期和实际数据权限需由项目负责人填写，不在本底稿中臆造。

| Task | 输入/动作 | 输出记录 | 责任角色 | 通过 / FAIL / 暂缓 |
|---|---|---|---|---|
| T1 业务事件合同 | 回答第 5.2 节；记录订单/子单/商品/支付/退款事件关系、发生时点、TP/迈志范围、例外 | 业务确认版本、签字人、日期、事件定义和允许重复规则 | 电商业务流程 owner、源系统 owner | 未确认 = `NEEDS_BUSINESS_CONFIRMATION`；不能 PASS/FAIL |
| T2 Grain / Key | 选定 scope 与样例分区；执行第 5.3 的重复、缺失查询；按来源/BU/状态/时间/更正切片 | 实际 SQL、运行时点、分区、键冲突样例、业务解释 | 数据工程师、数据 QA；键语义由业务 owner | 合同允许的例外归档；合同明确唯一性被违反且非例外才 FAIL |
| T3 目标 Statement 7 joins | 依次跑 temp_03、store、customer 键重复、匹配覆盖、键组级扇出；复现完整生产过滤 | 三个直接 JOIN 的右键基数及 unmatched/multiple 统计、影响样例 | 数据工程师、主数据 owner | 按合同证明非预期多匹配/错配且影响目标才 FAIL |
| T4 上游 Statements 2/4 joins | 验证客户、area、city、region、product、store mapping 六个关系；记录每个运行时 MAX_PT | 六个上游 JOIN 结果与 `UNION ALL` 来源解释 | SQL owner、主数据/地理 mapping owner、源系统 owner | 各项独立裁决；语义不清标业务确认 |
| T5 数量金额口径 | 由业务/财务签认定义；对正常、退货/退款/取消/更正、零量/零额样例逐步复算并与来源对账 | 指标定义、原始与目标差异明细、批准容差 | 财务/指标 owner、电商业务 owner、数据工程师 | 已批准公式不符且可复现才 FAIL；无定义先确认 |
| T6 时间/分区/重跑 | 查 `SHOW PARTITIONS`、任务调度/参数/运行日志；验证迟到、重跑、回刷和历史更正 | 分区映射、MAX_PT 参数、覆盖窗口与幂等/历史对账 | DataWorks 任务 owner、业务 owner、数据平台 owner | 未确认时间语义或无运行证据时保持待确认/待验证 |
| T7 模型职责与下游 | 对照 6 表候选组、27 outgoing SQL refs；访谈关键消费者并核实实际使用字段/指标 | 语义对比表、权威性/消费合同、受影响资产清单 | 数仓架构师、模型 owner、ADS/报表 owner | 只有确认等价且重复造成具体损害才支持合并 |
| T8 评审裁决与风险 | 按要求逐维度填写状态、风险等级、置信度、未决事项和暂行控制 | 有责任人/日期的评估记录与整改决策 | 评审主持人、业务 owner、数仓架构师、治理 | 机器优先级独立于业务风险；未决风险有 deadline |

## 12. 整改触发、选项和验收门槛

| 证实情形 | 可考虑的行动 | 整改前风险 / 影响范围 | 必须验收的证据 |
|---|---|---|---|
| 生产 SQL 在同一应唯一的事实键上将右表多行展开，导致重复事实/计量 | 修 JOIN 条件、有效分区/时态条件、主数据唯一性治理或先聚合/选版本 | 目标表行数及门店/客户属性、所有下游金额/数量指标受影响；评估历史分区 | 修复前后每事实匹配数、0/1/multi 分布；修复后目标 key合同检查、金额/数量和分区对账；27 个 downstream refs 中关键消费者回归 |
| 业务确认同表承载互斥且未显式区分的粒度，造成消费误算 | 经架构审批拆分模型或显式区分事件/类型/粒度并更新消费合同 | 70 字段使用者迁移、历史事件重新分配、跨来源和下游报表兼容 | 新模型每行合同；来源覆盖/无意遗漏与重复；历史回刷；下游逐一签收和回滚计划 |
| 金额/数量表达式与已批准公式不符 | 修 SQL 的计算/状态/税率/NULL处理；必要时版本化指标定义 | 历史报表/财务指标/所有依赖者，需确定影响起始期 | 代表场景独立复算；按来源、状态、税/币种切片的历史重算和财务对账；容差事先批准 |
| `UNION ALL` 将重叠来源事件重复计入，且业务确认应去重/优先级处理 | 修复来源边界、源优先级、业务事件身份或去重规则 | 两来源历史覆盖期、状态/时点差异、可能的合法双源场景 | 业务确认的范围；事件级来源交叉表；重复分类解释；变更前后数量/金额历史对账 |
| `ds`/overwrite 范围导致迟到/更正数据遗漏或误覆盖 | 调整分区策略、回刷窗口或增量/幂等逻辑 | 分区回刷成本、历史改写、下游时效 | 迟到/重跑/更正案例；目标分区变化记录；源目标对账；下游延迟与恢复验证 |
| 结构与业务合同相符，问题只是证据/监控/职责说明缺失 | 保留模型，补数据字典、质量监控、血缘/消费者目录和 owner | 维护遗漏、文档漂移 | 文档/owner/version、生效时间；监控触发演练；关键下游确认 |
| 业务定义/数据访问仍不可得 | 暂不结构整改；设补证任务、责任人、期限和临时风险控制 | 暴露期和潜在核心指标影响必须记录，不能记为 PASS | 未决项有负责人/期限；按风险做临时监控/止损；期限到达时重新评估 |

任何 SQL/模型整改上线前，需经方案评审；若变更 grain、key、JOIN、字段口径、历史分区，按[规范 §10.1](../DWD_MODEL_QUALITY_AND_REMEDIATION_STANDARD.md)执行回刷、对账和下游回归。实现完成不等于关闭。

## 13. 工作底稿状态表与责任确认

| 维度 | 当前状态（本底稿初始评估） | 当前已知证据 | 未决责任/行动 |
|---|---|---|---|
| Table identity / 列结构 | **Observed；技术身份可追溯** | Workspace 466337、70 列、1 个 `ds` 分区列 | DDL owner 确认线上定义与 Snapshot 一致 |
| 业务对象/过程/权威用途 | `NEEDS_BUSINESS_CONFIRMATION` | 注释、Process/Fact 候选、SQL 文本 | 电商业务 owner 确认正式过程、来源和消费者 |
| 一行语义/Grain | `NEEDS_BUSINESS_CONFIRMATION` + `NEEDS_DATA_VALIDATION` | GROUP BY、UNION、4 Grain Candidates、Problem 0327 | 确认 event contract 后执行分区/来源/状态验证 |
| 候选键/唯一性 | `NEEDS_BUSINESS_CONFIRMATION` + `NEEDS_DATA_VALIDATION` | 四组候选键字段存在且均为 STRING | 业务确认 scope/例外；数据 QA 执行重复/缺失检查 |
| JOIN 基数/扇出 | `NEEDS_DATA_VALIDATION` | 9 个 JOIN 的实际 key/filter 可追踪 | 数据工程/MDM owner 执行 join key、覆盖及实际结果对比 |
| 字段/金额/数量语义 | `NEEDS_BUSINESS_CONFIRMATION` | Schema 注释与 SQL 表达式可见 | 财务/指标 owner 签认公式/单位/方向，再做逐样例对账 |
| `ds` / 历史处理 | `NEEDS_BUSINESS_CONFIRMATION` + `NEEDS_DATA_VALIDATION` | STRING 分区；部分 SQL 投影 pay_time/bill_date；overwrite | 业务确认时点；DataWorks owner 提供运行参数/迟到回刷证据 |
| 重复建模与模型职责 | `NEEDS_BUSINESS_CONFIRMATION` | 机器 Finding/Problem 和相似表候选 | 逐表 SQL/用途/消费者核对后决定保留、补文档或整改 |
| 上下游完整性 | `INSUFFICIENT_EVIDENCE`（对调度依赖和完整消费者清单） | SQL Table Lineage 当前记 4 incoming/27 outgoing | 调度/消费 owner 核实任务依赖、重要性、字段和指标传播 |
| 质量监控/运行控制 | `INSUFFICIENT_EVIDENCE` | 当前 Profiling metadata-only | QA/平台 owner 提供规则、告警、运行 SLA、故障处理记录 |

**当前正式结论**：不作总体 PASS 或 FAIL。该表是有可追溯 SQL / 表级 Lineage 的评审对象，存在多个需优先核查的机器候选；未验证的业务 grain、键、JOIN、指标和时间维度均应保持未决。未达到设计批准门槛。

### 责任人填写区

| 角色 | 姓名 | 确认事项 / 交付 | 目标日期 | 签认/链接 |
|---|---|---|---|---|
| 电商业务过程 owner | 待指定 | 事件/粒度/来源范围/例外 | 待指定 |  |
| 财务/指标 owner | 待指定 | 金额、数量、退货/退款口径及容差 | 待指定 |  |
| DataWorks / SQL owner | 待指定 | 运行时分区、SQL版本、重跑/回刷策略 | 待指定 |  |
| MDM / mapping owner | 待指定 | 门店、客户、产品、地理键及有效时态 | 待指定 |  |
| DWD 模型 owner / 架构师 | 待指定 | 责任边界、候选模型比较、设计评审 | 待指定 |  |
| 数据 QA / 验证执行人 | 待指定 | 只读查询、对账、结果复核 | 待指定 |  |
| ADS/报表消费者 owner | 待指定 | 关键字段/指标依赖与回归签收 | 待指定 |  |
| 评审主持人 / 治理 | 待指定 | 记录状态、风险、结论、整改关闭 | 待指定 |  |

## 14. 执行 SQL 前置与风险控制

1. **只读连接**：使用获批只读/隔离环境；先验证查询不会写入或触发 UDF 外部副作用。本文所有 SQL 仅为 SELECT / SHOW。
2. **固定快照**：记录所用源/临时/主数据分区值、目标分区、作业运行 ID 和查询时间，避免用不同运行的 `_temp_02` 与 target 结果对账。
3. **确认分区编码**：运行 `SHOW PARTITIONS` 并确认 `ds` 实际取值格式；未经确认不使用字符串范围过滤。
4. **控制扫描量**：先选业务批准的少数代表性分区，核对执行计划/扫描量；扩展到全历史前审批成本和资源。
5. **验证 SQL 方言**：原 SQL 是 MaxCompute 风格，包含 `${dme_cdm}` 参数与 `MAX_PT`；模板改为完整 Project 表名和 `<...>` 占位符。正式执行前用只读控制台验证 `WITH`、`CASE`、`TRIM`、`SUM` 及分区筛选语法。若任一写法不被当前引擎接受，停止并改为经验证的等价 SELECT，不保留“已执行”说法。
6. **结果治理**：只保存汇总、脱敏样例和 query ID；敏感业务数据按最小必要字段访问，不把明细值写入此底稿。
7. **签认后才判定**：未确认键/事件定义、容差和合法多值之前，SQL 查询产出的重复/差异是 observed evidence，不自动成为 FAIL。

## 15. 完成前关闭清单

- [ ] 业务 owner 已确认过程、事件、一行语义、来源/状态/更正例外并记录版本。
- [ ] 四个候选键逐项已确认“适用/不适用/需加范围”并已在获批分区完成唯一性与缺失检查。
- [ ] 9 个 JOIN 均已核对生产右侧分区/过滤、预期基数、未匹配和多匹配。
- [ ] Statement 2、4、6、7 的 SQL 转换、过滤、GROUP BY、UNION ALL、fallback 已与合同核对。
- [ ] 数量/金额/退货退款公式按代表性数据和批准口径完成源到目标对账。
- [ ] `ds` 语义、迟到、overwrite、重跑、回刷、历史更正和幂等性有实际运行证据。
- [ ] 4 incoming / 27 outgoing SQL Lineage 已与调度依赖、关键消费者和字段/指标用法补充核对。
- [ ] Problem 去重完成；机器 `candidate` / `review_required` / classification 未混入评估状态。
- [ ] 评估每项有 PASS/FAIL/NEEDS_BUSINESS_CONFIRMATION/NEEDS_DATA_VALIDATION/INSUFFICIENT_EVIDENCE/NOT_APPLICABLE 及证据/负责人。
- [ ] 若触发整改，方案有影响范围、历史回刷、对账阈值、下游回归、回滚、业务验收人和日期。
- [ ] 业务 owner、数据 owner、QA、架构及受影响消费者完成签认。
