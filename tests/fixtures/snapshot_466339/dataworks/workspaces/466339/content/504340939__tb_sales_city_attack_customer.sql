---所属主题: City attack 定制化取数
--功能描述: 供City attack数据表 by客户(抽样城市的部分pos)
--创建者: mass
--创建日期: 2023-12-04
--修改日期  修改人 修改内容
--yyyymmdd  name  comment
-- 20240105 mass  下掉依赖：tb_controlling_reports_database_by_customer_mf
-- 20240129 mass  调整ecom退货，DT others逻辑,添加MPD渠道数据
-- 20240425 mass  调整BC 间供合同比例ka关联；屈臣氏云仓23年数据用24年基价分摊到城市；MPD 渠道城市占比、monthly 销额新增取数逻辑；新增省份字段
-- 20240524 mass  调整BC线下费比逻辑:202405前后计算逻辑不同
-- 20240718 mass 调整屈臣氏云仓23年数据用24年基价分摊逻辑,新增字段wats_base_amt_online_city_rate、wats_gmv_online_city_rate
-- 20240719 mass  处理单月展示最大pos经销名称逻辑调整（针对同一个ka既有直供又有间供：大润发华东20240315转直供）
-- 20250215 mass  DT客户转MPD需求调整，2025年之后剔除零售线NKA间供+LKA和DT Others分类数据
-- 20250310   xueyang 大润发拆分通过逻辑处理保障原有字段存放原始值
-- 20251224  mass  调整ecom已有门店id和名称信息为MDM标准数据
--20260127  xueyang  KA主数据调整，KA信息走主数据，统一KA名称，并新增KA英文名称
--********************************************************************--

-- 零售线 建统一维表 
drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp0 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp0 as
select
   b.months
   ,b.years
   ,a.idh
   ,a.customer_type
   ,a.bu_1
   ,a.bu_2
from (
  select
    if(upper(customer_idh_snapshot)='CRV-TESCO','Tesco',customer_idh_snapshot) as idh
    ,customer_type_snapshot as customer_type
    ,bu_1
    ,bu_2
    ,substr(month,1,4) as years
  from dme_ads.tb_controlling_reports_database_by_customer_mf
   where UPPER(is_not_py)='N'
   and UPPER(slow_moving)='ALL'
   and upper(bu_2)='BEAUTY CARE'
   and ds=max_pt('dme_ads.tb_controlling_reports_database_by_customer_mf')
  group by if(upper(customer_idh_snapshot)='CRV-TESCO','Tesco',customer_idh_snapshot)
      ,customer_type_snapshot,bu_1 ,bu_2,substr(month,1,4)
 ) a
 inner join (
     select month_id as months,substr(month_id,1,4) as years
     from ${dme_cdm}.dim_day
     where month_id >='202001' and month_id <='${bizmonth}'
     group by month_id,substr(month_id,1,4)
 ) b
 on a.years=b.years
;

-- 零售线 建统一维表 
drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp1 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp1 as
select
   b.months
   ,b.years
   ,a.idh
   ,a.customer_type
   ,a.bu_1
   ,a.bu_2
from (
  select
    if(upper(customer_idh_snapshot)='CRV-TESCO','Tesco',customer_idh_snapshot) as idh
    ,customer_type_snapshot as customer_type
    ,bu_1
    ,bu_2
    ,substr(month,1,4) as years
  from dme_ads.tb_controlling_reports_database_by_customer_mf_v2
   where UPPER(is_not_py)='N'
   and UPPER(slow_moving)='ALL'
   and upper(bu_2) in ('BEAUTY CARE','LAUNDRY')
   and ds=max_pt('dme_ads.tb_controlling_reports_database_by_customer_mf_v2')
  group by if(upper(customer_idh_snapshot)='CRV-TESCO','Tesco',customer_idh_snapshot)
       ,customer_type_snapshot,bu_1 ,bu_2,substr(month,1,4)
 ) a
 inner join (
     select month_id as months,substr(month_id,1,4) as years
     from ${dme_cdm}.dim_day
     where month_id >='202001' and month_id <='${bizmonth}'
     group by month_id,substr(month_id,1,4)
 ) b
 on a.years=b.years
;

-- 专业线 建统一维表
drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp1_01 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp1_01 as
select
   b.months
   ,b.years
   ,a.customer_code
   ,a.channel_hierarchy_1
   ,a.customer_id
   ,a.bu_1
   ,a.bu_2
from (
  select distinct
    years
    ,customer_code
    ,channel_hierarchy_1
    ,case when bu_2='SKP' AND upper(channel_hierarchy_1) IN ('NKA','SELECTIVE RETAILER') then
         case when customer_group in ('Auchan','Tesco','Carrefour','DIA','HomeClub','LOTUS','Mannings','NGS','RT','Sams','Wanjia','Watsons','SaSa') then customer_group
              when customer_code in ('129019')     then 'Metro'     -- 麦德龙
              when customer_code in ('703429','708859','2509858') then 'Sams'
           else customer_code  end
        when bu_2='SKP' and customer_code in ('129019')     then 'Metro'     -- 麦德龙
        when bu_2='SKP' and customer_code in ('703429','708859','2509858') then 'Sams'
      else customer_code end as customer_id
    ,bu_1
    ,bu_2
  from ${dme_cdm}.dwd_sap_customer_summary_bu
  where ds =max_pt('${dme_cdm}.dwd_sap_customer_summary_bu')
  and bu_2='SKP'
 ) a
 inner join (
     select month_id as months,substr(month_id,1,4) as years
     from ${dme_cdm}.dim_day
     where month_id >='202001' and month_id <='${bizmonth}'
     group by month_id,substr(month_id,1,4)
 ) b
 on a.years=b.years
;

-- YTD 指标
drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp2 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp2 as
select a.*
from(
 select
    t.months
   ,t.years
   ,t.customer_idh
   ,t.channel
   ,t.bu_1
   ,t.bu_2
   ,t.data_type
   ,sum(t.NGS              ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type,months order by months asc) as NGS_MONTHLY               -- 月的 Net_Gross_Sales，净销售总额
   ,sum(t.rebate           ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as rebate            -- YTD 返利
   ,sum(t.CA               ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as CA                -- YTD 价差
   ,sum(t.PLD              ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as PLD               -- YTD Price_Listing_Discount，固定价格折扣
   ,sum(t.PPD              ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as PPD               -- YTD Price_Promotion_Discount，促销价格折扣
   ,sum(t.FG               ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as FG                -- YTD Free_Goods，赠品金额
   ,sum(t.GES              ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as GES               -- YTD 集团外毛销售额
   ,sum(t.NGS              ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as NGS               -- YTD Net_Gross_Sales，净销售总额
   ,sum(t.logistic_fee     ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as logistic_fee      -- YTD 物流费
   ,sum(t.listing_fee      ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as listing_fee       -- YTD 进场费
   ,sum(t.nka_expense      ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as nka_expense       -- YTD NKA费用，如气柱费、信息费等
   ,sum(t.2nd_dis_dm_others) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as 2nd_dis_dm_others -- YTD 二次陈列费+海报费+其他
   ,sum(t.l10_commission   ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as l10_commission    -- YTD Commission（佣金）
   ,sum(t.l11_t_w          ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as l11_t_w           -- YTD Transport/Warehouse，运输和仓库管理相关费用
   ,sum(t.l14_cog          ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as l14_cog           -- YTD 即Total_Manufacturing_Cost，制造类费用
   ,sum(t.l16_umc          ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as l16_umc           -- YTD 额外运营费用
   ,sum(t.l17_total        ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as l17_total         -- YTD 用于Controlling调整FCST的L17费用
   ,sum(t.l17_nka_tm_o2o   ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as l17_nka_tm_o2o    -- YTD L17细项
   ,sum(t.l17_channel      ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as l17_channel       -- YTD l17_po+l17_Manual
   ,sum(t.l17_py           ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as l17_py            -- YTD l17_py
   ,sum(t.l17_ba           ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as l17_ba            -- YTD L17细项
   ,sum(t.l17_mkt          ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as l17_mkt           -- YTD L17细项
   ,sum(t.l17_digital      ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as l17_digital       -- YTD L17细项
   ,sum(t.lka_contract_fee ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as lka_contract_fee  -- Lka合同返利
   ,sum(t.indirect_rebate  ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as indirect_rebate   -- 间供返利
   ,sum(t.retailer_rebate  ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as retailer_rebate   -- 间供返利
   ,sum(t.oos              ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as oos  
   ,sum(t.ka_expense       ) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as ka_expense 
   ,sum(t.promotion_activists) over(partition by t.years,t.customer_idh,t.channel,t.bu_1,t.bu_2,t.data_type order by months asc) as promotion_activists 
 from (
  -- 202405月之前取新逻辑 
  select
    a.months          as months
    ,a.years          as years
    ,case when a.months<='202307' and a.idh='1967491' then '2925773'
          when a.idh like 'RT%' then 'RT'  
          else a.idh end  as customer_idh
    ,a.customer_type  as channel
  --  ,case when a.months<='202307' and a.idh='1967491' then '北京沃亿商业管理有限公司'
  --    else a.customer_name end  as customer_name
    ,a.bu_1           as bu_1
    ,a.bu_2           as bu_2
    ,sum(if(b.value_type='rebate'           ,nvl(b.index_value ,0),null)) as rebate            -- 返利
    ,sum(if(b.value_type='ca'               ,nvl(b.index_value ,0),null)) as CA                -- 价差
    ,sum(if(b.value_type='pld'              ,nvl(b.index_value ,0),null)) as PLD               -- Price_Listing_Discount，固定价格折扣
    ,sum(if(b.value_type='ppd'              ,nvl(b.index_value ,0),null)) as PPD               -- Price_Promotion_Discount，促销价格折扣
    ,sum(if(b.value_type='fg'               ,nvl(b.index_value ,0),null)) as FG                -- Free_Goods，赠品金额
    ,sum(if(b.value_type='ges'              ,nvl(b.index_value ,0),null)) as GES               -- 集团外毛销售额
    ,sum(if(b.value_type='ngs'              ,nvl(b.index_value ,0),null)) as NGS               -- Net_Gross_Sales，净销售总额
    ,sum(if(b.value_type='logistic_fee'     ,nvl(b.index_value ,0),null)) as logistic_fee      -- 物流费
    ,sum(if(b.value_type='listing_fee'      ,nvl(b.index_value ,0),null)) as listing_fee       -- 进场费
    ,sum(if(b.value_type='nka_expense'      ,nvl(b.index_value ,0),null)) as nka_expense       -- NKA费用，如气柱费、信息费等
    ,sum(if(b.value_type='2nd_dis_dm_others',nvl(b.index_value ,0),null)) as 2nd_dis_dm_others -- 二次陈列费+海报费+其他
    ,sum(if(b.value_type='l10_commission'   ,nvl(b.index_value ,0),null)) as l10_commission    -- Commission（佣金）
    ,sum(if(b.value_type='l11_t_w'          ,nvl(b.index_value ,0),null)) as l11_t_w           -- Transport/Warehouse，运输和仓库管理相关费用
    ,sum(if(b.value_type='l14_cog'          ,nvl(b.index_value ,0),null)) as l14_cog           -- 即Total_Manufacturing_Cost，制造类费用
    ,sum(if(b.value_type='l16_umc'          ,nvl(b.index_value ,0),null)) as l16_umc           -- 额外运营费用
    ,sum(if(b.value_type='l17_total'        ,nvl(b.index_value ,0),null)) as l17_total         -- 用于Controlling调整FCST的L17费用
    ,sum(if(b.value_type='l17_nka_tm_o2o'   ,nvl(b.index_value ,0),null)) as l17_nka_tm_o2o    -- L17细项
    ,sum(if(b.value_type='l17_nka_fix'      ,nvl(b.index_value ,0),null)) as l17_channel       -- l17_po+l17_Manual
    ,sum(if(b.value_type='py_release'       ,nvl(b.index_value ,0),null)) as l17_py            -- l17_py
    ,sum(if(b.value_type='l17_ba'           ,nvl(b.index_value ,0),null)) as l17_ba            -- L17细项
    ,sum(if(b.value_type='l17_mkt'          ,nvl(b.index_value ,0),null)) as l17_mkt           -- L17细项
    ,sum(if(b.value_type='l17_digital'      ,nvl(b.index_value ,0),null)) as l17_digital       -- L17细项
    ,sum(if(b.value_type='lka_contract_fee' ,nvl(b.index_value ,0),null)) as lka_contract_fee  -- Lka合同返利
    ,sum(if(b.value_type='indirect_rebate'  ,nvl(b.index_value ,0),null)) as indirect_rebate   -- 间供返利
    ,null as retailer_rebate   -- 间供返利
    ,null as oos   
    ,null as ka_expense  
    ,null as promotion_activists
    ,'old' as data_type
  from ${dme_ads}.tb_sales_city_attack_customer_tmp0 a
  left join dme_ads.tb_controlling_reports_database_by_customer_mf b
    on nvl(a.idh          ,'')=if(upper(b.customer_idh_snapshot)='CRV-TESCO','Tesco',nvl(b.customer_idh_snapshot,''))
   and nvl(a.customer_type,'')=nvl(b.customer_type_snapshot ,'')
   --and nvl(a.customer_name,'')=nvl(b.customer_name ,'')
   and nvl(a.bu_1         ,'')=nvl(b.bu_1          ,'')
   and nvl(a.bu_2         ,'')=nvl(b.bu_2          ,'')
   and nvl(a.months       ,'')=nvl(b.month         ,'')
   and UPPER(b.is_not_py)='N'
   and UPPER(b.slow_moving)='ALL'
   and b.ds=max_pt('dme_ads.tb_controlling_reports_database_by_customer_mf')
  group by a.months
     ,a.years
     ,case when a.months<='202307' and a.idh='1967491' then '2925773'
          when a.idh like 'RT%' then 'RT'  
       else a.idh end
     ,a.customer_type
     ,a.bu_1
     ,a.bu_2
   union all  
   -- 202405月之后取新逻辑 
   select
     a.months          as months
     ,a.years          as years
     ,case when a.months<='202307' and a.idh='1967491' then '2925773'
          when a.idh like 'RT%' then 'RT'  
       else a.idh end  as customer_idh
     ,a.customer_type  as channel
   --  ,case when a.months<='202307' and a.idh='1967491' then '北京沃亿商业管理有限公司'
   --    else a.customer_name end  as customer_name
     ,a.bu_1           as bu_1
     ,a.bu_2           as bu_2
     ,sum(if(b.value_type='rebate'           ,nvl(b.index_value ,0),null)) as rebate            -- 返利
     ,sum(if(b.value_type='ca'               ,nvl(b.index_value ,0),null)) as CA                -- 价差
     ,sum(if(b.value_type='pld'              ,nvl(b.index_value ,0),null)) as PLD               -- Price_Listing_Discount，固定价格折扣
     ,sum(if(b.value_type='ppd'              ,nvl(b.index_value ,0),null)) as PPD               -- Price_Promotion_Discount，促销价格折扣
     ,sum(if(b.value_type='fg'               ,nvl(b.index_value ,0),null)) as FG                -- Free_Goods，赠品金额
     ,sum(if(b.value_type='ges'              ,nvl(b.index_value ,0),null)) as GES               -- 集团外毛销售额
     ,sum(if(b.value_type='ngs'              ,nvl(b.index_value ,0),null)) as NGS               -- Net_Gross_Sales，净销售总额
     ,sum(if(b.value_type='logistic_fee'     ,nvl(b.index_value ,0),null)) as logistic_fee      -- 物流费
     ,sum(if(b.value_type='listing_fee'      ,nvl(b.index_value ,0),null)) as listing_fee       -- 进场费
     ,sum(if(b.value_type='nka_expense'      ,nvl(b.index_value ,0),null)) as nka_expense       -- NKA费用，如气柱费、信息费等
     ,sum(if(b.value_type='2nd_dis_dm_others',nvl(b.index_value ,0),null)) as 2nd_dis_dm_others -- 二次陈列费+海报费+其他
     ,sum(if(b.value_type='l10_commission'   ,nvl(b.index_value ,0),null)) as l10_commission    -- Commission（佣金）
     ,sum(if(b.value_type='l11_t_w'          ,nvl(b.index_value ,0),null)) as l11_t_w           -- Transport/Warehouse，运输和仓库管理相关费用
     ,sum(if(b.value_type='l14_cog'          ,nvl(b.index_value ,0),null)) as l14_cog           -- 即Total_Manufacturing_Cost，制造类费用
     ,sum(if(b.value_type='l16_umc'          ,nvl(b.index_value ,0),null)) as l16_umc           -- 额外运营费用
     ,sum(if(b.value_type='l17_total'        ,nvl(b.index_value ,0),null)) as l17_total         -- 用于Controlling调整FCST的L17费用
     ,sum(if(b.value_type='l17_nka_tm_o2o'   ,nvl(b.index_value ,0),null)) as l17_nka_tm_o2o    -- L17细项
     ,sum(if(b.value_type='l17_nka_fix'      ,nvl(b.index_value ,0),null)) as l17_channel       -- l17_po+l17_Manual
     ,sum(if(b.value_type='py_release'       ,nvl(b.index_value ,0),null)) as l17_py            -- l17_py
     ,sum(if(b.value_type='l17_ba'           ,nvl(b.index_value ,0),null)) as l17_ba            -- L17细项
     ,sum(if(b.value_type='l17_mkt'          ,nvl(b.index_value ,0),null)) as l17_mkt           -- L17细项
     ,sum(if(b.value_type='l17_digital'      ,nvl(b.index_value ,0),null)) as l17_digital       -- L17细项
     ,sum(if(b.value_type='lka_contract_fee' ,nvl(b.index_value ,0),null)) as lka_contract_fee  -- Lka合同返利
     ,sum(if(b.value_type='indirect_rebate'  ,nvl(b.index_value ,0),null)) as indirect_rebate   -- 间供返利
     ,sum(if(b.value_type='retailer_rebate'  ,nvl(b.index_value ,0),null)) as retailer_rebate   -- 间供返利
     ,sum(if(b.value_type='oos'              ,nvl(b.index_value ,0),null)) as oos   
     ,sum(if(b.value_type='ka_expense'       ,nvl(b.index_value ,0),null)) as ka_expense  
     ,sum(if(b.value_type='promotion_activists',nvl(b.index_value ,0),null)) as promotion_activists
     ,'new' as data_type
  from ${dme_ads}.tb_sales_city_attack_customer_tmp1 a
  left join dme_ads.tb_controlling_reports_database_by_customer_mf_v2 b
    on nvl(a.idh          ,'')=if(upper(b.customer_idh_snapshot)='CRV-TESCO','Tesco',nvl(b.customer_idh_snapshot,''))
   and nvl(a.customer_type,'')=nvl(b.customer_type_snapshot ,'')
   --and nvl(a.customer_name,'')=nvl(b.customer_name ,'')
   and nvl(a.bu_1         ,'')=nvl(b.bu_1          ,'')
   and nvl(a.bu_2         ,'')=nvl(b.bu_2          ,'')
   and nvl(a.months       ,'')=nvl(b.month         ,'')
   and UPPER(b.is_not_py)='N'
   and UPPER(b.slow_moving)='ALL'
   and b.ds=max_pt('dme_ads.tb_controlling_reports_database_by_customer_mf_v2')
  group by a.months
     ,a.years
     ,case when a.months<='202307' and a.idh='1967491' then '2925773'
           when a.idh like 'RT%' then 'RT'  
      else a.idh end
     ,a.customer_type
     ,a.bu_1
     ,a.bu_2
  
   union all
   -- 合并专业线SKP数据
   select
     a.months                  as months
     ,a.years                  as years
     ,case when a.months<='202307' and a.customer_id='1967491' then '2925773'
       else a.customer_id end  as customer_idh
     ,a.channel_hierarchy_1    as channel
    -- ,case when a.months<='202307' and a.customer_id='1967491' then '北京沃亿商业管理有限公司'
    --   else a.customer_name  end as customer_name
     ,a.bu_1                 as bu_1
     ,a.bu_2                 as bu_2
     ,sum(nvl(b.gbf_growth_bonus,0) +nvl(b.abf_assortment_bonus,0)+nvl(b.ppf_prod_prom_disc,0)
        +nvl(b.lff_prod_listing_fee,0)+nvl(b.pxf_prod_except_disc,0))  as rebate            -- 返利
     ,null as CA                -- 价差
     ,sum(nvl(b.pld ,0)) as PLD -- Price_Listing_Discount，固定价格折扣
     ,sum(nvl(b.ppd ,0)) as PPD -- Price_Promotion_Discount，促销价格折扣
     ,sum(nvl(b.pfg ,0)) as FG  -- Free_Goods，赠品金额
     ,sum(nvl(b.ges ,0)) as GES -- 集团外毛销售额
     ,sum(nvl(b.NGS ,0)) as NGS               -- Net_Gross_Sales，净销售总额
     ,sum(nvl(b.logistics,0)) as logistic_fee      -- 物流费
     ,null as listing_fee       -- 进场费
     ,null as nka_expense       -- NKA费用，如气柱费、信息费等
     ,null as 2nd_dis_dm_others -- 二次陈列费+海报费+其他
     ,sum(nvl(b.l10 ,0)) as l10_commission    -- Commission（佣金）
     ,sum(nvl(b.l11 ,0)) as l11_t_w           -- Transport/Warehouse，运输和仓库管理相关费用
     ,sum(nvl(b.l14 ,0)) as l14_cog           -- 即Total_Manufacturing_Cost，制造类费用
     ,sum(nvl(b.l16 ,0)) as l16_umc           -- 额外运营费用
     ,sum(nvl(b.l17 ,0)) as l17_total         -- 用于Controlling调整FCST的L17费用
     ,null as l17_nka_tm_o2o    -- L17细项
     ,null as l17_channel       -- l17_po+l17_Manual
     ,null as l17_py            -- l17_py
     ,null as l17_ba            -- L17细项
     ,null as l17_mkt           -- L17细项
     ,null as l17_digital       -- L17细项
     ,null as lka_contract_fee  -- Lka合同返利
     ,null as indirect_rebate   -- 间供返利
     ,null as retailer_rebate   -- 间供返利
     ,null as oos  
     ,null as ka_expense
     ,null as promotion_activists
     ,'new' as data_type
  from ${dme_ads}.tb_sales_city_attack_customer_tmp1_01 a
  left join ${dme_cdm}.dwd_sap_customer_summary_bu b
    on nvl(a.months         ,'')=nvl(b.months        ,'')
   and nvl(a.customer_code  ,'')=nvl(b.customer_code ,'')
   and nvl(a.channel_hierarchy_1 ,'')=nvl(b.channel_hierarchy_1 ,'')
   and nvl(a.bu_1         ,'')=nvl(b.bu_1          ,'')
   and nvl(a.bu_2         ,'')=nvl(b.bu_2          ,'')
   and b.ds=max_pt('${dme_cdm}.dwd_sap_customer_summary_bu')
   and b.bu_2='SKP'
   group by a.months
     ,a.years
     ,case when a.months<='202307' and a.customer_id='1967491' then '2925773'
       else a.customer_id end
     ,a.channel_hierarchy_1
    -- ,case when a.months<='202307' and a.customer_id='1967491' then '北京沃亿商业管理有限公司'
    --   else a.customer_name  end
     ,a.bu_1
     ,a.bu_2
 ) t
) a
where if(UPPER(a.bu_2) in ('BEAUTY CARE','LAUNDRY'） and a.months<'202405',a.data_type='old',a.data_type='new')
;


-- 合并Beauty Care、Laundry的YTD 指标
drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp2_01 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp2_01 as
select
   t.months
   ,t.years
   ,t.customer_idh
   ,t.channel
   ,sum(t.NGS_MONTHLY      ) as NGS_MONTHLY            -- 月的 Net_Gross_Sales，净销售总额
   ,sum(t.rebate           ) as rebate            -- 返利
   ,sum(t.CA               ) as CA                -- 价差
   ,sum(t.PLD              ) as PLD               -- Price_Listing_Discount，固定价格折扣
   ,sum(t.PPD              ) as PPD               -- Price_Promotion_Discount，促销价格折扣
   ,sum(t.FG               ) as FG                -- Free_Goods，赠品金额
   ,sum(t.GES              ) as GES               -- 集团外毛销售额
   ,sum(t.NGS              ) as NGS               -- Net_Gross_Sales，净销售总额
   ,sum(t.logistic_fee     ) as logistic_fee      -- 物流费
   ,sum(t.listing_fee      ) as listing_fee       -- 进场费
   ,sum(t.nka_expense      ) as nka_expense       -- NKA费用，如气柱费、信息费等
   ,sum(t.2nd_dis_dm_others) as 2nd_dis_dm_others -- 二次陈列费+海报费+其他
   ,sum(t.l10_commission   ) as l10_commission    -- Commission（佣金）
   ,sum(t.l11_t_w          ) as l11_t_w           -- Transport/Warehouse，运输和仓库管理相关费用
   ,sum(t.l14_cog          ) as l14_cog           -- 即Total_Manufacturing_Cost，制造类费用
   ,sum(t.l16_umc          ) as l16_umc           -- 额外运营费用
   ,sum(t.l17_total        ) as l17_total         -- 用于Controlling调整FCST的L17费用
   ,sum(t.l17_nka_tm_o2o   ) as l17_nka_tm_o2o    -- L17细项
   ,sum(t.l17_channel      ) as l17_channel       -- l17_po+l17_Manual
   ,sum(t.l17_py           ) as l17_py            -- l17_py
   ,sum(t.l17_ba           ) as l17_ba            -- L17细项
   ,sum(t.l17_mkt          ) as l17_mkt           -- L17细项
   ,sum(t.l17_digital      ) as l17_digital       -- L17细项
   ,sum(t.lka_contract_fee ) as lka_contract_fee  -- Lka合同返利
   ,sum(t.indirect_rebate  ) as indirect_rebate   -- 间供返利
   ,sum(t.retailer_rebate  ) as retailer_rebate   -- 间供返利
   ,sum(t.oos              ) as oos  
   ,sum(t.ka_expense       ) as ka_expense
   ,sum(t.promotion_activists) as promotion_activists
from ${dme_ads}.tb_sales_city_attack_customer_tmp2 t
where t.bu_2 in ('Beauty Care','Laundry')
group by t.months ,t.years ,t.customer_idh ,t.channel
;

-- 算出P&L指标YTD的百分比 WS、DT渠道数据
drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_ws_dt_tmp3 ;
create table ${dme_ads}.tb_sales_city_attack_customer_ws_dt_tmp3 as
 select
   t.months
   ,t.years
   ,case when t.bu_2='Beauty Care' and upper(t.channel)='DT' then 'DT Others'
         when t.bu_2='Beauty Care' and upper(t.channel)='MPD' then 'MPD' 
         else t.customer_idh end as distributer_code
   ,t.channel
   ,t.bu_1
   ,t.bu_2
   ,sum(t.NGS_MONTHLY      ) as Orig_NGS_MONTHLY            -- 月的 Net_Gross_Sales，净销售总额
   ,sum(t.rebate           ) as Orig_rebate            -- 返利
   ,sum(t.CA               ) as Orig_CA                -- 价差
   ,sum(t.PLD              ) as Orig_PLD               -- Price_Listing_Discount，固定价格折扣
   ,sum(t.PPD              ) as Orig_PPD               -- Price_Promotion_Discount，促销价格折扣
   ,sum(t.FG               ) as Orig_FG                -- Free_Goods，赠品金额
   ,sum(t.GES              ) as Orig_GES               -- 集团外毛销售额
   ,sum(t.NGS              ) as Orig_NGS               -- Net_Gross_Sales，净销售总额
   ,sum(t.logistic_fee     ) as Orig_logistic_fee      -- 物流费
   ,sum(t.listing_fee      ) as Orig_listing_fee       -- 进场费
   ,sum(t.nka_expense      ) as Orig_nka_expense       -- NKA费用，如气柱费、信息费等
   ,sum(t.2nd_dis_dm_others) as Orig_2nd_dis_dm_others -- 二次陈列费+海报费+其他
   ,sum(t.l10_commission   ) as Orig_l10_commission    -- Commission（佣金）
   ,sum(t.l11_t_w          ) as Orig_l11_t_w           -- Transport/Warehouse，运输和仓库管理相关费用
   ,sum(t.l14_cog          ) as Orig_l14_cog           -- 即Total_Manufacturing_Cost，制造类费用
   ,sum(t.l16_umc          ) as Orig_l16_umc           -- 额外运营费用
   ,sum(t.l17_total        ) as Orig_l17_total         -- 用于Controlling调整FCST的L17费用
   ,sum(t.l17_nka_tm_o2o   ) as Orig_l17_nka_tm_o2o    -- L17细项
   ,sum(t.l17_channel      ) as Orig_l17_channel       -- l17_po+l17_Manual
   ,sum(t.l17_py           ) as Orig_l17_py            -- l17_py
   ,sum(t.l17_ba           ) as Orig_l17_ba            -- L17细项
   ,sum(t.l17_mkt          ) as Orig_l17_mkt           -- L17细项
   ,sum(t.l17_digital      ) as Orig_l17_digital       -- L17细项
   ,sum(t.lka_contract_fee ) as Orig_lka_contract_fee  -- Lka合同返利
   ,sum(t.indirect_rebate  ) as Orig_indirect_rebate   -- 间供返利
   ,sum(t.retailer_rebate  ) as Orig_retailer_rebate   -- 间供返利
   ,sum(t.oos              ) as Orig_oos  
   ,sum(t.ka_expense       ) as Orig_ka_expense
   ,sum(t.promotion_activists) as Orig_promotion_activists
   ,sum(t.PLD   )/sum(if(t.GES=0,null,t.GES)) AS PLD_Rate
   ,sum(t.PPD   )/sum(if(t.GES=0,null,t.GES)) AS PPD_Rate
   ,sum(t.FG    )/sum(if(t.GES=0,null,t.GES)) AS FG_Rate
   ,sum(t.rebate)/sum(if(t.NGS=0,null,t.NGS)) AS Rebate_Rate
   ,sum(t.CA    )/sum(if(t.NGS=0,null,t.NGS)) AS CA_Rate
   ,sum(t.logistic_fee)/sum(if(t.NGS=0,null,t.NGS)) AS  logistic_fee_Rate
   --,sum(nvl(t.listing_fee,0)+nvl(t.nka_expense,0)+nvl(t.2nd_dis_dm_others,0))/sum(if(t.NGS=0,null,t.NGS)) AS Other_investment_Rate
   ,sum(case when t.months>='202405' and t.bu_2='Beauty Care' then nvl(t.listing_fee,0)+nvl(t.oos,0)+nvl(t.ka_expense,0)+nvl(t.promotion_activists,0) 
         else nvl(t.listing_fee,0)+nvl(t.nka_expense,0)+nvl(t.2nd_dis_dm_others,0)
       end) /sum(if(t.NGS=0,null,t.NGS)) AS  Other_investment_Rate    -- 24年5月份开始加工逻辑调整
   ,case when t.months>='202405' and t.bu_2='Beauty Care' then sum(t1.l10_commission)/sum(if(t1.GES=0,null,t1.GES))
      else sum(t.l10_commission)/sum(if(t.GES=0,null,t.GES)) end AS l10_commission_Rate
   ,case when t.months>='202405' and t.bu_2='Beauty Care' then sum(t1.l11_t_w)/sum(if(t1.GES=0,null,t1.GES))
      else sum(t.l11_t_w     )  /sum(if(t.GES=0,null,t.GES)) end AS l11_t_w_Rate
   ,case when t.months>='202405' and t.bu_2='Beauty Care' then sum(t1.l14_cog)/sum(if(t1.GES=0,null,t1.GES))
      else sum(t.l14_cog     )  /sum(if(t.GES=0,null,t.GES)) end AS l14_cog_Rate
   ,case when t.months>='202405' and t.bu_2='Beauty Care' then sum(t1.l16_umc)/sum(if(t1.GES=0,null,t1.GES))
      else sum(t.l16_umc     )  /sum(if(t.GES=0,null,t.GES)) end AS l16_umc_Rate
   ,case when t.months>='202405' and t.bu_2='Beauty Care' then sum(t1.l17_total)/sum(if(t1.GES=0,null,t1.GES))
      else sum(t.l17_total   )  /sum(if(t.GES=0,null,t.GES)) end AS l17_total_Rate
   ,case when t.months>='202405' and t.bu_2='Beauty Care' then sum(nvl(t1.l17_nka_tm_o2o,0)+nvl(t1.l17_py,0)+nvl(t1.l17_channel,0)+nvl(t1.l17_ba,0))/sum(if(t1.GES=0,null,t1.GES))
     else sum(nvl(t.l17_nka_tm_o2o,0)+nvl(t.l17_py,0)+nvl(t.l17_channel,0)+nvl(t.l17_ba,0))/sum(if(t.GES=0,null,t.GES)) end AS l17_opcb_Rate
   ,sum(case when t.months>='202405' and t.bu_2='Beauty Care' then nvl(t.retailer_rebate,0)
         else nvl(t.lka_contract_fee,0)+nvl(t.indirect_rebate,0) end)/sum(if(t.NGS=0,null,t.NGS)) as contract_Rate  -- 间供合同比例
 from ${dme_ads}.tb_sales_city_attack_customer_tmp2 t
 left join ${dme_ads}.tb_sales_city_attack_customer_tmp2_01 t1
  on nvl(t.months,'')=nvl(t1.months,'')
  and nvl(t.years,'')=nvl(t1.years,'')
  and nvl(t.customer_idh,'')=nvl(t1.customer_idh,'')
  and nvl(t.channel,'')=nvl(t1.channel,'')
 where upper(t.channel) in ('DT','MPD','WS') 
 --upper(t.channel) not in ('NKA','SELECTIVE RETAILER','LKA','ECOM')
 group by t.months ,t.years
      ,case when t.bu_2='Beauty Care' and upper(t.channel)='DT' then 'DT Others'
         when t.bu_2='Beauty Care' and upper(t.channel)='MPD' then 'MPD' 
         else t.customer_idh end ,t.channel,t.bu_1 ,t.bu_2

;

-- by ka计算当月最大pos基价销售额（未税）的经销商 ：零售线下的零售商，若存在同一个城市有多个经销商的情况，经销商账面金额使用该零售商在该城市所有经销商的账面金额加和，Customer IDH和Customer Name显示为当月POS基价销额最大的经销商（非YTD）
drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp3_01;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp3_01 as
  select
    b.year
    ,b.months
    ,if(b.year='2023' and a.ka_name regexp '屈臣氏' and nvl(upper(a.ka_name),'') not regexp 'OFFLINE','Others',a.city_name) as city_name      -- 城市 23年屈臣氏 云仓数据用24年数据分摊到具体城市
    ,a.first_channel_name
    ,a.Ka_name-- KA名称
    ,a.dist_type
    ,case when upper(a.first_channel_name) in ('NKA','SELECTIVE RETAILER') and a.dist_type='NKA直供' then
      case when a.Ka_name regexp '欧尚'     then 'Auchan'
           when a.Ka_name regexp '乐购'     then 'Tesco'
           when a.Ka_name regexp '家乐福'   then 'Carrefour'
           when a.Ka_name regexp '迪亚'     then 'DIA'
           when a.Ka_name regexp '天津家乐' then 'HomeClub'
           when a.Ka_name regexp '卜蜂莲花' then 'LOTUS'
           when a.Ka_name regexp '万宁'     then 'Mannings'
           when a.Ka_name regexp '麦德龙'   then 'Metro'
           when a.Ka_name regexp '农工商'   then 'NGS'
           when a.Ka_name regexp '大润发'   then 'RT'
           when a.Ka_name regexp '山姆'     then 'Sams'
           when a.Ka_name regexp '沃尔玛'   then 'WAL'
           when a.Ka_name regexp '华润万家' then 'Wanjia'
           when a.Ka_name regexp '屈臣氏'   then 'Watsons'
           when a.Ka_name regexp '莎莎'     then 'SaSa'
        else a.distributer_code  end
      else a.distributer_code
     end as distributer_code -- 客户code
    ,a.distributer_name -- 客户名称
    ,a.bu_1
    ,a.bu_2
    ,sum(case when a.months=b.months then a.return_after_base_amt end) as return_after_base_amt -- 退货后基价销售额（未税)
   from ${dme_ads}.tb_sales_city_attack_summry a
   inner join (
       select month_id as months,year_id as year
       from ${dme_cdm}.dim_day
       where month_id >='202001' and month_id <=substr('${bizdate}',1,6)
       group by month_id,year_id
   ) b
   on a.year=b.year
   where a.ds=max_pt('${dme_ads}.tb_sales_city_attack_summry')
   and a.bu_2 in ('Beauty Care','SKP')
  group by b.year
    ,b.months
    ,if(b.year='2023' and a.ka_name regexp '屈臣氏' and nvl(upper(a.ka_name),'') not regexp 'OFFLINE','Others',a.city_name) -- 城市
    ,a.first_channel_name
    ,a.Ka_name-- KA名称
    ,a.dist_type
    ,case when upper(a.first_channel_name) in ('NKA','SELECTIVE RETAILER') and a.dist_type='NKA直供' then
      case when a.Ka_name regexp '欧尚'     then 'Auchan'
           when a.Ka_name regexp '乐购'     then 'Tesco'
           when a.Ka_name regexp '家乐福'   then 'Carrefour'
           when a.Ka_name regexp '迪亚'     then 'DIA'
           when a.Ka_name regexp '天津家乐' then 'HomeClub'
           when a.Ka_name regexp '卜蜂莲花' then 'LOTUS'
           when a.Ka_name regexp '万宁'     then 'Mannings'
           when a.Ka_name regexp '麦德龙'   then 'Metro'
           when a.Ka_name regexp '农工商'   then 'NGS'
           when a.Ka_name regexp '大润发'   then 'RT'
           when a.Ka_name regexp '山姆'     then 'Sams'
           when a.Ka_name regexp '沃尔玛'   then 'WAL'
           when a.Ka_name regexp '华润万家' then 'Wanjia'
           when a.Ka_name regexp '屈臣氏'   then 'Watsons'
           when a.Ka_name regexp '莎莎'     then 'SaSa'
        else a.distributer_code  end
      else a.distributer_code
     end  -- 客户code
    ,a.distributer_name -- 客户名称
    ,a.bu_1
    ,a.bu_2
    -- 合并专业线线下维度信息
  union all
  select distinct
    a.years as year
    ,a.months
    ,c.city_name        -- 城市
    ,coalesce(a.channel,b.channel_hierarchy_1,'Others') AS first_channel_name
    ,null as Ka_name          -- KA名称
    ,null as dist_type
    ,a.distributer_code as distributer_code -- 客户code
    ,b.customer_name as distributer_name -- 客户名称
    ,a.bu_1
    ,a.bu_2
    ,null as return_after_base_amt
  from ${dme_ads}.tb_sales_city_attack_customer_ws_dt_tmp3 a
  left join (
     select
        customer_code,customer_name,bu_2,channel_hierarchy_1,substr(ds,1,6) as months
     from ${dme_cdm}.dwd_master_data_customer_bu
     where ds like '%01'
     group by customer_code,customer_name,bu_2,channel_hierarchy_1,substr(ds,1,6)
     ) b
  on a.distributer_code=b.customer_code
  and a.bu_2=b.bu_2
  and a.months=b.months
  left join ${dme_cdm}.dwd_city_attack_dist_list c   -- 专业线城市占比
  on a.distributer_code=c.dist_code
  and a.months>=c.begin_month
  and a.months<c.end_month
  and c.ds=max_pt('${dme_cdm}.dwd_city_attack_dist_list')
  where a.bu_2='SKP'
 
;

-- 取线下最大pos基价经销商
drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp3_02;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp3_02 as
 select
   a.year
   ,a.months
   ,a.city_name      -- 城市
   ,a.first_channel_name
   ,a.Ka_name-- KA名称
   ,a.dist_type
   ,a.distributer_code_orgi -- 客户code
   ,a.distributer_name_orgi -- 客户名称
   ,case when upper(a.distributer_code)='OTHERS' then a.distributer_code_orgi
      else a.distributer_code
     end as distributer_code -- 经销商code
   ,case when upper(distributer_code)='OTHERS' then a.distributer_name_orgi
      else a.distributer_name
     end as distributer_name -- 经销商名称
   ,a.bu_1
   ,a.bu_2
   ,a.return_after_base_amt -- 退货后基价销售额（未税）
 from(
   select
      a.year
     ,a.months
     ,a.city_name      -- 城市
     ,a.first_channel_name
     ,a.Ka_name-- KA名称
     ,a.dist_type
     ,a.distributer_code as distributer_code_orgi -- 客户code
     ,a.distributer_name as distributer_name_orgi -- 客户名称
     ,case when upper(a.first_channel_name) in ('NKA','SELECTIVE RETAILER','LKA') then first_value(a.distributer_code) over(partition by a.months,a.city_name,a.first_channel_name,a.Ka_name,a.dist_type,a.bu_1,a.bu_2 order by a.return_after_base_amt desc,if(nvl(b.return_after_base_amt,0)=0,distributer_code,1) desc)
        else a.distributer_code
       end as distributer_code -- 经销商code
     ,case when upper(a.first_channel_name) in ('NKA','SELECTIVE RETAILER','LKA') then first_value(a.distributer_name) over(partition by a.months,a.city_name,a.first_channel_name,a.Ka_name,a.dist_type,a.bu_1,a.bu_2 order by a.return_after_base_amt desc,if(nvl(b.return_after_base_amt,0)=0,distributer_code,1) desc)
      else a.distributer_name
       end as distributer_name -- 经销商名称
     ,a.bu_1
     ,a.bu_2
     ,a.return_after_base_amt -- 退货后基价销售额（未税）
   from ${dme_ads}.tb_sales_city_attack_customer_tmp3_01 a
   left join (
      select
        year
        ,months
        ,city_name      -- 城市
        ,first_channel_name
        ,Ka_name-- KA名称
        ,dist_type
        ,bu_1
        ,bu_2
        ,sum(return_after_base_amt) as return_after_base_amt
     from ${dme_ads}.tb_sales_city_attack_customer_tmp3_01
     group by year ,months ,city_name ,first_channel_name ,Ka_name ,bu_1 ,bu_2,dist_type
   ) b  -- 如果改ka销售数据都是0，保持原来的不变
   on a.year=b.year
   and a.months=b.months
   and nvl(a.city_name,'')=nvl(b.city_name,'')
   and nvl(a.first_channel_name,'')=nvl(b.first_channel_name,'')
   and nvl(a.Ka_name,'')=nvl(b.Ka_name,'')
   and nvl(a.dist_type,'')=nvl(b.dist_type,'')
   and nvl(a.bu_1,'')=nvl(b.bu_1,'')
   and nvl(a.bu_2,'')=nvl(b.bu_2,'')
 ) a
;
-- 算出P&L指标YTD的百分比 Ecom、NKA、LKA渠道，专业线下DT数据(原始经销商)
drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp3_03 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp3_03 as
select
  t0.months
  ,t0.year as years
  ,t0.distributer_code_orgi as distributer_code
  ,t0.distributer_name_orgi as distributer_name
  ,t0.bu_1
  ,t0.bu_2
  ,t0.city_name      -- 城市
  ,t0.first_channel_name
  ,t0.Ka_name-- KA名称
   ,cast(case when t0.months>='202405' and t0.bu_2='Beauty Care' then sum(t1.l17_mkt)
      else sum(t.l17_mkt) end as decimal(28,6)) as retail_Orig_l17_mkt          -- L17细项bc+Laundry
   ,cast(case when t0.months>='202405' and t0.bu_2='Beauty Care' then sum(t1.l17_digital)
      else sum(t.l17_digital) end as decimal(28,6)) as retail_Orig_l17_digital     -- L17细项bc+Laundry
   ,cast(case when t0.months>='202405' and t0.bu_2='Beauty Care' then sum(t1.GES)
      else sum(t.GES) end as decimal(28,6)) as retail_Orig_GES  -- L17细项bc+Laundry 
from (
  select
     months
    ,years
    ,customer_idh
    ,bu_1
    ,bu_2
    ,sum(NGS_MONTHLY      ) as Orig_NGS_MONTHLY            -- 月的 Net_Gross_Sales，净销售总额
    ,sum(rebate           ) as rebate            -- YTD 返利
    ,sum(CA               ) as CA                -- YTD 价差
    ,sum(PLD              ) as PLD               -- YTD Price_Listing_Discount，固定价格折扣
    ,sum(PPD              ) as PPD               -- YTD Price_Promotion_Discount，促销价格折扣
    ,sum(FG               ) as FG                -- YTD Free_Goods，赠品金额
    ,sum(GES              ) as GES               -- YTD 集团外毛销售额
    ,sum(NGS              ) as NGS               -- YTD Net_Gross_Sales，净销售总额
    ,sum(logistic_fee     ) as logistic_fee      -- YTD 物流费
    ,sum(listing_fee      ) as listing_fee       -- YTD 进场费
    ,sum(nka_expense      ) as nka_expense       -- YTD NKA费用，如气柱费、信息费等
    ,sum(2nd_dis_dm_others) as 2nd_dis_dm_others -- YTD 二次陈列费+海报费+其他
    ,sum(l10_commission   ) as l10_commission    -- YTD Commission（佣金）
    ,sum(l11_t_w          ) as l11_t_w           -- YTD Transport/Warehouse，运输和仓库管理相关费用
    ,sum(l14_cog          ) as l14_cog           -- YTD 即Total_Manufacturing_Cost，制造类费用
    ,sum(l16_umc          ) as l16_umc           -- YTD 额外运营费用
    ,sum(l17_total        ) as l17_total         -- YTD 用于Controlling调整FCST的L17费用
    ,sum(l17_nka_tm_o2o   ) as l17_nka_tm_o2o    -- YTD L17细项
    ,sum(l17_channel      ) as l17_channel       -- YTD l17_po+l17_Manual
    ,sum(l17_py           ) as l17_py            -- YTD l17_py
    ,sum(l17_ba           ) as l17_ba            -- YTD L17细项
    ,sum(l17_mkt          ) as l17_mkt           -- YTD L17细项
    ,sum(l17_digital      ) as l17_digital       -- YTD L17细项
    ,sum(lka_contract_fee ) as lka_contract_fee  -- Lka合同返利
    ,sum(indirect_rebate  ) as indirect_rebate   -- 间供返利
    ,sum(lka_contract_fee ) as retailer_rebate   -- 间供返利
    ,sum(oos              ) as oos  
    ,sum(ka_expense       ) as ka_expense
    ,sum(promotion_activists) as promotion_activists
  from ${dme_ads}.tb_sales_city_attack_customer_tmp2
  group by months ,years ,customer_idh ,bu_1 ,bu_2
 ) t
left join ${dme_ads}.tb_sales_city_attack_customer_tmp3_02 t0
on nvl(t.customer_idh,'')=nvl(t0.distributer_code_orgi,'')
and t.months=t0.months
and t.bu_1=t0.bu_1
and t.bu_2=t0.bu_2
left join (
   select
      months,years,customer_idh
    ,sum(NGS_MONTHLY      ) as Orig_NGS_MONTHLY            -- 月的 Net_Gross_Sales，净销售总额
    ,sum(rebate           ) as rebate            -- YTD 返利
    ,sum(CA               ) as CA                -- YTD 价差
    ,sum(PLD              ) as PLD               -- YTD Price_Listing_Discount，固定价格折扣
    ,sum(PPD              ) as PPD               -- YTD Price_Promotion_Discount，促销价格折扣
    ,sum(FG               ) as FG                -- YTD Free_Goods，赠品金额
    ,sum(GES              ) as GES               -- YTD 集团外毛销售额
    ,sum(NGS              ) as NGS               -- YTD Net_Gross_Sales，净销售总额
    ,sum(logistic_fee     ) as logistic_fee      -- YTD 物流费
    ,sum(listing_fee      ) as listing_fee       -- YTD 进场费
    ,sum(nka_expense      ) as nka_expense       -- YTD NKA费用，如气柱费、信息费等
    ,sum(2nd_dis_dm_others) as 2nd_dis_dm_others -- YTD 二次陈列费+海报费+其他
    ,sum(l10_commission   ) as l10_commission    -- YTD Commission（佣金）
    ,sum(l11_t_w          ) as l11_t_w           -- YTD Transport/Warehouse，运输和仓库管理相关费用
    ,sum(l14_cog          ) as l14_cog           -- YTD 即Total_Manufacturing_Cost，制造类费用
    ,sum(l16_umc          ) as l16_umc           -- YTD 额外运营费用
    ,sum(l17_total        ) as l17_total         -- YTD 用于Controlling调整FCST的L17费用
    ,sum(l17_nka_tm_o2o   ) as l17_nka_tm_o2o    -- YTD L17细项
    ,sum(l17_channel      ) as l17_channel       -- YTD l17_po+l17_Manual
    ,sum(l17_py           ) as l17_py            -- YTD l17_py
    ,sum(l17_ba           ) as l17_ba            -- YTD L17细项
    ,sum(l17_mkt          ) as l17_mkt           -- YTD L17细项
    ,sum(l17_digital      ) as l17_digital       -- YTD L17细项
    ,sum(lka_contract_fee ) as lka_contract_fee  -- Lka合同返利
    ,sum(indirect_rebate  ) as indirect_rebate   -- 间供返利
    ,sum(lka_contract_fee ) as retailer_rebate   -- 间供返利
    ,sum(oos              ) as oos  
    ,sum(ka_expense       ) as ka_expense
    ,sum(promotion_activists) as promotion_activists
   from ${dme_ads}.tb_sales_city_attack_customer_tmp2_01
   group by months,years,customer_idh
  ) t1
  on nvl(t.months,'')=nvl(t1.months,'')
  and nvl(t.years,'')=nvl(t1.years,'')
  and nvl(t.customer_idh,'')=nvl(t1.customer_idh,'')
group by t0.months,t0.year,t0.distributer_code_orgi,t0.distributer_name_orgi ,t0.bu_1,t0.bu_2,t0.city_name,t0.first_channel_name,t0.Ka_name
;


-- 算出P&L指标YTD的百分比 Ecom、NKA、LKA渠道，专业线下DT数据
drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp3 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp3 as
select
  t0.months
  ,t0.year as years
  ,t0.distributer_code
  ,t0.distributer_name
  ,t0.bu_1
  ,t0.bu_2
  ,t0.city_name      -- 城市
  ,t0.first_channel_name
  ,t0.Ka_name-- KA名称
  ,sum(t.Orig_NGS_MONTHLY ) as Orig_NGS_MONTHLY            -- 月的 Net_Gross_Sales，净销售总额
  ,sum(t.rebate           ) as Orig_rebate            -- 返利
  ,sum(t.CA               ) as Orig_CA                -- 价差
  ,sum(t.PLD              ) as Orig_PLD               -- Price_Listing_Discount，固定价格折扣
  ,sum(t.PPD              ) as Orig_PPD               -- Price_Promotion_Discount，促销价格折扣
  ,sum(t.FG               ) as Orig_FG                -- Free_Goods，赠品金额
  ,sum(t.GES              ) as Orig_GES               -- 集团外毛销售额
  ,sum(t.NGS              ) as Orig_NGS               -- Net_Gross_Sales，净销售总额
  ,sum(t.logistic_fee     ) as Orig_logistic_fee      -- 物流费
  ,sum(t.listing_fee      ) as Orig_listing_fee       -- 进场费
  ,sum(t.nka_expense      ) as Orig_nka_expense       -- NKA费用，如气柱费、信息费等
  ,sum(t.2nd_dis_dm_others) as Orig_2nd_dis_dm_others -- 二次陈列费+海报费+其他
  ,sum(t.l10_commission   ) as Orig_l10_commission    -- Commission（佣金）
  ,sum(t.l11_t_w          ) as Orig_l11_t_w           -- Transport/Warehouse，运输和仓库管理相关费用
  ,sum(t.l14_cog          ) as Orig_l14_cog           -- 即Total_Manufacturing_Cost，制造类费用
  ,sum(t.l16_umc          ) as Orig_l16_umc           -- 额外运营费用
  ,sum(t.l17_total        ) as Orig_l17_total         -- 用于Controlling调整FCST的L17费用
  ,sum(t.l17_nka_tm_o2o   ) as Orig_l17_nka_tm_o2o    -- L17细项
  ,sum(t.l17_channel      ) as Orig_l17_channel       -- l17_po+l17_Manual
  ,sum(t.l17_py           ) as Orig_l17_py            -- l17_py
  ,sum(t.l17_ba           ) as Orig_l17_ba            -- L17细项
  ,sum(t.l17_mkt          ) as Orig_l17_mkt           -- L17细项
  ,sum(t.l17_digital      ) as Orig_l17_digital       -- L17细项
  ,sum(t.lka_contract_fee ) as Orig_lka_contract_fee       -- Lka合同返利
  ,sum(t.indirect_rebate  ) as Orig_indirect_rebate        -- 间供返利
  ,sum(t.oos              ) as Orig_oos  
  ,sum(t.ka_expense       ) as Orig_ka_expense
  ,sum(t.promotion_activists) as Orig_promotion_activists
  ,cast(sum(t.PLD   )/sum(if(t.GES=0,null,t.GES)) as decimal(28,6)) AS PLD_Rate
  ,cast(sum(t.PPD   )/sum(if(t.GES=0,null,t.GES)) as decimal(28,6)) AS PPD_Rate
  ,cast(sum(t.FG    )/sum(if(t.GES=0,null,t.GES)) as decimal(28,6)) AS FG_Rate
  ,cast(sum(t.rebate)/sum(if(t.NGS=0,null,t.NGS)) as decimal(28,6)) AS Rebate_Rate
  ,cast(sum(t.CA    )/sum(if(t.NGS=0,null,t.NGS)) as decimal(28,6)) AS CA_Rate
  ,cast(sum(t.logistic_fee)/sum(if(t.NGS=0,null,t.NGS)) as decimal(28,6)) AS  logistic_fee_Rate
  ,cast(sum(case when t0.months>='202405' and t0.bu_2='Beauty Care' then nvl(t.listing_fee,0)+nvl(t.oos,0)+nvl(t.ka_expense,0)+nvl(t.promotion_activists,0) 
         else nvl(t.listing_fee,0)+nvl(t.nka_expense,0)+nvl(t.2nd_dis_dm_others,0)
       end) /sum(if(t.NGS=0,null,t.NGS)) as decimal(28,6)) AS Other_investment_Rate  -- 24年5月份开始加工逻辑调整
  ,cast(case when t0.months>='202405' and t0.bu_2='Beauty Care' then sum(t1.l10_commission)/sum(if(t1.GES=0,null,t1.GES))
      else sum(t.l10_commission)/sum(if(t.GES=0,null,t.GES)) end as decimal(28,6))  AS l10_commission_Rate
  ,cast(case when t0.months>='202405' and t0.bu_2='Beauty Care' then sum(t1.l11_t_w)/sum(if(t1.GES=0,null,t1.GES))
      else sum(t.l11_t_w     )  /sum(if(t.GES=0,null,t.GES)) end as decimal(28,6))  AS l11_t_w_Rate
  ,cast(case when t0.months>='202405' and t0.bu_2='Beauty Care' then sum(t1.l14_cog)/sum(if(t1.GES=0,null,t1.GES))
      else sum(t.l14_cog     )  /sum(if(t.GES=0,null,t.GES)) end as decimal(28,6))  AS l14_cog_Rate
  ,cast(case when t0.months>='202405' and t0.bu_2='Beauty Care' then sum(t1.l16_umc)/sum(if(t1.GES=0,null,t1.GES))
      else sum(t.l16_umc     )  /sum(if(t.GES=0,null,t.GES)) end as decimal(28,6))  AS l16_umc_Rate
  ,cast(case when t0.months>='202405' and t0.bu_2='Beauty Care' then sum(t1.l17_total)/sum(if(t1.GES=0,null,t1.GES))
      else sum(t.l17_total   )  /sum(if(t.GES=0,null,t.GES)) end as decimal(28,6))  AS l17_total_Rate
  ,cast(case when t0.months>='202405' and t0.bu_2='Beauty Care' then sum(nvl(t1.l17_nka_tm_o2o,0)+nvl(t1.l17_py,0)+nvl(t1.l17_channel,0)+nvl(t1.l17_ba,0))/sum(if(t1.GES=0,null,t1.GES))
    else sum(nvl(t.l17_nka_tm_o2o,0)+nvl(t.l17_py,0)+nvl(t.l17_channel,0)+nvl(t.l17_ba,0))/sum(if(t.GES=0,null,t.GES)) end as decimal(28,6)) AS l17_opcb_Rate

from (
  select
     months
    ,years
    ,customer_idh
    ,bu_1
    ,bu_2
    ,sum(NGS_MONTHLY      ) as Orig_NGS_MONTHLY            -- 月的 Net_Gross_Sales，净销售总额
    ,sum(rebate           ) as rebate            -- YTD 返利
    ,sum(CA               ) as CA                -- YTD 价差
    ,sum(PLD              ) as PLD               -- YTD Price_Listing_Discount，固定价格折扣
    ,sum(PPD              ) as PPD               -- YTD Price_Promotion_Discount，促销价格折扣
    ,sum(FG               ) as FG                -- YTD Free_Goods，赠品金额
    ,sum(GES              ) as GES               -- YTD 集团外毛销售额
    ,sum(NGS              ) as NGS               -- YTD Net_Gross_Sales，净销售总额
    ,sum(logistic_fee     ) as logistic_fee      -- YTD 物流费
    ,sum(listing_fee      ) as listing_fee       -- YTD 进场费
    ,sum(nka_expense      ) as nka_expense       -- YTD NKA费用，如气柱费、信息费等
    ,sum(2nd_dis_dm_others) as 2nd_dis_dm_others -- YTD 二次陈列费+海报费+其他
    ,sum(l10_commission   ) as l10_commission    -- YTD Commission（佣金）
    ,sum(l11_t_w          ) as l11_t_w           -- YTD Transport/Warehouse，运输和仓库管理相关费用
    ,sum(l14_cog          ) as l14_cog           -- YTD 即Total_Manufacturing_Cost，制造类费用
    ,sum(l16_umc          ) as l16_umc           -- YTD 额外运营费用
    ,sum(l17_total        ) as l17_total         -- YTD 用于Controlling调整FCST的L17费用
    ,sum(l17_nka_tm_o2o   ) as l17_nka_tm_o2o    -- YTD L17细项
    ,sum(l17_channel      ) as l17_channel       -- YTD l17_po+l17_Manual
    ,sum(l17_py           ) as l17_py            -- YTD l17_py
    ,sum(l17_ba           ) as l17_ba            -- YTD L17细项
    ,sum(l17_mkt          ) as l17_mkt           -- YTD L17细项
    ,sum(l17_digital      ) as l17_digital       -- YTD L17细项
    ,sum(lka_contract_fee ) as lka_contract_fee  -- Lka合同返利
    ,sum(indirect_rebate  ) as indirect_rebate   -- 间供返利
    ,sum(lka_contract_fee ) as retailer_rebate   -- 间供返利
    ,sum(oos              ) as oos  
    ,sum(ka_expense       ) as ka_expense
    ,sum(promotion_activists) as promotion_activists
  from ${dme_ads}.tb_sales_city_attack_customer_tmp2
  group by months ,years ,customer_idh ,bu_1 ,bu_2
 ) t
left join ${dme_ads}.tb_sales_city_attack_customer_tmp3_02 t0
on nvl(t.customer_idh,'')=nvl(t0.distributer_code_orgi,'')
and t.months=t0.months
and t.bu_1=t0.bu_1
and t.bu_2=t0.bu_2
left join (
   select
      months,years,customer_idh
    ,sum(NGS_MONTHLY      ) as Orig_NGS_MONTHLY            -- 月的 Net_Gross_Sales，净销售总额
    ,sum(rebate           ) as rebate            -- YTD 返利
    ,sum(CA               ) as CA                -- YTD 价差
    ,sum(PLD              ) as PLD               -- YTD Price_Listing_Discount，固定价格折扣
    ,sum(PPD              ) as PPD               -- YTD Price_Promotion_Discount，促销价格折扣
    ,sum(FG               ) as FG                -- YTD Free_Goods，赠品金额
    ,sum(GES              ) as GES               -- YTD 集团外毛销售额
    ,sum(NGS              ) as NGS               -- YTD Net_Gross_Sales，净销售总额
    ,sum(logistic_fee     ) as logistic_fee      -- YTD 物流费
    ,sum(listing_fee      ) as listing_fee       -- YTD 进场费
    ,sum(nka_expense      ) as nka_expense       -- YTD NKA费用，如气柱费、信息费等
    ,sum(2nd_dis_dm_others) as 2nd_dis_dm_others -- YTD 二次陈列费+海报费+其他
    ,sum(l10_commission   ) as l10_commission    -- YTD Commission（佣金）
    ,sum(l11_t_w          ) as l11_t_w           -- YTD Transport/Warehouse，运输和仓库管理相关费用
    ,sum(l14_cog          ) as l14_cog           -- YTD 即Total_Manufacturing_Cost，制造类费用
    ,sum(l16_umc          ) as l16_umc           -- YTD 额外运营费用
    ,sum(l17_total        ) as l17_total         -- YTD 用于Controlling调整FCST的L17费用
    ,sum(l17_nka_tm_o2o   ) as l17_nka_tm_o2o    -- YTD L17细项
    ,sum(l17_channel      ) as l17_channel       -- YTD l17_po+l17_Manual
    ,sum(l17_py           ) as l17_py            -- YTD l17_py
    ,sum(l17_ba           ) as l17_ba            -- YTD L17细项
    ,sum(l17_mkt          ) as l17_mkt           -- YTD L17细项
    ,sum(l17_digital      ) as l17_digital       -- YTD L17细项
    ,sum(lka_contract_fee ) as lka_contract_fee  -- Lka合同返利
    ,sum(indirect_rebate  ) as indirect_rebate   -- 间供返利
    ,sum(lka_contract_fee ) as retailer_rebate   -- 间供返利
    ,sum(oos              ) as oos  
    ,sum(ka_expense       ) as ka_expense
    ,sum(promotion_activists) as promotion_activists
   from ${dme_ads}.tb_sales_city_attack_customer_tmp2_01
   group by months,years,customer_idh
  ) t1
  on nvl(t.months,'')=nvl(t1.months,'')
  and nvl(t.years,'')=nvl(t1.years,'')
  and nvl(t.customer_idh,'')=nvl(t1.customer_idh,'')
group by t0.months,t0.year,t0.distributer_code,t0.distributer_name ,t0.bu_1,t0.bu_2,t0.city_name,t0.first_channel_name,t0.Ka_name
;


-- pos基价销售额（未税）ytd
drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp4_01 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp4_01 as
 select
   b.year
   ,b.months
   ,a.city_name        -- 城市
   ,a.Ka_code-- KA编码
   ,a.Ka_name-- KA名称
   ,a.Ka_code_tp -- ecom放TP侧门店id，线下是ka编码
   ,a.Ka_name_tp -- ecom放TP侧门店id，线下是ka编码
   ,case when upper(a.first_channel_name) in ('NKA','SELECTIVE RETAILER') and a.dist_type='NKA直供' then
         case when a.ka_code in ('KA0010','KA0070','KA0006','KA0011','KA0001','KA0007','KA0005','KA0004') then a.ka_name_en
              -- when a.Ka_name regexp '欧尚'     then 'Auchan'
              -- when a.Ka_name regexp '乐购'     then 'Tesco'
              -- when a.Ka_name regexp '家乐福'   then 'Carrefour'
              -- when a.Ka_name regexp '迪亚'     then 'DIA'
              -- when a.Ka_name regexp '天津家乐' then 'HomeClub'
              -- when a.Ka_name regexp '卜蜂莲花' then 'LOTUS'
              -- when a.Ka_name regexp '万宁'     then 'Mannings'
              -- when a.Ka_name regexp '麦德龙'   then 'Metro'
              -- when a.Ka_name regexp '农工商'   then 'NGS'
              -- when a.Ka_name regexp '大润发'   then 'RT'
              -- when a.Ka_name regexp '山姆'     then 'Sams'
              -- when a.Ka_name regexp '沃尔玛'   then 'WAL'
              -- when a.Ka_name regexp '华润万家' then 'Wanjia'
              -- when a.Ka_name regexp '屈臣氏'   then 'Watsons'
              -- when a.Ka_name regexp '莎莎'     then 'SaSa'
           else nvl(t0.distributer_code,a.distributer_code) end
       else nvl(t0.distributer_code,a.distributer_code)
     end as distributer_code  -- 客户code
   ,case when upper(a.first_channel_name) in ('NKA','SELECTIVE RETAILER')  and a.dist_type='NKA直供' then '公司直供'
      else nvl(t0.distributer_name,a.distributer_name)
     end as distributer_name -- 客户名称
   ,a.bu_1
   ,a.bu_2
   ,a.first_channel_name
   ,a.dist_type -- 经销商类型
   ,cast(sum(case when substr(a.months,5,2)='01' then if(a.dist_type='电商(手工_城市)',a.return_after_gmv,a.return_after_base_amt)*nvl(1-t3.return_rate,1) end) as decimal(38,6)) as Base_sale_amt_Jan  -- 1月份退货后基价销售额（未税）
   ,cast(sum(case when substr(a.months,5,2)='02' then if(a.dist_type='电商(手工_城市)',a.return_after_gmv,a.return_after_base_amt)*nvl(1-t3.return_rate,1) end) as decimal(38,6)) as Base_sale_amt_Feb  -- 2月份退货后基价销售额（未税）
   ,cast(sum(case when substr(a.months,5,2)='03' then if(a.dist_type='电商(手工_城市)',a.return_after_gmv,a.return_after_base_amt)*nvl(1-t3.return_rate,1) end) as decimal(38,6)) as Base_sale_amt_Mar  -- 3月份退货后基价销售额（未税）
   ,cast(sum(case when substr(a.months,5,2)='04' then if(a.dist_type='电商(手工_城市)',a.return_after_gmv,a.return_after_base_amt)*nvl(1-t3.return_rate,1) end) as decimal(38,6)) as Base_sale_amt_Apr  -- 4月份退货后基价销售额（未税）
   ,cast(sum(case when substr(a.months,5,2)='05' then if(a.dist_type='电商(手工_城市)',a.return_after_gmv,a.return_after_base_amt)*nvl(1-t3.return_rate,1) end) as decimal(38,6)) as Base_sale_amt_May  -- 5月份退货后基价销售额（未税）
   ,cast(sum(case when substr(a.months,5,2)='06' then if(a.dist_type='电商(手工_城市)',a.return_after_gmv,a.return_after_base_amt)*nvl(1-t3.return_rate,1) end) as decimal(38,6)) as Base_sale_amt_Jun  -- 6月份退货后基价销售额（未税）
   ,cast(sum(case when substr(a.months,5,2)='07' then if(a.dist_type='电商(手工_城市)',a.return_after_gmv,a.return_after_base_amt)*nvl(1-t3.return_rate,1) end) as decimal(38,6)) as Base_sale_amt_Jul  -- 7月份退货后基价销售额（未税）
   ,cast(sum(case when substr(a.months,5,2)='08' then if(a.dist_type='电商(手工_城市)',a.return_after_gmv,a.return_after_base_amt)*nvl(1-t3.return_rate,1) end) as decimal(38,6)) as Base_sale_amt_Aug  -- 8月份退货后基价销售额（未税）
   ,cast(sum(case when substr(a.months,5,2)='09' then if(a.dist_type='电商(手工_城市)',a.return_after_gmv,a.return_after_base_amt)*nvl(1-t3.return_rate,1) end) as decimal(38,6)) as Base_sale_amt_Sep  -- 9月份退货后基价销售额（未税）
   ,cast(sum(case when substr(a.months,5,2)='10' then if(a.dist_type='电商(手工_城市)',a.return_after_gmv,a.return_after_base_amt)*nvl(1-t3.return_rate,1) end) as decimal(38,6)) as Base_sale_amt_Oct  -- 10月份退货后基价销售额（未税）
   ,cast(sum(case when substr(a.months,5,2)='11' then if(a.dist_type='电商(手工_城市)',a.return_after_gmv,a.return_after_base_amt)*nvl(1-t3.return_rate,1) end) as decimal(38,6)) as Base_sale_amt_Nov  -- 11月份退货后基价销售额（未税）
   ,cast(sum(case when substr(a.months,5,2)='12' then if(a.dist_type='电商(手工_城市)',a.return_after_gmv,a.return_after_base_amt)*nvl(1-t3.return_rate,1) end)as decimal(38,6)) as Base_sale_amt_Dec  -- 12月份退货后基价销售额（未税）
   ,cast(sum(a.return_after_base_amt*nvl(1-t3.return_rate,1)) as decimal(38,6)) as base_sale_amt_ytd -- YTD退货后基价销售额（未税）
   ,cast(sum(a.return_after_gmv     *nvl(1-t3.return_rate,1)) as decimal(38,6)) as sales_amt_ytd     -- YTD退货后销售额（未税）
   ,cast(sum(a.return_after_shop_gmv*nvl(1-t3.return_rate,1)) as decimal(38,6)) as shop_gmv_ytd      -- YTD店铺退货后GMV（未税)
 from ${dme_ads}.tb_sales_city_attack_summry  a
 inner join (
     select month_id as months,year_id as year
     from ${dme_cdm}.dim_day
     where month_id >='202001' and month_id <=substr('${bizdate}',1,6)
     group by month_id,year_id
 ) b
 on a.year=b.year
 and a.months<=b.months
 left join ${dme_ads}.tb_sales_city_attack_customer_tmp3_02 t0
 on b.months=t0.months
 and case when upper(a.first_channel_name) in ('NKA','SELECTIVE RETAILER') and a.dist_type='NKA直供' then
         case when a.ka_code in ('KA0010','KA0070','KA0006','KA0011','KA0001','KA0007','KA0005','KA0004') then a.ka_name_en
           else a.distributer_code  end
       else a.distributer_code end=t0.distributer_code_orgi
 and nvl(a.distributer_name,'')=nvl(t0.distributer_name_orgi,'')
 and nvl(a.city_name,'')=nvl(t0.city_name,'')
 and nvl(a.Ka_name,'')=nvl(t0.Ka_name,'')
 and nvl(a.dist_type,'')=nvl(t0.dist_type,'')
 and nvl(a.bu_2,'')=nvl(t0.bu_2,'')
 left join  (
     select distinct bu,store_id_tp,begin_month,end_month,return_rate
     from ${dme_cdm}.dwd_city_attack_return_rsp_rate_ecom
      where ds=max_pt('${dme_cdm}.dwd_city_attack_return_rsp_rate_ecom')
      and store_id_tp in ('10231339','765276150')
    )  t3   -- 手工退货率
  on a.bu_2=t3.bu
  and a.ka_code_tp=t3.store_id_tp
  and b.months>=t3.begin_month
  and b.months<t3.end_month
 where a.ds=max_pt('${dme_ads}.tb_sales_city_attack_summry')
 group by  b.year
   ,b.months
   ,a.city_name  -- 城市
   ,a.Ka_code -- KA编码
   ,a.Ka_name -- KA名称
   ,a.Ka_code_tp -- ecom放TP侧门店id，线下是ka编码
   ,a.Ka_name_tp -- ecom放TP侧门店id，线下是ka编码
   ,case when upper(a.first_channel_name) in ('NKA','SELECTIVE RETAILER') and a.dist_type='NKA直供' then
         case when a.ka_code in ('KA0010','KA0070','KA0006','KA0011','KA0001','KA0007','KA0005','KA0004') then a.ka_name_en
         -- case when a.Ka_name regexp '欧尚'     then 'Auchan'
         --      when a.Ka_name regexp '乐购'     then 'Tesco'
         --      when a.Ka_name regexp '家乐福'   then 'Carrefour'
         --      when a.Ka_name regexp '迪亚'     then 'DIA'
         --      when a.Ka_name regexp '天津家乐' then 'HomeClub'
         --      when a.Ka_name regexp '卜蜂莲花' then 'LOTUS'
         --      when a.Ka_name regexp '万宁'     then 'Mannings'
         --      when a.Ka_name regexp '麦德龙'   then 'Metro'
         --      when a.Ka_name regexp '农工商'   then 'NGS'
         --      when a.Ka_name regexp '大润发'   then 'RT'
         --      when a.Ka_name regexp '山姆'     then 'Sams'
         --      when a.Ka_name regexp '沃尔玛'   then 'WAL'
         --      when a.Ka_name regexp '华润万家' then 'Wanjia'
         --      when a.Ka_name regexp '屈臣氏'   then 'Watsons'
         --      when a.Ka_name regexp '莎莎'     then 'SaSa'
           else nvl(t0.distributer_code,a.distributer_code) end
       else nvl(t0.distributer_code,a.distributer_code)
     end  -- 客户code
   ,case when upper(a.first_channel_name) in ('NKA','SELECTIVE RETAILER')  and a.dist_type='NKA直供' then '公司直供'
      else nvl(t0.distributer_name,a.distributer_name)
     end   -- 客户名称
   ,a.bu_1
   ,a.bu_2
   ,a.first_channel_name
   ,a.dist_type
;

drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp4_02 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp4_02 as
 select
   a.year
   ,a.months
   ,a.city_name        -- 城市
   ,a.Ka_name          -- KA名称
   ,a.distributer_code -- 客户code
   ,a.distributer_name -- 客户名称
   ,a.bu_1
   ,a.bu_2
   ,a.first_channel_name
   ,a.dist_type -- 经销商类型
   ,sum(a.Base_sale_amt_Jan) as Base_sale_amt_Jan  -- 1月份退货后基价销售额（未税）
   ,sum(a.Base_sale_amt_Feb) as Base_sale_amt_Feb  -- 2月份退货后基价销售额（未税）
   ,sum(a.Base_sale_amt_Mar) as Base_sale_amt_Mar  -- 3月份退货后基价销售额（未税）
   ,sum(a.Base_sale_amt_Apr) as Base_sale_amt_Apr  -- 4月份退货后基价销售额（未税）
   ,sum(a.Base_sale_amt_May) as Base_sale_amt_May  -- 5月份退货后基价销售额（未税）
   ,sum(a.Base_sale_amt_Jun) as Base_sale_amt_Jun  -- 6月份退货后基价销售额（未税）
   ,sum(a.Base_sale_amt_Jul) as Base_sale_amt_Jul  -- 7月份退货后基价销售额（未税）
   ,sum(a.Base_sale_amt_Aug) as Base_sale_amt_Aug  -- 8月份退货后基价销售额（未税）
   ,sum(a.Base_sale_amt_Sep) as Base_sale_amt_Sep  -- 9月份退货后基价销售额（未税）
   ,sum(a.Base_sale_amt_Oct) as Base_sale_amt_Oct  -- 10月份退货后基价销售额（未税）
   ,sum(a.Base_sale_amt_Nov) as Base_sale_amt_Nov  -- 11月份退货后基价销售额（未税）
   ,sum(a.Base_sale_amt_Dec) as Base_sale_amt_Dec  -- 12月份退货后基价销售额（未税）
   ,sum(a.base_sale_amt_ytd) as base_sale_amt_ytd  -- YTD退货后基价销售额（未税）
   ,sum(a.sales_amt_ytd    ) as sales_amt_ytd      -- YTD退货后销售额（未税）
   ,max(b.shop_gmv_ytd     ) as shop_gmv_ytd       -- 店铺GMV未税(YTD)
   ,max(c1.Rate_Value      ) as contract_Rate      -- BC 间供合同比例
 from ${dme_ads}.tb_sales_city_attack_customer_tmp4_01 a
 left join (
   select
      year
     ,months
     ,Ka_name          -- KA名称
     ,distributer_code -- 客户code
     ,distributer_name -- 客户名称
     ,bu_1
     ,bu_2
     ,SUM(shop_gmv_ytd) as shop_gmv_ytd  -- 店铺GMV未税(YTD)
   from ${dme_ads}.tb_sales_city_attack_customer_tmp4_01
    where upper(first_channel_name)='ECOM'
    group by year
     ,months
     ,Ka_name          -- KA名称
     ,distributer_code -- 客户code
     ,distributer_name -- 客户名称
     ,bu_1
     ,bu_2
 ) b
   on  a.year = b.year
  and nvl(a.months           ,'')=nvl(b.months           ,'')
  and nvl(a.Ka_name          ,'')=nvl(b.Ka_name          ,'')
  and nvl(a.distributer_code ,'')=nvl(b.distributer_code ,'')
  and nvl(a.distributer_name ,'')=nvl(b.distributer_name ,'')
  and nvl(a.bu_1             ,'')=nvl(b.bu_1             ,'')
  and nvl(a.bu_2             ,'')=nvl(b.bu_2             ,'')
 left join ${dme_cdm}.dwd_city_attack_rebate_contract_rate c1
   on a.bu_2=c1.bu
  and a.Ka_code=c1.dist_code
  and upper(c1.Rate_type) regexp '间供合同比例'
  and a.months>=c1.begin_month
  and a.months<c1.end_month
  and c1.ds=max_pt('${dme_cdm}.dwd_city_attack_rebate_contract_rate')
 group by a.year
   ,a.months
   ,a.city_name        -- 城市
   ,a.Ka_name          -- KA名称
   ,a.distributer_code -- 客户code
   ,a.distributer_name -- 客户名称
   ,a.bu_1
   ,a.bu_2
   ,a.first_channel_name
   ,a.dist_type -- 经销商类型
 ;

drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp4 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp4 as
 select
   a.year
   ,a.months
   ,a.city_name        -- 城市
   ,a.Ka_name          -- KA名称
   ,a.distributer_code -- 客户code
   ,a.distributer_name -- 客户名称
   ,a.bu_1
   ,a.bu_2
   ,a.first_channel_name
   ,a.dist_type -- 经销商类型
   ,a.Base_sale_amt_Jan  -- 1月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Feb  -- 2月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Mar  -- 3月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Apr  -- 4月份退货后基价销售额（未税）
   ,a.Base_sale_amt_May  -- 5月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Jun  -- 6月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Jul  -- 7月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Aug  -- 8月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Sep  -- 9月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Oct  -- 10月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Nov  -- 11月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Dec  -- 12月份退货后基价销售额（未税）
   ,a.base_sale_amt_ytd -- YTD退货后基价销售额（未税）
   ,a.sales_amt_ytd -- YTD退货后销售额（未税）
   ,a.shop_gmv_ytd  -- 店铺GMV未税(YTD)
   ,null as gmv_city_share -- 城市占比
   ,a.contract_Rate      -- BC 间供合同比例
   ,a.city_name as orig_city_name       -- 城市
   ,null as wats_base_amt_online_city_rate  -- 屈臣氏24年线上城市基价销售额比例
   ,null as wats_gmv_online_city_rate -- 屈臣氏24年线上城市GMV比例
 from ${dme_ads}.tb_sales_city_attack_customer_tmp4_02 a
 where nvl(a.dist_type,'')<>'电商(未城市)'
 and if(a.bu_2='SKP',UPPER(a.first_channel_name) regexp 'ECOM|NKA|SELECTIVE RETAILER',1=1)
 and if(a.year='2023' and a.ka_name regexp '屈臣氏',nvl(upper(a.ka_name),'')  regexp 'OFFLINE' ,1=1 )
 
 union all
 -- 屈臣氏线上部分23年数据，用24年基价销额分摊到具体城市
 select
   a.year
   ,a.months
   ,b.city_name        -- 城市
   ,a.Ka_name          -- KA名称
   ,a.distributer_code -- 客户code
   ,a.distributer_name -- 客户名称
   ,a.bu_1
   ,a.bu_2
   ,a.first_channel_name
   ,a.dist_type -- 经销商类型
   ,a.Base_sale_amt_Jan*(b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all)) as Base_sale_amt_Jan -- 1月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Feb*(b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all)) as Base_sale_amt_Feb -- 2月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Mar*(b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all)) as Base_sale_amt_Mar -- 3月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Apr*(b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all)) as Base_sale_amt_Apr -- 4月份退货后基价销售额（未税）
   ,a.Base_sale_amt_May*(b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all)) as Base_sale_amt_May -- 5月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Jun*(b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all)) as Base_sale_amt_Jun -- 6月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Jul*(b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all)) as Base_sale_amt_Jul -- 7月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Aug*(b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all)) as Base_sale_amt_Aug -- 8月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Sep*(b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all)) as Base_sale_amt_Sep -- 9月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Oct*(b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all)) as Base_sale_amt_Oct -- 10月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Nov*(b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all)) as Base_sale_amt_Nov -- 11月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Dec*(b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all)) as Base_sale_amt_Dec -- 12月份退货后基价销售额（未税）
   ,a.base_sale_amt_ytd*(b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all)) as base_sale_amt_ytd -- YTD退货后基价销售额（未税）
   ,a.sales_amt_ytd    *(b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all)) as sales_amt_ytd     -- YTD退货后销售额（未税）
   ,a.shop_gmv_ytd     *(b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all)) as shop_gmv_ytd      -- 店铺GMV未税(YTD)
   ,null as gmv_city_share -- 城市占比
   ,a.contract_Rate        -- BC 间供合同比例
   ,'Others' as orig_city_name       -- 城市
   ,b.base_sale_amt_ytd_city/if(b.base_sale_amt_ytd_all=0,null,b.base_sale_amt_ytd_all) as wats_base_amt_online_city_rate  -- 屈臣氏24年线上城市基价销售额比例
   ,b.sales_amt_ytd_city/if(b.sales_amt_ytd__all=0,null,b.sales_amt_ytd__all)  as wats_gmv_online_city_rate -- 屈臣氏24年线上城市GMV比例
 from (
     select 
         year
         ,months
         ,Ka_name          -- KA名称
         ,distributer_code -- 客户code
         ,distributer_name -- 客户名称
         ,bu_1
         ,bu_2
         ,first_channel_name
         ,dist_type -- 经销商类型
         ,sum(Base_sale_amt_Jan) as Base_sale_amt_Jan -- 1月份退货后基价销售额（未税）
         ,sum(Base_sale_amt_Feb) as Base_sale_amt_Feb -- 2月份退货后基价销售额（未税）
         ,sum(Base_sale_amt_Mar) as Base_sale_amt_Mar -- 3月份退货后基价销售额（未税）
         ,sum(Base_sale_amt_Apr) as Base_sale_amt_Apr -- 4月份退货后基价销售额（未税）
         ,sum(Base_sale_amt_May) as Base_sale_amt_May -- 5月份退货后基价销售额（未税）
         ,sum(Base_sale_amt_Jun) as Base_sale_amt_Jun -- 6月份退货后基价销售额（未税）
         ,sum(Base_sale_amt_Jul) as Base_sale_amt_Jul -- 7月份退货后基价销售额（未税）
         ,sum(Base_sale_amt_Aug) as Base_sale_amt_Aug -- 8月份退货后基价销售额（未税）
         ,sum(Base_sale_amt_Sep) as Base_sale_amt_Sep -- 9月份退货后基价销售额（未税）
         ,sum(Base_sale_amt_Oct) as Base_sale_amt_Oct -- 10月份退货后基价销售额（未税）
         ,sum(Base_sale_amt_Nov) as Base_sale_amt_Nov -- 11月份退货后基价销售额（未税）
         ,sum(Base_sale_amt_Dec) as Base_sale_amt_Dec -- 12月份退货后基价销售额（未税）
         ,sum(base_sale_amt_ytd) as base_sale_amt_ytd -- YTD退货后基价销售额（未税）
         ,sum(sales_amt_ytd    ) as sales_amt_ytd     -- YTD退货后销售额（未税）
         ,sum(shop_gmv_ytd     ) as shop_gmv_ytd      -- 店铺GMV未税(YTD)
         ,max(contract_Rate    ) as contract_Rate    -- BC 间供合同比例
     from ${dme_ads}.tb_sales_city_attack_customer_tmp4_02 
     where year='2023' 
     and ka_name regexp '屈臣氏' 
     and nvl(upper(ka_name),'') not regexp 'OFFLINE'
     group by year
         ,months
         ,Ka_name          -- KA名称
         ,distributer_code -- 客户code
         ,distributer_name -- 客户名称
         ,bu_1
         ,bu_2
         ,first_channel_name
         ,dist_type -- 经销商类型
   ) a
 left join (
     select
         t1.bu_2,t1.city_name,t1.ka_name
         ,sum(t1.base_sale_amt_ytd)over(partition by t1.bu_2,t1.city_name,t1.ka_name) as base_sale_amt_ytd_city
         ,sum(t1.base_sale_amt_ytd)over(partition by t1.bu_2,t1.ka_name) as base_sale_amt_ytd_all
         ,sum(t1.sales_amt_ytd)over(partition by t1.bu_2,t1.city_name,t1.ka_name) as sales_amt_ytd_city
         ,sum(t1.sales_amt_ytd)over(partition by t1.bu_2,t1.ka_name) as sales_amt_ytd__all
     from(
        SELECT bu_2,city_name,ka_name
              ,sum(base_sale_amt_ytd) as base_sale_amt_ytd
              ,sum(sales_amt_ytd) as sales_amt_ytd
        from  ${dme_ads}.tb_sales_city_attack_customer_tmp4_02 
        where year='2024' 
         and ka_name regexp '屈臣氏' 
         and nvl(upper(ka_name),'') not regexp 'OFFLINE'
         and months=to_char(to_date(add_months(getdate(),-1),'yyyy-mm-dd'),'yyyymm')
        -- and case when to_char(now(),'yyyymmdd')<'20240701' then months='202403'
        --   when to_char(now(),'yyyymmdd')<'20241001' then months='202406'
        --   when to_char(now(),'yyyymmdd')<'20250101' then months='202409'
        --  when to_char(now(),'yyyymmdd')>='20250101' then months='202412'
        -- end  -- 季度未过完取上个季度数据做分摊比例
         group by bu_2,city_name,ka_name
     ) t1
 ) b
 on a.bu_2=b.bu_2
 and nvl(a.ka_name,'')=nvl(b.ka_name,'')

 union all
 -- 合并不到城市粒度电商数据,城市GMV用 施华蔻天猫官旗 店铺比例
 select
   a.year
   ,a.months
   ,b.city_name        -- 城市
   ,a.Ka_name          -- KA名称
   ,a.distributer_code -- 客户code
   ,a.distributer_name -- 客户名称
   ,a.bu_1
   ,a.bu_2
   ,a.first_channel_name
   ,a.dist_type -- 经销商类型
   ,null as Base_sale_amt_Jan  -- 1月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Feb  -- 2月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Mar  -- 3月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Apr  -- 4月份退货后基价销售额（未税）
   ,null as Base_sale_amt_May  -- 5月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Jun  -- 6月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Jul  -- 7月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Aug  -- 8月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Sep  -- 9月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Oct  -- 10月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Nov  -- 11月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Dec  -- 12月份退货后基价销售额（未税）
   ,a.base_sale_amt_ytd*(b.sales_amt_ytd_city/if(b.sales_amt_ytd_all=0,null,b.sales_amt_ytd_all)) as base_sale_amt_ytd -- YTD退货后基价销售额（未税）
   ,a.sales_amt_ytd*(b.sales_amt_ytd_city/if(b.sales_amt_ytd_all=0,null,b.sales_amt_ytd_all)) as sales_amt_ytd-- YTD退货后销售额（未税）
   ,a.shop_gmv_ytd  -- 店铺GMV未税(YTD)
   ,null as gmv_city_share -- 城市占比
   ,a.contract_Rate  -- BC 间供合同比例
   ,a.city_name as orig_city_name       -- 城市
   ,null as wats_base_amt_online_city_rate  -- 屈臣氏24年线上城市基价销售额比例
   ,null as wats_gmv_online_city_rate -- 屈臣氏24年线上城市GMV比例
 from ${dme_ads}.tb_sales_city_attack_customer_tmp4_02 a
 left join (
     select distinct
         t1.months,t1.bu_2,t1.city_name
         ,sum(t1.sales_amt_ytd)over(partition by t1.months,t1.bu_2,t1.city_name) as sales_amt_ytd_city
         ,sum(t1.sales_amt_ytd)over(partition by t1.months,t1.bu_2) as sales_amt_ytd_all
     from(
       select months,bu_2,city_name,Ka_name,sum(sales_amt_ytd) as sales_amt_ytd
       from ${dme_ads}.tb_sales_city_attack_customer_tmp4_01 
       where upper(first_channel_name)='ECOM'
       AND Ka_code_tp='14'
       group by months,bu_2,city_name,Ka_name
     ) t1
     -- AND Ka_name='施华蔻天猫官旗'
 ) b
 on a.months=b.months
 and a.bu_2=b.bu_2
 where a.dist_type='电商(未城市)'

 union all
 -- 合并SKP 线下DT WS经销商部分数据(用PL客户信息数据)
 select distinct
   a.years as year
   ,a.months
   ,c.city_name        -- 城市
   ,null as Ka_name          -- KA名称
   ,a.distributer_code as distributer_code -- 客户code
   ,b.customer_name as distributer_name -- 客户名称
   ,a.bu_1
   ,a.bu_2
   ,coalesce(a.channel,b.channel_hierarchy_1,'Others') AS first_channel_name
   ,'专业线下'    as dist_type -- 经销商类型
   ,null as Base_sale_amt_Jan  -- 1月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Feb  -- 2月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Mar  -- 3月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Apr  -- 4月份退货后基价销售额（未税）
   ,null as Base_sale_amt_May  -- 5月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Jun  -- 6月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Jul  -- 7月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Aug  -- 8月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Sep  -- 9月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Oct  -- 10月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Nov  -- 11月份退货后基价销售额（未税）
   ,null as Base_sale_amt_Dec  -- 12月份退货后基价销售额（未税）
   ,null as base_sale_amt_ytd -- YTD退货后基价销售额（未税）
   ,null as sales_amt_ytd-- YTD退货后销售额（未税）
   ,null as shop_gmv_ytd  -- 店铺GMV未税(YTD)
   ,c.gmv_city_share -- 城市占比
   ,null as contract_Rate -- BC 间供合同比例
   ,c.city_name as orig_city_name       -- 城市
   ,null as wats_base_amt_online_city_rate  -- 屈臣氏24年线上城市基价销售额比例
   ,null as wats_gmv_online_city_rate -- 屈臣氏24年线上城市GMV比例
 from ${dme_ads}.tb_sales_city_attack_customer_ws_dt_tmp3 a
 left join (
    select
       customer_code,customer_name,bu_2,channel_hierarchy_1,substr(ds,1,6) as months
    from ${dme_cdm}.dwd_master_data_customer_bu
    where ds like '%01'
    group by customer_code,customer_name,bu_2,channel_hierarchy_1,substr(ds,1,6)
    ) b
 on a.distributer_code=b.customer_code
 and a.bu_2=b.bu_2
 and a.months=b.months
 left join ${dme_cdm}.dwd_city_attack_dist_list c   -- 专业线城市占比
 on a.distributer_code=c.dist_code
 and a.months>=c.begin_month
 and a.months<c.end_month
 and c.ds=max_pt('${dme_cdm}.dwd_city_attack_dist_list')
 where a.bu_2='SKP'
 --AND nvl(upper(b.channel_hierarchy_1),'')<>'ECOM'
;

-- 计算ECOM店铺/经销商所有城市YTD的pos 基价销售额（未税）
drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp5_01 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp5_01 as
select
  a.year
   ,a.months
   ,a.city_name        -- 城市
   ,a.first_channel_name
   ,a.Ka_name          -- KA名称
   ,a.distributer_code -- 客户code
   ,a.distributer_name -- 客户名称
   ,a.bu_1
   ,a.bu_2
   ,a.dist_type -- 经销商类型
   ,sum(a.base_sale_amt_ytd)over(partition by a.year,a.months,a.first_channel_name,a.distributer_code,a.distributer_name,a.bu_1,a.bu_2)
      as  base_sale_amt_ytd_dist -- 经销商所有店铺的 YTD退货后基价销售额（未税）
   ,sum(a.base_sale_amt_ytd)over(partition by a.year,a.months,a.first_channel_name,a.Ka_name,a.bu_1,a.bu_2)
      as  base_sale_amt_ytd_shop -- 店铺所有城市的 YTD退货后基价销售额（未税）
from ${dme_ads}.tb_sales_city_attack_customer_tmp4 a
where upper(a.first_channel_name)='ECOM'
;

-- pos基价销售额（未税）ytd
drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp5 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp5 as
 select
   a.year
   ,a.months
   ,a.city_name        -- 城市
   ,a.first_channel_name
   ,a.Ka_name          -- KA名称
   ,a.distributer_code -- 客户code
   ,a.distributer_name -- 客户名称
   ,a.bu_1
   ,a.bu_2
   ,a.dist_type -- 经销商类型
   ,a.Base_sale_amt_Jan  -- 1月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Feb  -- 2月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Mar  -- 3月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Apr  -- 4月份退货后基价销售额（未税）
   ,a.Base_sale_amt_May  -- 5月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Jun  -- 6月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Jul  -- 7月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Aug  -- 8月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Sep  -- 9月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Oct  -- 10月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Nov  -- 11月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Dec  -- 12月份退货后基价销售额（未税）
   ,a.base_sale_amt_ytd  -- YTD退货后基价销售额（未税）
   ,a.sales_amt_ytd      -- YTD退货后销售额（未税）
   ,a.shop_gmv_ytd  -- 店铺GMV未税(YTD)
   ,cast(case when a.bu_2='Beauty Care'  and a.dist_type in ('NKA间供+LKA','NKA直供','DT Others') then null
         when a.bu_2='SKP'  and a.dist_type ='NKA_专业线' then null
         when a.bu_2 in ('Beauty Care','SKP') and a.dist_type in ('电商(城市)','电商(未城市)') then a.sales_amt_ytd*1.13
         when a.bu_2 in ('Beauty Care','SKP') and a.dist_type in ('电商(手工_城市)') then a.sales_amt_ytd*1.13
    --   when a.bu_2='Beauty Care' and a.dist_type = '电商(未城市)'  then ****
    --   when a.bu_2='Beauty Care' and a.dist_type = '电商(手工_城市)' then ****
    --   when a.bu_1='Professional' and a.dist_type = '电商(城市)' then null
     end as decimal(38,18))  as gmv_city    -- 城市GMV
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供','DT Others') then null
         when a.bu_2='SKP' and a.dist_type ='NKA_专业线' then null
       when a.bu_2 in ('Beauty Care','SKP') and a.dist_type regexp '电商' then a.shop_gmv_ytd*1.13      -- YTD销售额（含税）
     end   as gmv           -- 店铺GMV
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供','DT Others') then null
         when a.bu_2='Beauty Care' and a.dist_type in ('电商(城市)','电商(未城市)') then a.sales_amt_ytd*1.13/if(a.shop_gmv_ytd=0,null,a.shop_gmv_ytd*1.13)
         when a.bu_2='Beauty Care' and a.dist_type in ('电商(手工_城市)') then a.sales_amt_ytd*1.13/if(a.shop_gmv_ytd=0,null,a.shop_gmv_ytd*1.13)
         when a.bu_2='SKP' and a.dist_type regexp '电商' then null
         when a.bu_2='SKP' and a.dist_type ='NKA_专业线' then null
         WHEN a.bu_2='SKP' and a.dist_type = '专业线下' then a.gmv_city_share
     end   as Ratio_Rate    -- 城市占比
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供','DT Others','电商(城市)') then a.base_sale_amt_ytd  -- YTD退货后基价销售额（未税）
         when a.bu_2='SKP' and a.dist_type in ('电商(城市)','NKA_专业线') then a.base_sale_amt_ytd
         WHEN a.bu_2='SKP' and a.dist_type = '专业线下' then b.Orig_GES * a.gmv_city_share
     end   as GES
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then b.PLD_Rate
         when a.bu_2='SKP' then b.PLD_Rate
     end   as PLD_Rate
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then b.PPD_Rate
         when a.bu_2='SKP' then b.PPD_Rate
     end   as PPD_Rate
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then b.FG_Rate
         when a.bu_2='SKP' then b.FG_Rate
     end   as FG_Rate
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then b.PLD_Rate*a.base_sale_amt_ytd
         when a.bu_2='SKP' and a.dist_type in ('电商(城市)','NKA_专业线') then a.base_sale_amt_ytd *b.PLD_Rate
         WHEN a.bu_2='SKP' and nvl(a.dist_type,'') not regexp '电商' then b.Orig_GES * a.gmv_city_share *b.PLD_Rate
     end   as PLD
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then b.PPD_Rate*a.base_sale_amt_ytd
         when a.bu_2='SKP' and a.dist_type in ('电商(城市)','NKA_专业线') then a.base_sale_amt_ytd *b.PPD_Rate
         WHEN a.bu_2='SKP' and nvl(a.dist_type,'') not regexp '电商' then b.Orig_GES * a.gmv_city_share *b.PPD_Rate
     end   as PPD
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then b.FG_Rate*a.base_sale_amt_ytd
         when a.bu_2='Beauty Care' and a.dist_type in ('电商(城市)','电商(未城市)') then (d.base_sale_amt_ytd_shop/if(d.base_sale_amt_ytd_dist=0,null,d.base_sale_amt_ytd_dist))
            * (a.sales_amt_ytd*1.13/if(a.shop_gmv_ytd=0,null,a.shop_gmv_ytd*1.13)) *b.Orig_FG
         when a.bu_2='Beauty Care' and a.dist_type in ('电商(手工_城市)') then (d.base_sale_amt_ytd_shop/if(d.base_sale_amt_ytd_dist=0,null,d.base_sale_amt_ytd_dist))
            * (a.sales_amt_ytd/if(a.shop_gmv_ytd=0,null,a.shop_gmv_ytd*1.13)) *b.Orig_FG
         when a.bu_2='SKP' and a.dist_type in ('电商(城市)','NKA_专业线') then a.base_sale_amt_ytd *b.FG_Rate
         WHEN a.bu_2='SKP' and a.dist_type regexp '专业线下' then b.Orig_GES * a.gmv_city_share *b.FG_Rate
     end   as FG
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then nvl(a.base_sale_amt_ytd,0)*(1-nvl(b.PLD_Rate,0)-nvl(b.PPD_Rate,0)-nvl(b.FG_Rate,0))
         when a.bu_2='SKP' and a.dist_type in ('电商(城市)','NKA_专业线') then nvl(a.base_sale_amt_ytd,0)*(1-nvl(b.PLD_Rate,0)-nvl(b.PPD_Rate,0)-nvl(b.FG_Rate,0))
         WHEN a.bu_2='SKP' and a.dist_type regexp '专业线下' then b.Orig_GES * a.gmv_city_share *(1-nvl(b.PLD_Rate,0)-nvl(b.PPD_Rate,0)-nvl(b.FG_Rate,0))
     end   as NGS
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA直供') then b.Rebate_Rate
         when a.bu_2='Beauty Care' and (a.dist_type in ('NKA间供+LKA') or a.dist_type like '%电商%') and upper(c.Rate_type) regexp 'REBATE' then nvl(c.Rate_Value,0)
         when a.bu_2='SKP' then b.Orig_rebate /if(b.Orig_NGS=0,null,b.Orig_NGS)
     end   as Rebate_Rate
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then b.CA_Rate
         when a.bu_2='Beauty Care' and a.dist_type regexp '电商' then b.CA_Rate  
     end   as CA_Rate
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then b.logistic_fee_Rate
         when a.bu_2='SKP' then b.Orig_logistic_fee /if(b.Orig_NGS=0,null,b.Orig_NGS)
         when a.bu_2='Beauty Care' and a.dist_type regexp '电商' then b.logistic_fee_Rate  
     end   as Logistics_Rate
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA直供') then 0
         when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA') then nvl(a.contract_Rate,0)
     end   as contract_Rate
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('电商(城市)','电商(未城市)') then (d.base_sale_amt_ytd_shop/if(d.base_sale_amt_ytd_dist=0,null,d.base_sale_amt_ytd_dist))
            * (a.sales_amt_ytd*1.13/if(a.shop_gmv_ytd=0,null,a.shop_gmv_ytd*1.13)) *b.Orig_Rebate
         when a.bu_2='Beauty Care' and a.dist_type in ('电商(手工_城市)') then (d.base_sale_amt_ytd_shop/if(d.base_sale_amt_ytd_dist=0,null,d.base_sale_amt_ytd_dist))
            * (a.sales_amt_ytd*1.13/if(a.shop_gmv_ytd=0,null,a.shop_gmv_ytd*1.13)) *b.Orig_Rebate
     end   as Rebate
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('电商(城市)','电商(未城市)') then (d.base_sale_amt_ytd_shop/if(d.base_sale_amt_ytd_dist=0,null,d.base_sale_amt_ytd_dist))
            * (a.sales_amt_ytd*1.13/if(a.shop_gmv_ytd=0,null,a.shop_gmv_ytd*1.13)) *b.Orig_CA
         when a.bu_2='Beauty Care' and a.dist_type in ('电商(手工_城市)') then (d.base_sale_amt_ytd_shop/if(d.base_sale_amt_ytd_dist=0,null,d.base_sale_amt_ytd_dist))
            * (a.sales_amt_ytd*1.13/if(a.shop_gmv_ytd=0,null,a.shop_gmv_ytd*1.13)) *b.Orig_CA
     end   as CA
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('电商(城市)','电商(未城市)') then (d.base_sale_amt_ytd_shop/if(d.base_sale_amt_ytd_dist=0,null,d.base_sale_amt_ytd_dist))
            * (a.sales_amt_ytd*1.13/if(a.shop_gmv_ytd=0,null,a.shop_gmv_ytd*1.13)) *b.Orig_logistic_fee
         when a.bu_2='Beauty Care' and a.dist_type in ('电商(手工_城市)') then (d.base_sale_amt_ytd_shop/if(d.base_sale_amt_ytd_dist=0,null,d.base_sale_amt_ytd_dist))
            * (a.sales_amt_ytd*1.13/if(a.shop_gmv_ytd=0,null,a.shop_gmv_ytd*1.13)) *b.Orig_logistic_fee
     end   as Logistics
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then b.Other_investment_Rate end as Other_investment_Rate
   ,case when a.bu_2 ='SKP' or (a.bu_2='Beauty Care' and nvl(a.dist_type,'')<>'DT Others') then b.l10_commission_Rate end as L10_Rate
   ,case when a.bu_2 ='SKP' or (a.bu_2='Beauty Care' and nvl(a.dist_type,'')<>'DT Others') then b.l11_t_w_Rate end as L11_Rate
   ,case when a.bu_2 ='SKP' or (a.bu_2='Beauty Care' and nvl(a.dist_type,'')<>'DT Others') then b.l14_cog_Rate end as L14_Rate
   ,case when a.bu_2 ='SKP' or (a.bu_2='Beauty Care' and nvl(a.dist_type,'')<>'DT Others') then b.l16_umc_Rate end as L16_Rate
   ,case when a.bu_2 ='SKP'  then b.L17_total_Rate end as L17_Rate
   ,case when nvl(a.dist_type,'')<>'DT Others' then b.l17_total_Rate end as L17_total_Rate
   ,case when nvl(a.dist_type,'')<>'DT Others' then b.l17_opcb_Rate end as L17_opcb_Rate
   ,b.Orig_NGS_MONTHLY            -- 月的 Net_Gross_Sales，净销售总额
   ,b.Orig_rebate
   ,b.Orig_CA
   ,b.Orig_PLD
   ,b.Orig_PPD
   ,b.Orig_FG
   ,b.Orig_GES
   ,b.Orig_NGS
   ,b.Orig_logistic_fee
   ,b.Orig_listing_fee
   ,b.Orig_nka_expense
   ,b.Orig_2nd_dis_dm_others
   ,b.Orig_l10_commission
   ,b.Orig_l11_t_w
   ,b.Orig_l14_cog
   ,b.Orig_l16_umc
   ,b.Orig_l17_total
   ,b.Orig_l17_nka_tm_o2o
   ,b.Orig_l17_channel
   ,b.Orig_l17_py
   ,b.Orig_l17_ba
   ,b.Orig_l17_mkt
   ,b.Orig_l17_digital
   ,b.Orig_lka_contract_fee       -- Lka合同返利
   ,b.Orig_indirect_rebate        -- 间供返利
   ,a.wats_base_amt_online_city_rate  -- 屈臣氏24年线上城市基价销售额比例
   ,a.wats_gmv_online_city_rate -- 屈臣氏24年线上城市GMV比例
 from ${dme_ads}.tb_sales_city_attack_customer_tmp4 a
 left join ${dme_ads}.tb_sales_city_attack_customer_tmp3 b
 on a.months=b.months
 and nvl(a.distributer_code  ,'')=nvl(b.distributer_code,'')
 and nvl(a.distributer_name  ,'')=nvl(b.distributer_name,'')
 and nvl(a.first_channel_name,'')=nvl(b.first_channel_name,'')
 and nvl(a.orig_city_name,'')=nvl(b.city_name,'')
 and nvl(a.Ka_name  ,'')=nvl(b.Ka_name,'')
 and nvl(a.bu_2     ,'')=nvl(b.bu_2,'')
 left join ${dme_cdm}.dwd_city_attack_rebate_contract_rate c
 on a.bu_2=c.bu
 and a.distributer_code=c.dist_code
 and upper(c.Rate_type) regexp 'REBATE'
 and a.months>=c.begin_month
 and a.months<c.end_month
 and c.ds=max_pt('${dme_cdm}.dwd_city_attack_rebate_contract_rate')
 -- left join ${dme_cdm}.dwd_city_attack_rebate_contract_rate c1
 -- on a.bu_2=c1.bu
 -- and case when a.Ka_name regexp '屈臣氏' then '屈臣氏' else a.Ka_name end=c1.dist_code
 -- and upper(c1.Rate_type) regexp '间供合同比例'
 -- and a.months>=c1.begin_month
 -- and a.months<c1.end_month
 -- and c1.ds=max_pt('${dme_cdm}.dwd_city_attack_rebate_contract_rate')
 left join ${dme_ads}.tb_sales_city_attack_customer_tmp5_01 d  -- 计算ECOM店铺/经销商所有城市YTD的pos 基价销售额（未税）
   on nvl(a.year              ,'')=nvl(d.year              ,'')
  and nvl(a.months            ,'')=nvl(d.months            ,'')
  and nvl(a.city_name         ,'')=nvl(d.city_name         ,'')
  and nvl(a.first_channel_name,'')=nvl(d.first_channel_name,'')
  and nvl(a.Ka_name           ,'')=nvl(d.Ka_name           ,'')
  and nvl(a.distributer_code  ,'')=nvl(d.distributer_code  ,'')
  and nvl(a.distributer_name  ,'')=nvl(d.distributer_name  ,'')
  and nvl(a.bu_1              ,'')=nvl(d.bu_1              ,'')
  and nvl(a.bu_2              ,'')=nvl(d.bu_2              ,'')
  and nvl(a.dist_type         ,'')=nvl(d.dist_type         ,'')
 ;


---- 手工L17数据YTD计算
--drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp6_01 ;
--create table ${dme_ads}.tb_sales_city_attack_customer_tmp6_01 as
--select
--  t.months,t.years,t.bu,t.city_name
--  ,sum(cast(t1.L17 as decimal(38,18))) over(partition by t.years,t.bu,t.city_name order by t.months asc) as L17_YTD
--from(
--   select b.months,b.years,a.bu,a.city_name
--   from (
--    select
--      bu
--      ,city_name
--      ,substr(months,1,4) as years
--    from ${dme_ods}.s_city_attack_city_l17
--     where ds=max_pt('${dme_cdm}.s_city_attack_city_l17')
--    group by bu,city_name,substr(months,1,4)
--   ) a
--   left join (
--       select month_id as months,substr(month_id,1,4) as years
--       from ${dme_cdm}.dim_day
--       where month_id >='202001' and month_id <='${bizmonth}'
--       group by month_id,substr(month_id,1,4)
--   ) b
--   on a.years=b.years
--) t
--left join ${dme_ods}.s_city_attack_city_l17 t1
--on t.months=t1.months
--and t.bu=t1.bu
--and replace(t.city_name,'市','')=replace(t1.city_name,'市','')
--and t1.ds=max_pt('${dme_cdm}.s_city_attack_city_l17')
--;

-- 该城市所有经销商的账面YTD L17(MKT+Digital) 、该城市所有经销商的账面YTD GES ，计算L17使用
drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp6_02 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp6_02 as
select
  t.months,t.bu_2,t.city_name
  ,max(t.Orig_l17_mkt)      as Orig_l17_mkt_ytd
  ,max(t.Orig_l17_digital)  as Orig_l17_digital_ytd
  ,max(t.Orig_GES)  as Orig_GES_ytd
  ,sum(t1.L17)  as L17_City_Investment
  ,(max(nvl(t.Orig_l17_mkt,0)+nvl(t.Orig_l17_digital,0)) - nvl(sum(cast(t1.L17 as decimal(38,18))),0))
     / max(if(t.Orig_GES=0,null,t.Orig_GES))  as L17_Rate_city
from (
  select months,bu_2,city_name
      ,sum(Orig_l17_mkt    ) as Orig_l17_mkt
      ,sum(Orig_l17_digital) as Orig_l17_digital
      ,sum(Orig_GES        ) as Orig_GES
  from(
   select distinct
       months,bu_2
      ,distributer_code -- 客户code
      ,city_name
      ,retail_Orig_l17_mkt as Orig_l17_mkt
      ,retail_Orig_l17_digital as Orig_l17_digital
      ,retail_Orig_GES as Orig_GES
   from ${dme_ads}.tb_sales_city_attack_customer_tmp3_03
   )
   group by months,bu_2,city_name
  ) t
left join (
  select
     months    -- 数据月份
    ,city_name -- 城市
    ,sum(L17)  as L17
  from ${dme_cdm}.dwd_city_attack_city_l17
  where ds=max_pt('${dme_cdm}.dwd_city_attack_city_l17')
  and bu in ('Beauty Care','Laundry')
  group by months    -- 数据月份
    ,city_name
  ) t1
on t.months>=t1.months
and substr(t.months,1,4)=substr(t1.months,1,4)
and replace(t.city_name,'市','')=replace(t1.city_name,'市','')
group by t.months,t.bu_2,t.city_name
;

drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp6 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp6 as
 select
   a.year
   ,a.months
   ,a.city_name        -- 城市
   ,a.first_channel_name
   ,a.Ka_name          -- KA名称
   ,a.distributer_code -- 客户code
   ,a.distributer_name -- 客户名称
   ,a.bu_1
   ,a.bu_2
   ,a.dist_type -- 经销商类型
   ,a.Base_sale_amt_Jan  -- 1月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Feb  -- 2月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Mar  -- 3月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Apr  -- 4月份退货后基价销售额（未税）
   ,a.Base_sale_amt_May  -- 5月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Jun  -- 6月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Jul  -- 7月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Aug  -- 8月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Sep  -- 9月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Oct  -- 10月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Nov  -- 11月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Dec  -- 12月份退货后基价销售额（未税）
   ,a.base_sale_amt_ytd  -- YTD退货后基价销售额（未税）
   ,a.sales_amt_ytd      -- YTD退货后销售额（未税）
   ,a.gmv_city    -- 城市GMV
   ,a.gmv         -- 店铺GMV
   ,a.Ratio_Rate  -- 城市占比    
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('电商(手工_城市)','电商(未城市)') then nvl(a.gmv_city/t3.avg_discount_rate*t2.index_value,0)+nvl(a.FG,0)
         when a.bu_2='SKP' and a.dist_type in ('电商(手工_城市)','电商(未城市)') then nvl(a.gmv_city/t3.avg_discount_rate*t2.index_value,0)* (1+nvl(a.FG_Rate,0))
      else a.GES
    end as GES
   ,a.PLD_Rate
   ,a.PPD_Rate
   ,a.FG_Rate
   ,a.PLD
   ,a.PPD
   ,case when a.bu_2='SKP' and a.dist_type in ('电商(手工_城市)','电商(未城市)') then nvl(a.gmv_city/t3.avg_discount_rate*t2.index_value,0)*a.FG_Rate
      else a.FG
    end FG
   ,case when a.bu_2='Beauty Care' and a.dist_type = '电商(城市)' then (nvl(a.GES,0)-nvl(a.FG,0))/t2.index_value*t1.discount_rate
        when a.bu_2 IN ('Beauty Care','SKP') and a.dist_type in ('电商(手工_城市)','电商(未城市)') then a.gmv_city/t3.avg_discount_rate*t1.discount_rate
      else a.NGS
    end as NGS
   ,a.Rebate_Rate
   ,a.CA_Rate
   ,a.Logistics_Rate
   ,case when a.bu_2='Beauty Care' and a.dist_type regexp '电商' then null
         when a.bu_2='SKP' then null
       else a.contract_Rate
    end as contract_Rate
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then a.NGS* a.Rebate_Rate
      else a.Rebate
    end as Rebate
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then a.NGS* a.CA_Rate
         when a.bu_2='SKP' then null
      else a.CA
    end as CA
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then a.NGS* a.Logistics_Rate
      else a.Logistics
    end as Logistics
   ,case when a.bu_2='Beauty Care' and a.dist_type ='NKA间供+LKA' and a.first_channel_name='NKA' then a.NGS* a.contract_Rate
         when a.bu_2='Beauty Care' and a.dist_type regexp '电商|NKA直供' then null
         when a.bu_2='SKP' then null
    end as Indirect_Rebate
   ,case when a.bu_2='Beauty Care' and a.dist_type ='NKA间供+LKA' and a.first_channel_name='LKA' then a.NGS* a.contract_Rate
         when a.bu_2='Beauty Care' and a.dist_type regexp '电商|NKA直供' then null
         when a.bu_2='SKP' then null
    end as LKA_contract_fee
   ,case when a.bu_2='Beauty Care' and a.dist_type regexp '电商' then null
         when a.bu_2='SKP' then null
      else a.Other_investment_Rate
    end as Other_investment_Rate
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then a.NGS* a.Other_investment_Rate
         when a.bu_2='Beauty Care' and a.dist_type regexp '电商' then null
         when a.bu_2='SKP' then null
    end as Other_investment
   ,a.L10_Rate
   ,a.L11_Rate
   ,a.L14_Rate
   ,a.L16_Rate
   ,a.L17_Rate
   ,a.L17_total_Rate
   ,a.L17_opcb_Rate
   ,b.L17_Rate_city
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then a.GES*a.L10_Rate
         when a.bu_2='SKP' and a.dist_type in ('电商(城市)','专业线下','NKA_专业线') then a.GES*a.L10_Rate
         when a.bu_2='SKP' and a.dist_type in ('电商(手工_城市)','电商(未城市)') then nvl(a.gmv_city/t3.avg_discount_rate*t2.index_value,0)* (1+nvl(a.FG_Rate,0))*a.L10_Rate
     end as L10
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then a.GES*a.L11_Rate
         when a.bu_2='SKP' and a.dist_type in ('电商(城市)','专业线下','NKA_专业线') then a.GES*a.L11_Rate
         when a.bu_2='SKP' and a.dist_type in ('电商(手工_城市)','电商(未城市)') then nvl(a.gmv_city/t3.avg_discount_rate*t2.index_value,0)* (1+nvl(a.FG_Rate,0))*a.L11_Rate
     end as L11
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then a.GES*a.L14_Rate
         when a.bu_2='SKP' and a.dist_type in ('电商(城市)','专业线下','NKA_专业线') then a.GES*a.L14_Rate
         when a.bu_2='SKP' and a.dist_type in ('电商(手工_城市)','电商(未城市)') then nvl(a.gmv_city/t3.avg_discount_rate*t2.index_value,0)* (1+nvl(a.FG_Rate,0))*a.L14_Rate
     end as L14
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供') then a.GES*a.L16_Rate
         when a.bu_2='SKP' and a.dist_type in ('电商(城市)','专业线下','NKA_专业线') then a.GES*a.L16_Rate
         when a.bu_2='SKP' and a.dist_type in ('电商(手工_城市)','电商(未城市)') then nvl(a.gmv_city/t3.avg_discount_rate*t2.index_value,0)* (1+nvl(a.FG_Rate,0))*a.L16_Rate
     end as L16
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供','电商(城市)') then a.GES*  (nvl(a.L17_opcb_Rate,0)+nvl(b.L17_Rate_city,0))
         when a.bu_2='Beauty Care' and a.dist_type in ('电商(手工_城市)','电商(未城市)') then 
         (nvl(a.gmv_city/t3.avg_discount_rate*t2.index_value,0)+nvl(a.FG,0))* (nvl(a.L17_opcb_Rate,0)+nvl(b.L17_Rate_city,0))
     end as L17
   ,a.Orig_NGS_MONTHLY            -- 月的 Net_Gross_Sales，净销售总额
   ,a.Orig_rebate
   ,a.Orig_CA
   ,a.Orig_PLD
   ,a.Orig_PPD
   ,a.Orig_FG
   ,a.Orig_GES
   ,a.Orig_NGS
   ,a.Orig_logistic_fee
   ,a.Orig_listing_fee
   ,a.Orig_nka_expense
   ,a.Orig_2nd_dis_dm_others
   ,a.Orig_l10_commission
   ,a.Orig_l11_t_w
   ,a.Orig_l14_cog
   ,a.Orig_l16_umc
   ,a.Orig_l17_total
   ,a.Orig_l17_nka_tm_o2o
   ,a.Orig_l17_channel
   ,a.Orig_l17_py
   ,a.Orig_l17_ba
   ,a.Orig_l17_mkt
   ,a.Orig_l17_digital
   ,a.Orig_lka_contract_fee       -- Lka合同返利
   ,a.Orig_indirect_rebate        -- 间供返利
   ,a.wats_base_amt_online_city_rate  -- 屈臣氏24年线上城市基价销售额比例
   ,a.wats_gmv_online_city_rate -- 屈臣氏24年线上城市GMV比例
 from ${dme_ads}.tb_sales_city_attack_customer_tmp5 a
 left join  ${dme_ads}.tb_sales_city_attack_customer_tmp6_02 b  -- 该城市所有经销商的账面YTD 数据
  on a.months=b.months
  and a.bu_2=b.bu_2
  and a.city_name=b.city_name
 left join ${dme_cdm}.dwd_city_attack_discount_rate_ecom t1  -- 电商供货折扣率
  on a.bu_2=t1.bu
  and a.months>=t1.begin_month
  and a.months<t1.end_month
  and t1.ds=max_pt('${dme_cdm}.dwd_city_attack_discount_rate_ecom')
 left join ${dme_cdm}.dwd_city_attack_weight_base_price_rate t2   -- 基价转换率
  on a.bu_2=t2.bu
  and a.months>=t2.begin_month
  and a.months<t2.end_month
  and t2.ds=max_pt('${dme_cdm}.dwd_city_attack_weight_base_price_rate')
  and t2.index_name='base_price_rate'  -- 基价转换率
 left join (
     select distinct bu,store_name,begin_month,end_month,avg_discount_rate
     from ${dme_cdm}.dwd_city_attack_return_rsp_rate_ecom
      where ds=max_pt('${dme_cdm}.dwd_city_attack_return_rsp_rate_ecom')
    ) t3   -- YTD平均折扣率
  on a.bu_2=t3.bu
  and case when a.Ka_name regexp '屈臣氏' then '屈臣氏' else a.Ka_name end=t3.store_name
  and a.months>=t3.begin_month
  and a.months<t3.end_month


 ;

drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp7 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp7 as
 select
   a.year
   ,a.months
   ,a.city_name        -- 城市
   ,a.first_channel_name
   ,a.Ka_name          -- KA名称
   ,a.distributer_code -- 客户code
   ,a.distributer_name -- 客户名称
   ,a.bu_1
   ,a.bu_2
   ,a.dist_type -- 经销商类型
   ,a.Base_sale_amt_Jan  -- 1月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Feb  -- 2月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Mar  -- 3月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Apr  -- 4月份退货后基价销售额（未税）
   ,a.Base_sale_amt_May  -- 5月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Jun  -- 6月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Jul  -- 7月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Aug  -- 8月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Sep  -- 9月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Oct  -- 10月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Nov  -- 11月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Dec  -- 12月份退货后基价销售额（未税）
   ,a.base_sale_amt_ytd  -- YTD退货后基价销售额（未税）
   ,a.sales_amt_ytd      -- YTD退货后销售额（未税）
   ,a.gmv_city    -- 城市GMV
   ,a.gmv           -- 店铺GMV
   ,a.Ratio_Rate
   ,a.GES
   ,case when a.bu_2='Beauty Care' and a.dist_type regexp '电商' then (nvl(a.GES,0)-nvl(a.NGS,0)-nvl(a.FG,0))/if(a.GES=0,null,a.GES)
      else a.PLD_Rate
    end as PLD_Rate
   ,case when a.bu_2='Beauty Care' and a.dist_type regexp '电商' then 0
      else a.PPD_Rate
    end as PPD_Rate
   ,case when a.bu_2='Beauty Care' and a.dist_type regexp '电商' then a.FG/if(a.GES=0,null,a.GES)
      else a.FG_Rate
    end as FG_Rate
   ,case when a.bu_2='Beauty Care' and a.dist_type  regexp '电商' then nvl(a.GES,0)-nvl(a.NGS,0)-nvl(a.FG,0)
         when a.bu_2='SKP' and a.dist_type in ('电商(手工_城市)','电商(未城市)') then a.GES * a.PLD_Rate
      else a.PLD
    end as PLD
   ,case when a.bu_2='Beauty Care' and a.dist_type  regexp '电商' then 0
         when a.bu_2='SKP' and a.dist_type in ('电商(手工_城市)','电商(未城市)') then a.GES * a.PPD_Rate
      else a.PPD
    end as PPD
   ,a.FG
   ,a.NGS
   ,a.Rebate_Rate
   --,case when a.bu_2='Beauty Care' and a.dist_type like '%电商%' then 0.25
   --   else a.Rebate_Rate
   -- end as Rebate_Rate
   ,a.CA_Rate        as CA_Rate
   ,a.Logistics_Rate as Logistics_Rate
   ,a.contract_Rate
   ,case when a.bu_2='SKP' then a.NGS * a.Rebate_Rate
         when a.bu_2='Beauty Care' and a.dist_type like '%电商%' then 0.25*a.NGS
        else a.Rebate
      end as Rebate
   ,case when a.bu_2='Beauty Care' and a.dist_type like '%电商%' then a.CA_Rate*a.NGS
         else a.CA
      end as CA
   ,case when a.bu_2='SKP' then a.NGS * a.Logistics_Rate
         when a.bu_2='Beauty Care' and a.dist_type like '%电商%' then a.Logistics_Rate*a.NGS
        else a.Logistics
      end as Logistics
   ,a.Indirect_Rebate
   ,a.LKA_contract_fee
   ,a.Other_investment_Rate
   ,a.Other_investment
   ,a.L10_Rate
   ,a.L11_Rate
   ,a.L14_Rate
   ,a.L16_Rate
   ,case when a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA','NKA直供','电商(城市)','电商(手工_城市)','电商(未城市)')
      then a.L17/IF(a.GES=0,NULL,A.ges)
         else a.L17_Rate
     end as L17_Rate
   ,a.L17_total_Rate
   ,a.L17_opcb_Rate
   ,a.L17_Rate_city
   ,case when a.bu_2='Beauty Care' and a.dist_type  regexp '电商' then a.GES*a.L10_Rate
      else a.L10
    end as L10
   ,case when a.bu_2='Beauty Care' and a.dist_type  regexp '电商' then a.GES*a.L11_Rate
      else a.L11
    end as L11
   ,case when a.bu_2='Beauty Care' and a.dist_type  regexp '电商' then a.GES*a.L14_Rate
      else a.L14
    end as L14
   ,case when a.bu_2='Beauty Care' and a.dist_type  regexp '电商' then a.GES*a.L16_Rate
      else a.L16
    end as L16
   ,case when a.bu_2='SKP' then a.GES*a.L17_Rate
      else a.L17
    end as L17
   ,a.Orig_NGS_MONTHLY            -- 月的 Net_Gross_Sales，净销售总额
   ,a.Orig_rebate
   ,a.Orig_CA
   ,a.Orig_PLD
   ,a.Orig_PPD
   ,a.Orig_FG
   ,a.Orig_GES
   ,a.Orig_NGS
   ,a.Orig_logistic_fee
   ,a.Orig_listing_fee
   ,a.Orig_nka_expense
   ,a.Orig_2nd_dis_dm_others
   ,a.Orig_l10_commission
   ,a.Orig_l11_t_w
   ,a.Orig_l14_cog
   ,a.Orig_l16_umc
   ,a.Orig_l17_total
   ,a.Orig_l17_nka_tm_o2o
   ,a.Orig_l17_channel
   ,a.Orig_l17_py
   ,a.Orig_l17_ba
   ,a.Orig_l17_mkt
   ,a.Orig_l17_digital
   ,a.Orig_lka_contract_fee       -- Lka合同返利
   ,a.Orig_indirect_rebate        -- 间供返利
   ,a.wats_base_amt_online_city_rate  -- 屈臣氏24年线上城市基价销售额比例
   ,a.wats_gmv_online_city_rate -- 屈臣氏24年线上城市GMV比例
 from ${dme_ads}.tb_sales_city_attack_customer_tmp6 a
 union all
 -- 合并DT Others 的数据
 select
    a.year
    ,a.months
    ,a.city_name        -- 城市
    ,a.first_channel_name
    ,a.Ka_name          -- KA名称
    ,a.distributer_code -- 客户code
    ,a.distributer_name -- 客户名称
    ,a.bu_1
    ,a.bu_2
    ,a.dist_type -- 经销商类型
    ,a.Base_sale_amt_Jan  -- 1月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Feb  -- 2月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Mar  -- 3月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Apr  -- 4月份退货后基价销售额（未税）
    ,a.Base_sale_amt_May  -- 5月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Jun  -- 6月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Jul  -- 7月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Aug  -- 8月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Sep  -- 9月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Oct  -- 10月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Nov  -- 11月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Dec  -- 12月份退货后基价销售额（未税）
    ,a.base_sale_amt_ytd  -- YTD退货后基价销售额（未税）
    ,a.sales_amt_ytd      -- YTD退货后销售额（未税）
    ,a.gmv_city    -- 城市GMV
    ,a.gmv           -- 店铺GMV
    ,a.Ratio_Rate
    ,a.GES
    ,a.PLD_Rate
    ,a.PPD_Rate
    ,a.FG_Rate
    ,a.PLD
    ,a.PPD
    ,a.FG
    ,a.NGS
    ,a.Rebate_Rate
    ,a.CA_Rate
    ,a.Logistics_Rate
    ,a.contract_Rate
    ,a.NGS*a.Rebate_Rate     as Rebate
    ,a.NGS*a.CA_Rate        as CA
    ,a.NGS*a.Logistics_Rate as Logistics
    ,a.NGS*a.contract_Rate  as Indirect_Rebate
    ,a.LKA_contract_fee
    ,a.Other_investment_Rate
    ,a.NGS*a.Other_investment_Rate as Other_investment
    ,a.L10_Rate
    ,a.L11_Rate
    ,a.L14_Rate
    ,a.L16_Rate
    ,a.L17_Rate
    ,a.L17_total_Rate
    ,a.L17_opcb_Rate
    ,a.L17_Rate_city
    ,a.L10
    ,a.L11
    ,a.L14
    ,a.L16
    ,a.L17
    ,a.Orig_NGS_MONTHLY            -- 月的 Net_Gross_Sales，净销售总额
    ,a.Orig_rebate
    ,a.Orig_CA
    ,a.Orig_PLD
    ,a.Orig_PPD
    ,a.Orig_FG
    ,a.Orig_GES
    ,a.Orig_NGS
    ,a.Orig_logistic_fee
    ,a.Orig_listing_fee
    ,a.Orig_nka_expense
    ,a.Orig_2nd_dis_dm_others
    ,a.Orig_l10_commission
    ,a.Orig_l11_t_w
    ,a.Orig_l14_cog
    ,a.Orig_l16_umc
    ,a.Orig_l17_total
    ,a.Orig_l17_nka_tm_o2o
    ,a.Orig_l17_channel
    ,a.Orig_l17_py
    ,a.Orig_l17_ba
    ,a.Orig_l17_mkt
    ,a.Orig_l17_digital
    ,a.Orig_lka_contract_fee       -- Lka合同返利
    ,a.Orig_indirect_rebate        -- 间供返利
    ,null as wats_base_amt_online_city_rate  -- 屈臣氏24年线上城市基价销售额比例
    ,null as wats_gmv_online_city_rate -- 屈臣氏24年线上城市GMV比例
 from(
     select
       a.year
       ,a.months
       ,a.city_name        -- 城市
       ,'DT Others' as first_channel_name
       ,'DT Others' as Ka_name          -- KA名称
       ,'DT Others' as distributer_code -- 客户code
       ,'DT Others' as distributer_name -- 客户名称
       ,a.bu_1
       ,a.bu_2
       ,'DT Others' as dist_type -- 经销商类型
       ,sum(a.Base_sale_amt_Jan*c.index_value/(1-c.index_value)) as Base_sale_amt_Jan  -- 1月份退货后基价销售额（未税）
       ,sum(a.Base_sale_amt_Feb*c.index_value/(1-c.index_value)) as Base_sale_amt_Feb  -- 2月份退货后基价销售额（未税）
       ,sum(a.Base_sale_amt_Mar*c.index_value/(1-c.index_value)) as Base_sale_amt_Mar  -- 3月份退货后基价销售额（未税）
       ,sum(a.Base_sale_amt_Apr*c.index_value/(1-c.index_value)) as Base_sale_amt_Apr  -- 4月份退货后基价销售额（未税）
       ,sum(a.Base_sale_amt_May*c.index_value/(1-c.index_value)) as Base_sale_amt_May  -- 5月份退货后基价销售额（未税）
       ,sum(a.Base_sale_amt_Jun*c.index_value/(1-c.index_value)) as Base_sale_amt_Jun  -- 6月份退货后基价销售额（未税）
       ,sum(a.Base_sale_amt_Jul*c.index_value/(1-c.index_value)) as Base_sale_amt_Jul  -- 7月份退货后基价销售额（未税）
       ,sum(a.Base_sale_amt_Aug*c.index_value/(1-c.index_value)) as Base_sale_amt_Aug  -- 8月份退货后基价销售额（未税）
       ,sum(a.Base_sale_amt_Sep*c.index_value/(1-c.index_value)) as Base_sale_amt_Sep  -- 9月份退货后基价销售额（未税）
       ,sum(a.Base_sale_amt_Oct*c.index_value/(1-c.index_value)) as Base_sale_amt_Oct  -- 10月份退货后基价销售额（未税）
       ,sum(a.Base_sale_amt_Nov*c.index_value/(1-c.index_value)) as Base_sale_amt_Nov  -- 11月份退货后基价销售额（未税）
       ,sum(a.Base_sale_amt_Dec*c.index_value/(1-c.index_value)) as Base_sale_amt_Dec  -- 12月份退货后基价销售额（未税）
       ,sum(a.base_sale_amt_ytd*c.index_value/(1-c.index_value)) as base_sale_amt_ytd  -- YTD退货后基价销售额（未税）
       ,sum(a.sales_amt_ytd    *c.index_value/(1-c.index_value)) as sales_amt_ytd      -- YTD退货后销售额（未税）
       ,null as gmv_city    -- 城市GMV
       ,null as gmv           -- 店铺GMV
       ,null as Ratio_Rate
       ,sum(a.GES*c.index_value/(1-c.index_value))  as GES
       ,avg(d.PLD_Rate)   as PLD_Rate
       ,avg(d.PPD_Rate)   as PPD_Rate
       ,avg(d.FG_Rate )   as FG_Rate
       ,sum(a.GES*c.index_value/(1-c.index_value)) * avg(d.PLD_Rate)   as PLD
       ,sum(a.GES*c.index_value/(1-c.index_value)) * avg(d.PPD_Rate)   as PPD
       ,sum(a.GES*c.index_value/(1-c.index_value)) * avg(d.FG_Rate )   as FG
       ,sum(a.GES*c.index_value/(1-c.index_value)) * (1 -avg(nvl(d.PLD_Rate,0)) -avg(nvl(d.PPD_Rate,0)) -avg(nvl(d.FG_Rate,0))) as NGS
       ,avg(d.Rebate_Rate )      as Rebate_Rate
       ,avg(d.CA_Rate     )      as CA_Rate
       ,avg(d.logistic_fee_Rate) as Logistics_Rate
       ,avg(d.contract_Rate)     as contract_Rate
       ,null as Rebate
       ,null as CA
       ,null as Logistics
       ,null as Indirect_Rebate
       ,0 as LKA_contract_fee
       ,avg(d.Other_investment_Rate) as Other_investment_Rate
       ,null as Other_investment
       ,null as NES
       ,null as TS_Rate
       ,avg(d.l10_commission_Rate ) as L10_Rate
       ,avg(d.l11_t_w_Rate  )       as L11_Rate
       ,avg(d.l14_cog_Rate  )       as L14_Rate
       ,avg(d.l16_umc_Rate  )       as L16_Rate
       ,avg(d.L17_total_Rate)       as L17_Rate
       ,null as L17_total_Rate
       ,null as L17_opcb_Rate
       ,null as L17_Rate_city
       ,sum(a.GES*c.index_value/(1-c.index_value)) * avg(d.l10_commission_Rate ) as L10
       ,sum(a.GES*c.index_value/(1-c.index_value)) * avg(d.l11_t_w_Rate  )       as L11
       ,sum(a.GES*c.index_value/(1-c.index_value)) * avg(d.l14_cog_Rate  )       as L14
       ,null                 as C1
       ,sum(a.GES*c.index_value/(1-c.index_value)) * avg(d.l16_umc_Rate  ) as L16
       ,null                 as GP1
       ,sum(a.GES*c.index_value/(1-c.index_value)) * avg(d.L17_total_Rate) as L17
       ,null                 as GP2
       ,avg(d.Orig_NGS_MONTHLY    ) as Orig_NGS_MONTHLY           -- 月的 Net_Gross_Sales，净销售总额
       ,avg(d.Orig_rebate           ) as Orig_rebate
       ,avg(d.Orig_CA               ) as Orig_CA
       ,avg(d.Orig_PLD              ) as Orig_PLD
       ,avg(d.Orig_PPD              ) as Orig_PPD
       ,avg(d.Orig_FG               ) as Orig_FG
       ,avg(d.Orig_GES              ) as Orig_GES
       ,avg(d.Orig_NGS              ) as Orig_NGS
       ,avg(d.Orig_logistic_fee     ) as Orig_logistic_fee
       ,avg(d.Orig_listing_fee      ) as Orig_listing_fee
       ,avg(d.Orig_nka_expense      ) as Orig_nka_expense
       ,avg(d.Orig_2nd_dis_dm_others) as Orig_2nd_dis_dm_others
       ,avg(d.Orig_l10_commission   ) as Orig_l10_commission
       ,avg(d.Orig_l11_t_w          ) as Orig_l11_t_w
       ,avg(d.Orig_l14_cog          ) as Orig_l14_cog
       ,avg(d.Orig_l16_umc          ) as Orig_l16_umc
       ,avg(d.Orig_l17_total        ) as Orig_l17_total
       ,avg(d.Orig_l17_nka_tm_o2o   ) as Orig_l17_nka_tm_o2o
       ,avg(d.Orig_l17_channel      ) as Orig_l17_channel
       ,avg(d.Orig_l17_py           ) as Orig_l17_py
       ,avg(d.Orig_l17_ba           ) as Orig_l17_ba
       ,avg(d.Orig_l17_mkt          ) as Orig_l17_mkt
       ,avg(d.Orig_l17_digital      ) as Orig_l17_digital
       ,avg(d.Orig_lka_contract_fee ) as Orig_lka_contract_fee      -- Lka合同返利
       ,avg(d.Orig_indirect_rebate  ) as Orig_indirect_rebate       -- 间供返利
     from ${dme_ads}.tb_sales_city_attack_customer_tmp6 a
     left join ${dme_cdm}.dwd_city_attack_weight_base_price_rate c
     on a.bu_2=c.bu
     and a.months>=c.begin_month
     and a.months<c.end_month
     and c.ds=max_pt('${dme_cdm}.dwd_city_attack_weight_base_price_rate')
     and c.index_name='Sales_Weight'  -- DT Others的Sales Weight
     left join ${dme_ads}.tb_sales_city_attack_customer_ws_dt_tmp3 d
     on a.year=d.years
     and a.months=d.months
     and a.bu_2=d.bu_2
     and UPPER(d.channel)='DT'
     where a.bu_2='Beauty Care' and a.dist_type in ('NKA间供+LKA')
     group by a.year,a.months,a.city_name ,a.bu_1,a.bu_2
   ) a

 union all
 -- 合并MPD的数据
 select
    a.year
    ,a.months
    ,a.city_name        -- 城市
    ,a.first_channel_name
    ,a.Ka_name          -- KA名称
    ,a.distributer_code -- 客户code
    ,a.distributer_name -- 客户名称
    ,a.bu_1
    ,a.bu_2
    ,a.dist_type -- 经销商类型
    ,a.Base_sale_amt_Jan  -- 1月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Feb  -- 2月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Mar  -- 3月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Apr  -- 4月份退货后基价销售额（未税）
    ,a.Base_sale_amt_May  -- 5月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Jun  -- 6月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Jul  -- 7月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Aug  -- 8月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Sep  -- 9月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Oct  -- 10月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Nov  -- 11月份退货后基价销售额（未税）
    ,a.Base_sale_amt_Dec  -- 12月份退货后基价销售额（未税）
    ,a.base_sale_amt_ytd  -- YTD退货后基价销售额（未税）
    ,a.sales_amt_ytd      -- YTD退货后销售额（未税）
    ,a.gmv_city    -- 城市GMV
    ,a.gmv           -- 店铺GMV
    ,a.Ratio_Rate
    ,a.GES
    ,a.PLD_Rate
    ,a.PPD_Rate
    ,a.FG_Rate
    ,a.GES * a.PLD_Rate as PLD
    ,a.GES * a.PPD_Rate as PPD
    ,a.GES * a.FG_Rate  as FG
    ,a.NGS
    ,a.Rebate_Rate
    ,a.CA_Rate
    ,a.Logistics_Rate
    ,a.contract_Rate
    ,a.Rebate
    ,a.CA
    ,a.Logistics
    ,a.Indirect_Rebate
    ,a.LKA_contract_fee
    ,a.Other_investment_Rate
    ,a.Other_investment
    ,a.L10_Rate
    ,a.L11_Rate
    ,a.L14_Rate
    ,a.L16_Rate
    ,a.L17_Rate
    ,a.L17_total_Rate
    ,a.L17_opcb_Rate
    ,a.L17_Rate_city
    ,a.GES * a.L10_Rate as L10
    ,a.GES * a.L11_Rate as L11
    ,a.GES * a.L14_Rate as L14
    ,a.GES * a.L16_Rate as L16
    ,a.GES * a.L17_Rate as L17
    ,a.Orig_NGS_MONTHLY           -- 月的 Net_Gross_Sales，净销售总额
    ,a.Orig_rebate
    ,a.Orig_CA
    ,a.Orig_PLD
    ,a.Orig_PPD
    ,a.Orig_FG
    ,a.Orig_GES
    ,a.Orig_NGS
    ,a.Orig_logistic_fee
    ,a.Orig_listing_fee
    ,a.Orig_nka_expense
    ,a.Orig_2nd_dis_dm_others
    ,a.Orig_l10_commission
    ,a.Orig_l11_t_w
    ,a.Orig_l14_cog
    ,a.Orig_l16_umc
    ,a.Orig_l17_total
    ,a.Orig_l17_nka_tm_o2o
    ,a.Orig_l17_channel
    ,a.Orig_l17_py
    ,a.Orig_l17_ba
    ,a.Orig_l17_mkt
    ,a.Orig_l17_digital
    ,a.Orig_lka_contract_fee       -- Lka合同返利
    ,a.Orig_indirect_rebate        -- 间供返利
    ,null as wats_base_amt_online_city_rate  -- 屈臣氏24年线上城市基价销售额比例
    ,null as wats_gmv_online_city_rate -- 屈臣氏24年线上城市GMV比例
 from(
     select
       a.year
       ,a.months
       ,c.city_name as city_name        -- 城市
       ,'MPD' as first_channel_name
       ,'MPD' as Ka_name          -- KA名称
       ,'MPD' as distributer_code -- 客户code
       ,'MPD' as distributer_name -- 客户名称
       ,'Consumer'   as bu_1
       ,'Beauty Care' as bu_2
       ,'MPD' as dist_type -- 经销商类型
       ,sum(e.Base_sale_amt_Jan*c.gmv_city_share) as Base_sale_amt_Jan  -- 1月份退货后基价销售额（未税）
       ,sum(e.Base_sale_amt_Feb*c.gmv_city_share) as Base_sale_amt_Feb  -- 2月份退货后基价销售额（未税）
       ,sum(e.Base_sale_amt_Mar*c.gmv_city_share) as Base_sale_amt_Mar  -- 3月份退货后基价销售额（未税）
       ,sum(e.Base_sale_amt_Apr*c.gmv_city_share) as Base_sale_amt_Apr  -- 4月份退货后基价销售额（未税）
       ,sum(e.Base_sale_amt_May*c.gmv_city_share) as Base_sale_amt_May  -- 5月份退货后基价销售额（未税）
       ,sum(e.Base_sale_amt_Jun*c.gmv_city_share) as Base_sale_amt_Jun  -- 6月份退货后基价销售额（未税）
       ,sum(e.Base_sale_amt_Jul*c.gmv_city_share) as Base_sale_amt_Jul  -- 7月份退货后基价销售额（未税）
       ,sum(e.Base_sale_amt_Aug*c.gmv_city_share) as Base_sale_amt_Aug  -- 8月份退货后基价销售额（未税）
       ,sum(e.Base_sale_amt_Sep*c.gmv_city_share) as Base_sale_amt_Sep  -- 9月份退货后基价销售额（未税）
       ,sum(e.Base_sale_amt_Oct*c.gmv_city_share) as Base_sale_amt_Oct  -- 10月份退货后基价销售额（未税）
       ,sum(e.Base_sale_amt_Nov*c.gmv_city_share) as Base_sale_amt_Nov  -- 11月份退货后基价销售额（未税）
       ,sum(e.Base_sale_amt_Dec*c.gmv_city_share) as Base_sale_amt_Dec  -- 12月份退货后基价销售额（未税）
       ,sum(d.Orig_NGS         *c.gmv_city_share) as base_sale_amt_ytd  -- YTD退货后基价销售额（未税）
       ,null as sales_amt_ytd      -- YTD退货后销售额（未税）
       ,null as gmv_city      -- 城市GMV
       ,null as gmv           -- 店铺GMV
       ,max(c.gmv_city_share) as Ratio_Rate
       ,sum(d.Orig_NGS*c.gmv_city_share)/(1 -avg(nvl(d.PLD_Rate,0)) -avg(nvl(d.PPD_Rate,0)) -avg(nvl(d.FG_Rate,0)))  as GES
       ,sum(d.PLD_Rate)   as PLD_Rate
       ,sum(d.PPD_Rate)   as PPD_Rate
       ,sum(d.FG_Rate )   as FG_Rate
       ,null   as PLD
       ,null   as PPD
       ,null   as FG
       ,sum(d.Orig_NGS*c.gmv_city_share) as NGS
       ,sum(d.Rebate_Rate )      as Rebate_Rate
       ,sum(d.CA_Rate     )      as CA_Rate
       ,sum(d.logistic_fee_Rate) as Logistics_Rate
       ,sum(d.contract_Rate)     as contract_Rate
       ,sum(d.Orig_NGS*c.gmv_city_share*d.Rebate_Rate      ) as Rebate
       ,sum(d.Orig_NGS*c.gmv_city_share*d.CA_Rate          ) as CA
       ,sum(d.Orig_NGS*c.gmv_city_share*d.logistic_fee_Rate) as Logistics
       ,sum(d.Orig_NGS*c.gmv_city_share*d.contract_Rate    ) as Indirect_Rebate
       ,0 as LKA_contract_fee
       ,sum(d.Other_investment_Rate) as Other_investment_Rate
       ,sum(d.Orig_NGS*c.gmv_city_share*d.Other_investment_Rate) as Other_investment
       ,null as NES
       ,null as TS_Rate
       ,sum(d.l10_commission_Rate ) as L10_Rate
       ,sum(d.l11_t_w_Rate  )       as L11_Rate
       ,sum(d.l14_cog_Rate  )       as L14_Rate
       ,sum(d.l16_umc_Rate  )       as L16_Rate
       ,sum(d.L17_total_Rate)       as L17_Rate
       ,null as L17_total_Rate
       ,null as L17_opcb_Rate
       ,null as L17_Rate_city
       ,null as L10
       ,null as L11
       ,null as L14
       ,null as C1
       ,null as L16
       ,null as GP1
       ,null as L17
       ,null as GP2
       ,sum(d.Orig_NGS_MONTHLY      ) as Orig_NGS_MONTHLY       -- 月的 Net_Gross_Sales，净销售总额
       ,sum(d.Orig_rebate           ) as Orig_rebate
       ,sum(d.Orig_CA               ) as Orig_CA
       ,sum(d.Orig_PLD              ) as Orig_PLD
       ,sum(d.Orig_PPD              ) as Orig_PPD
       ,sum(d.Orig_FG               ) as Orig_FG
       ,sum(d.Orig_GES              ) as Orig_GES
       ,sum(d.Orig_NGS              ) as Orig_NGS
       ,sum(d.Orig_logistic_fee     ) as Orig_logistic_fee
       ,sum(d.Orig_listing_fee      ) as Orig_listing_fee
       ,sum(d.Orig_nka_expense      ) as Orig_nka_expense
       ,sum(d.Orig_2nd_dis_dm_others) as Orig_2nd_dis_dm_others
       ,sum(d.Orig_l10_commission   ) as Orig_l10_commission
       ,sum(d.Orig_l11_t_w          ) as Orig_l11_t_w
       ,sum(d.Orig_l14_cog          ) as Orig_l14_cog
       ,sum(d.Orig_l16_umc          ) as Orig_l16_umc
       ,sum(d.Orig_l17_total        ) as Orig_l17_total
       ,sum(d.Orig_l17_nka_tm_o2o   ) as Orig_l17_nka_tm_o2o
       ,sum(d.Orig_l17_channel      ) as Orig_l17_channel
       ,sum(d.Orig_l17_py           ) as Orig_l17_py
       ,sum(d.Orig_l17_ba           ) as Orig_l17_ba
       ,sum(d.Orig_l17_mkt          ) as Orig_l17_mkt
       ,sum(d.Orig_l17_digital      ) as Orig_l17_digital
       ,sum(d.Orig_lka_contract_fee ) as Orig_lka_contract_fee      -- Lka合同返利
       ,sum(d.Orig_indirect_rebate  ) as Orig_indirect_rebate       -- 间供返利
     from (
        select month_id as months,year_id as year,'1' as flag
        from ${dme_cdm}.dim_day
        where month_id >='202001' and month_id <=substr('${bizdate}',1,6)
        group by month_id,year_id
     )  a
     inner join (
         select  *,'1' as flag
        from ${dme_cdm}.dwd_city_attack_gmv_city_share_mpd
        where ds=max_pt('${dme_cdm}.dwd_city_attack_gmv_city_share_mpd')
     ) c
      on a.flag=c.flag
      and a.months>=c.begin_month
      and a.months<c.end_month
    left join ${dme_ads}.tb_sales_city_attack_customer_ws_dt_tmp3 d
      on a.year=d.years
      and a.months=d.months
      and UPPER(d.channel)='MPD'
      and d.bu_2='Beauty Care'
    left join(
      select 
         b.months
         ,b.years
         ,cast(sum(case when substr(a.months,5,2)='01' then a.Orig_NGS_MONTHLY end) as decimal(38,6)) as Base_sale_amt_Jan  -- 1月份退货后基价销售额（未税）
         ,cast(sum(case when substr(a.months,5,2)='02' then a.Orig_NGS_MONTHLY end) as decimal(38,6)) as Base_sale_amt_Feb  -- 2月份退货后基价销售额（未税）
         ,cast(sum(case when substr(a.months,5,2)='03' then a.Orig_NGS_MONTHLY end) as decimal(38,6)) as Base_sale_amt_Mar  -- 3月份退货后基价销售额（未税）
         ,cast(sum(case when substr(a.months,5,2)='04' then a.Orig_NGS_MONTHLY end) as decimal(38,6)) as Base_sale_amt_Apr  -- 4月份退货后基价销售额（未税）
         ,cast(sum(case when substr(a.months,5,2)='05' then a.Orig_NGS_MONTHLY end) as decimal(38,6)) as Base_sale_amt_May  -- 5月份退货后基价销售额（未税）
         ,cast(sum(case when substr(a.months,5,2)='06' then a.Orig_NGS_MONTHLY end) as decimal(38,6)) as Base_sale_amt_Jun  -- 6月份退货后基价销售额（未税）
         ,cast(sum(case when substr(a.months,5,2)='07' then a.Orig_NGS_MONTHLY end) as decimal(38,6)) as Base_sale_amt_Jul  -- 7月份退货后基价销售额（未税）
         ,cast(sum(case when substr(a.months,5,2)='08' then a.Orig_NGS_MONTHLY end) as decimal(38,6)) as Base_sale_amt_Aug  -- 8月份退货后基价销售额（未税）
         ,cast(sum(case when substr(a.months,5,2)='09' then a.Orig_NGS_MONTHLY end) as decimal(38,6)) as Base_sale_amt_Sep  -- 9月份退货后基价销售额（未税）
         ,cast(sum(case when substr(a.months,5,2)='10' then a.Orig_NGS_MONTHLY end) as decimal(38,6)) as Base_sale_amt_Oct  -- 10月份退货后基价销售额（未税）
         ,cast(sum(case when substr(a.months,5,2)='11' then a.Orig_NGS_MONTHLY end) as decimal(38,6)) as Base_sale_amt_Nov  -- 11月份退货后基价销售额（未税）
         ,cast(sum(case when substr(a.months,5,2)='12' then a.Orig_NGS_MONTHLY end) as decimal(38,6)) as Base_sale_amt_Dec  -- 12月份退货后基价销售额（未税）
       from ${dme_ads}.tb_sales_city_attack_customer_ws_dt_tmp3 a
       inner join (
            select month_id as months,year_id as years
            from ${dme_cdm}.dim_day
            where month_id >='202001' and month_id <=substr('${bizdate}',1,6)
            group by month_id,year_id
        ) b
        on a.years=b.years
        and a.months<=b.months
       where upper(a.bu_2)='BEAUTY CARE'  
       and upper(a.channel)='MPD'
       group by b.months,b.years
      ) e
      on a.year=e.years
      and a.months=e.months    
    group by a.year,a.months,c.city_name 
   ) a

;

drop table if EXISTS ${dme_ads}.tb_sales_city_attack_customer_tmp8 ;
create table ${dme_ads}.tb_sales_city_attack_customer_tmp8 as
 select
   a.year
   ,a.months
   ,a.city_name        -- 城市
   ,a.first_channel_name
   ,a.Ka_name          -- KA名称
   ,a.distributer_code -- 客户code
   ,a.distributer_name -- 客户名称
   ,a.bu_1
   ,a.bu_2
   ,a.dist_type -- 经销商类型
   ,a.Base_sale_amt_Jan  -- 1月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Feb  -- 2月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Mar  -- 3月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Apr  -- 4月份退货后基价销售额（未税）
   ,a.Base_sale_amt_May  -- 5月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Jun  -- 6月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Jul  -- 7月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Aug  -- 8月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Sep  -- 9月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Oct  -- 10月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Nov  -- 11月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Dec  -- 12月份退货后基价销售额（未税）
   ,a.base_sale_amt_ytd  -- YTD退货后基价销售额（未税）
   ,a.sales_amt_ytd      -- YTD退货后销售额（未税）
   ,a.gmv_city    -- 城市GMV
   ,a.gmv           -- 店铺GMV
   ,a.Ratio_Rate
   ,a.GES
   ,a.PLD_Rate
   ,a.PPD_Rate
   ,a.FG_Rate
   ,a.PLD
   ,a.PPD
   ,a.FG
   ,a.NGS
   ,a.Rebate_Rate
   ,a.CA_Rate
   ,a.Logistics_Rate
   ,a.contract_Rate
   ,a.Rebate
   ,a.CA
   ,a.Logistics
   ,a.Indirect_Rebate
   ,a.LKA_contract_fee
   ,a.Other_investment_Rate
   ,a.Other_investment
   ,nvl(a.NGS,0)-nvl(a.Rebate,0)-nvl(a.CA,0)-nvl(a.Logistics,0)-nvl(a.Indirect_Rebate,0)-nvl(a.LKA_contract_fee,0)
      -nvl(a.Other_investment,0) as NES
   ,(nvl(a.GES,0) -
        (nvl(a.NGS,0)-nvl(a.Rebate,0)-nvl(a.CA,0)-nvl(a.Logistics,0)-nvl(a.Indirect_Rebate,0)
         -nvl(a.LKA_contract_fee,0)-nvl(a.Other_investment,0)
       ))/ if(a.GES=0,null,a.GES)   as TS_Rate
   ,a.L10_Rate
   ,a.L11_Rate
   ,a.L14_Rate
   ,a.L16_Rate
   ,a.L17_Rate
   ,a.L17_total_Rate
   ,a.L17_opcb_Rate
   ,a.L17_Rate_city
   ,a.L10
   ,a.L11
   ,a.L14
   ,nvl(a.NGS,0)-nvl(a.Rebate,0)-nvl(a.CA,0)-nvl(a.Logistics,0)-nvl(a.Indirect_Rebate,0)-nvl(a.LKA_contract_fee,0)
      -nvl(a.Other_investment,0) -nvl(a.L10,0)-nvl(a.L11,0)-nvl(a.L14,0) as C1
   ,a.L16
   ,nvl(a.NGS,0)-nvl(a.Rebate,0)-nvl(a.CA,0)-nvl(a.Logistics,0)-nvl(a.Indirect_Rebate,0)-nvl(a.LKA_contract_fee,0)
      -nvl(a.Other_investment,0) -nvl(a.L10,0)-nvl(a.L11,0)-nvl(a.L14,0)-nvl(a.L16,0) as GP1
   ,a.L17
   ,nvl(a.NGS,0)-nvl(a.Rebate,0)-nvl(a.CA,0)-nvl(a.Logistics,0)-nvl(a.Indirect_Rebate,0)-nvl(a.LKA_contract_fee,0)
      -nvl(a.Other_investment,0) -nvl(a.L10,0)-nvl(a.L11,0)-nvl(a.L14,0)-nvl(a.L16,0)-nvl(a.L17,0)  as GP2
   ,a.Orig_NGS_MONTHLY       -- 月的 Net_Gross_Sales，净销售总额
   ,a.Orig_rebate
   ,a.Orig_CA
   ,a.Orig_PLD
   ,a.Orig_PPD
   ,a.Orig_FG
   ,a.Orig_GES
   ,a.Orig_NGS
   ,a.Orig_logistic_fee
   ,a.Orig_listing_fee
   ,a.Orig_nka_expense
   ,a.Orig_2nd_dis_dm_others
   ,a.Orig_l10_commission
   ,a.Orig_l11_t_w
   ,a.Orig_l14_cog
   ,a.Orig_l16_umc
   ,a.Orig_l17_total
   ,a.Orig_l17_nka_tm_o2o
   ,a.Orig_l17_channel
   ,a.Orig_l17_py
   ,a.Orig_l17_ba
   ,a.Orig_l17_mkt
   ,a.Orig_l17_digital
   ,a.wats_base_amt_online_city_rate  -- 屈臣氏24年线上城市基价销售额比例
   ,a.wats_gmv_online_city_rate -- 屈臣氏24年线上城市GMV比例
 from ${dme_ads}.tb_sales_city_attack_customer_tmp7 a

 ;
insert overwrite table ${dme_ads}.tb_sales_city_attack_customer partition(ds)
 select
   a.year
   ,a.months
   ,a.city_name        -- 城市
   ,a.first_channel_name
   ,case when a.bu_2='SKP' AND a.dist_type='专业线下' THEN t2.store_name
         when a.Ka_name regexp '大润发' THEN '大润发'
         when a.Ka_name regexp '永辉' THEN '永辉'
      ELSE a.Ka_name
     END Ka_name         -- KA名称
   ,case when a.year='2023' and a.distributer_code='2925773' then '2925773/1967491'
      else a.distributer_code
     end as distributer_code -- 客户code
   ,case when a.year='2023' and a.distributer_code='2925773' then '北京沃亿商业管理有限公司/北京广大华行贸易有限公司'
      else a.distributer_name
     end as distributer_name -- 客户名称
   ,a.bu_1
   ,a.bu_2
   ,a.dist_type          -- 经销商类型
   ,a.Base_sale_amt_Jan  -- 1月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Feb  -- 2月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Mar  -- 3月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Apr  -- 4月份退货后基价销售额（未税）
   ,a.Base_sale_amt_May  -- 5月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Jun  -- 6月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Jul  -- 7月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Aug  -- 8月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Sep  -- 9月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Oct  -- 10月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Nov  -- 11月份退货后基价销售额（未税）
   ,a.Base_sale_amt_Dec  -- 12月份退货后基价销售额（未税）
   ,a.base_sale_amt_ytd  -- YTD退货后基价销售额（未税）
   ,a.sales_amt_ytd      -- YTD退货后销售额（未税）
   ,cast(a.gmv_city as DECIMAL(38,6)) as gmv_city          -- 城市GMV
   ,cast(a.gmv               as DECIMAL(38,6)) as gmv                 -- 店铺GMV
   ,cast(a.Ratio_Rate        as DECIMAL(38,6)) as Ratio_Rate          -- City Ratio%（城市占比%）
   ,cast(a.GES               as DECIMAL(38,6)) as GES                 -- GES
   ,cast(a.PLD_Rate          as DECIMAL(38,6)) as PLD_Rate            -- PLD%
   ,cast(a.PPD_Rate          as DECIMAL(38,6)) as PPD_Rate            -- PPD%
   ,cast(a.FG_Rate           as DECIMAL(38,6)) as FG_Rate             -- FG%
   ,cast(a.PLD               as DECIMAL(38,6)) as PLD                 -- PLD
   ,cast(a.PPD               as DECIMAL(38,6)) as PPD                 -- PPD
   ,cast(a.FG                as DECIMAL(38,6)) as FG                  -- FG
   ,cast(a.NGS               as DECIMAL(38,6)) as NGS                 -- NGS
   ,cast(a.Rebate_Rate       as DECIMAL(38,6)) as Rebate_Rate         -- Rebate%
   ,cast(a.CA_Rate           as DECIMAL(38,6)) as CA_Rate             -- CA%
   ,cast(a.Logistics_Rate    as DECIMAL(38,6)) as Logistics_Rate      -- Logistics%
   ,cast(a.contract_Rate     as DECIMAL(38,6)) as contract_Rate       -- 间供合同比例%
   ,cast(a.Rebate            as DECIMAL(38,6)) as Rebate              -- Rebate
   ,cast(a.CA                as DECIMAL(38,6)) as CA                  -- CA
   ,cast(a.Logistics         as DECIMAL(38,6)) as Logistics           -- Logistics
   ,cast(a.Indirect_Rebate   as DECIMAL(38,6)) as Indirect_Rebate     -- Indirect Rebate
   ,cast(a.LKA_contract_fee  as DECIMAL(38,6)) as LKA_contract_fee    -- LKA contract fee
   ,cast(a.Other_investment_Rate as DECIMAL(38,6)) Other_investment_Rate -- Other investment%
   ,cast(a.Other_investment      as DECIMAL(38,6)) Other_investment     -- Other investment
   ,cast(a.NES                   as DECIMAL(38,6)) NES                  -- NES
   ,cast(a.TS_Rate               as DECIMAL(38,6)) TS_Rate              -- TS%
   ,cast(a.L10_Rate              as DECIMAL(38,6)) L10_Rate             -- L10%
   ,cast(a.L11_Rate              as DECIMAL(38,6)) L11_Rate             -- L11%
   ,cast(a.L14_Rate              as DECIMAL(38,6)) L14_Rate             -- L14%
   ,cast(a.L16_Rate              as DECIMAL(38,6)) L16_Rate             -- L16%
   ,cast(a.L17_Rate              as DECIMAL(38,6)) L17_Rate             -- L17%
   ,cast(a.L10                   as DECIMAL(38,6)) L10                  -- L10
   ,cast(a.L11                   as DECIMAL(38,6)) L11                  -- L11
   ,cast(a.L14                   as DECIMAL(38,6)) L14                  -- L14
   ,cast(a.C1                    as DECIMAL(38,6)) C1                   -- C1
   ,cast(a.L16                   as DECIMAL(38,6)) L16                  -- L16
   ,cast(a.GP1                   as DECIMAL(38,6)) GP1                  -- GP1
   ,cast(a.L17                   as DECIMAL(38,6)) L17                  -- L17
   ,cast(a.GP2                   as DECIMAL(38,6)) GP2                  -- GP2
   ,nvl(b.province_name,'Others')  as province_name -- 省份
   ,cast(a.wats_base_amt_online_city_rate as DOUBLE) as wats_base_amt_online_city_rate  -- 屈臣氏24年线上城市基价销售额比例
   ,cast(a.wats_gmv_online_city_rate as DOUBLE) as wats_gmv_online_city_rate -- 屈臣氏24年线上城市GMV比例
   ,'${bizdate}'as ds
 from ${dme_ads}.tb_sales_city_attack_customer_tmp8 a
 left join (
    select *,row_number()over(partition by district_name order by ds desc, create_time desc ) as rn
    from ${dme_ods}.s_city_province_mapping 
    where ds=max_pt('${dme_ods}.s_city_province_mapping')
  ) b
  on a.city_name=b.district_name
  and b.rn=1
 left join ${dme_cdm}.dwd_city_attack_dist_list t2   -- 专业线经销商清单
  on a.distributer_code=t2.dist_code
  and replace(a.city_name,'市','')=replace(t2.city_name,'市','')
  and a.months>=t2.begin_month
  and a.months<t2.end_month
  and t2.ds=max_pt('${dme_cdm}.dwd_city_attack_dist_list')
  and a.bu_2='SKP'
 where (nvl(a.base_sale_amt_ytd,0)<>0 or nvl(a.sales_amt_ytd,0)<>0 or Ka_name='DT Others' or a.dist_type ='专业线下' or Ka_name='MPD')
 and if(a.bu_2='SKP' and a.dist_type ='专业线下',t2.dist_code is not null ,1=1)
 --and nvl(UPPER(a.city_name),'OTHERS')<>'OTHERS'
 --and if(a.Ka_name in ('施华蔻专业京东官旗','施华蔻京东官旗','丝蕴京东官旗'),nvl(UPPER(a.city_name),'OTHERS')<>'OTHERS',1=1) -- 这三个店铺城市gmv数据来自业务上传，来自DME划不到城市的数据踢掉
 and if(a.dist_type='电商(手工_城市)',nvl(UPPER(a.city_name),'OTHERS')<>'OTHERS',1=1) -- 这三个店铺城市gmv数据来自业务上传，来自DME划不到城市的数据踢掉
 and if(a.year>='2025' and a.bu_1='Consumer',nvl(a.dist_type,'') not in ('NKA间供+LKA','DT Others'),1=1) -- DT客户转MPD需求调整，2025年之后剔除零售线NKA间供+LKA和DT Others分类数据
 and a.year>='2022'
 ; 