--MaxCompute_SQL
--********************************************************************--
--所属主题: TMKT O2O---如交易域、运营数据报表
--功能描述: O2O平台粒度GMV明细数据
--创建者: yuxuan.zhang_datacvg.com(yuxuan.zhang_datacvg.com@henkelhcdfacc)
--创建日期: 2023-10-18 16:41:47
--修改日期	修改人	修改内容
--yyyymmdd	name	comment
--20240229 shiwu 若'O2O+标准零售商名+mapping'中无法获取京东到家的‘汉高零售商平台',则从 K1K2匹配表中获取K1的零售商平台名称 
--20240312 zyx 修改retailer_name零售商(平台)字段逻辑
--20240313 yyq 修改retailer_name零售商(平台)字段逻辑,追后关联条件有问题
--20240403 yyq o2o多点表改用数据填报表，由月分区增量改成全量
--20250418 yyq o2o多点表GMV取销售金额字段（之前是数量*件均价）
--20240524 wpf 增加 NKA和SELECTIVE RETAILER 限制
--20240701 wpf 产品基价使用快照基价
--20241105 xueyang 数值类型精度调整为decimal(28,6)
--20250403 yyq     剔除kapos系统屈臣氏数据,汉高零售商和渠道匹配不到,美团,淘鲜达,饿了么,京东到家置为mpd,其他平台置为未匹配（mapping表里面为others的，也置为未匹配）
--20251104 mass 将产品主数据表切换到bu表
--20260115 yyq  通过ka名称匹配ka主数据 获取ka group
--20260720 mass 新增BU字段
--********************************************************************--

--合并手工、多点o2o销售数据
drop table if exists ${dme_cdm}.dwd_o2o_platform_sale_info_temp01;
create table ${dme_cdm}.dwd_o2o_platform_sale_info_temp01 as
    select   
    t1.platform_name                   as platform_name  --平台名称
    , t1.sales_date                      as sales_date     --销售日期
    , replace(t1.retailer_name,'#N/A','')                   as retailer_name  --零售商(平台)
    , tt.upc_barcode                     as barcode        --UPC条码(平台)
    , t1.product_name                    as product_name   --产品名(平台)
    , t1.retailer_rsp                    as retailer_rsp   --零售商RSP
    , t1.page_price                      as page_price     --页面价
    , t1.sales_qty                       as sales_qty      --销量
    , t1.gmv                             as GMV            --GMV
    , case when t1.province_name like '宁夏%' then '宁夏回族自治区'  
        when t1.province_name like '内蒙古%' then '内蒙古自治区'     
        when t1.province_name like '新疆%' then '新疆维吾尔自治区'
        when t1.province_name like '广西%' then '广西壮族自治区' 
        when t1.province_name like '西藏%' then '西藏自治区'
        when t1.province_name in ('北京','上海','天津','重庆') then concat(t1.province_name,'市')
        when t1.province_name not like '%省' and t1.province_name not like '%市' then concat(t1.province_name,'省')
    else t1.province_name  end        as province_name  --省份
    , t1.city_name                       as city_name      --城市 
    , t2.product_name                   as henkel_product_name      --汉高产品名
    , t2.product_name_en                as henkel_product_name_en   --汉高产品英文名     
    , t2.category_name                  as henkel_category_name     --汉高品类
    , t2.category_name_en               as henkel_category_name_en  --汉高品类英文名称
    , t2.brand_name                     as henkel_brand_name        --汉高品牌
    , t2.brand_name_en                  as henkel_brand_name_en     --汉高品牌英文名
    , t2.sub_product_function           as henkel_sub_product_function --汉高子品类
    , t2.product_line                   as henkel_product_line         --汉高产品线
    , t2.product_pack_ori               as henkel_product_pack_ori     --汉高产品规格
    , t2.retail_price_tax               as henkel_rsp                  --汉高RSP      
    , '手工'                             as data_source                 --数据来源
    , cast(t1.sales_qty*t2.retail_price_tax as decimal(28,6)) as GMV2   --GMV(RSP*QTY)
    , t3.k1_retailer_name                as k1_retailer_name            --K1-零售商名称
    , t3.k2_store_name                   as k2_store_name               --K2-门店名称 
    ,COALESCE(t1.bu,t2.bu_2,'Beauty Care') as bu_2
from  (select 
             t1.platform_name                        as platform_name  --平台名称
           , substr(concat(
			split_part(replace(replace(t1.sales_date,'.','-'),'/','-'),'-',1),
		     case when length(split_part(replace(replace(t1.sales_date,'.','-'),'/','-'),'-',2))=1
			then concat('0',split_part(replace(replace(t1.sales_date,'.','-'),'/','-'),'-',2))
			else split_part(replace(replace(t1.sales_date,'.','-'),'/','-'),'-',2) end,
            case when length(split_part(replace(replace(t1.sales_date,'.','-'),'/','-'),'-',3))=1
			then concat('0',split_part(replace(replace(t1.sales_date,'.','-'),'/','-'),'-',3))
			else split_part(replace(replace(t1.sales_date,'.','-'),'/','-'),'-',3) end
  		),1,8)                                 as sales_date     --销售日期
           , t1.retailer_name                        as retailer_name  --零售商(平台)
           , case when trim(t1.upc_code) in ('#N/A')  then '-110'
                  else coalesce(t1.upc_code,'-110')  end as upc_code       --UPC条码(平台)
           , t1.product_name                         as product_name   --产品名(平台)
           , cast(t1.retailer_rsp as decimal(28,6))  as retailer_rsp   --零售商RSP
           , cast(t1.page_price as decimal(28,6))    as page_price     --页面价
           , sum(cast(t1.sales_qty as bigint))       as sales_qty      --销量
           , sum(cast(t1.gmv as decimal(28,6)))      as GMV            --GMV
           , t1.province_name                        as province_name  --省份
           , t1.city_name                            as city_name      --城市 
           , t1.k1_code                              as k1_code        --k1
           , t1.k2_code                              as k2_code        --k2
           ,t1.bu
        from ${dme_ods}.s_o2o_platform_sale_info t1        
         where t1.ds=max_pt('${dme_ods}.s_o2o_platform_sale_info') 
       group by t1.platform_name, t1.retailer_name, t1.k1_code , t1.k2_code
               ,t1.bu
               , case when trim(t1.upc_code) in ('#N/A') then '-110'
                  else coalesce(t1.upc_code,'-110')  end  
               , t1.product_name , t1.retailer_rsp, t1.city_name, t1.page_price , t1.province_name
               , substr(concat(
			split_part(replace(replace(sales_date,'.','-'),'/','-'),'-',1),
			case when length(split_part(replace(replace(sales_date,'.','-'),'/','-'),'-',2))=1
			then concat('0',split_part(replace(replace(sales_date,'.','-'),'/','-'),'-',2))
			else split_part(replace(replace(sales_date,'.','-'),'/','-'),'-',2) end,
            case when length(split_part(replace(replace(sales_date,'.','-'),'/','-'),'-',3))=1
			then concat('0',split_part(replace(replace(sales_date,'.','-'),'/','-'),'-',3))
			else split_part(replace(replace(sales_date,'.','-'),'/','-'),'-',3) end
  		),1,8)
        ) t1 lateral view explode(split(t1.upc_code,',')) tt as upc_barcode
left join ${dme_cdm}.dwd_master_data_product_pos_bu t2
       on t1.upc_code = t2.product_barcode
      and t1.sales_date = t2.ds
left join ${dme_ods}.s_tmkt_o2o_k1k2_mapping t3
       on t1.k1_code = t3.k1_code
      and t1.k2_code = t3.k2_code
      and t3.ds=max_pt('${dme_ods}.s_tmkt_o2o_k1k2_mapping')
    where (length(tt.upc_barcode)=13 or tt.upc_barcode = '-110')

--多点
union all
select
      '多点'                    as platform_name
     , bcconvert(replace(t1.sales_date,'-',''))            as sales_date  --销售日期
     , bcconvert(t1.merchant_name)         as retailer_name  --零售商(平台)  
     , replace(bcconvert(t1.barcode),'#N/A','')               as barcode        --UPC条码(平台)  
     , bcconvert(t1.item_name)             as product_name   --产品名(平台)  
     , null                                as retailer_rsp   --零售商RSP  
     , null                                as page_price     --页面价  
     , cast(t1.sales_qty  as bigint)       as sales_qty      --销量  
     , cast(t1.sales_amt as decimal(28,6)) as GMV  --GMV
     , bcconvert(t1.province_name)         as province_name  --省份  
     , bcconvert(t1.city_name)             as city_name      --城市 
     , t2.product_name          as henkel_product_name      --汉高产品名
     , t2.product_name_en       as henkel_product_name_en   --汉高产品英名     
     , t2.category_name         as henkel_category_name     --汉高品类
     , t2.category_name_en      as henkel_category_name_en  --汉高品类英文名称
     , t2.brand_name            as henkel_brand_name        --汉高品牌
     , t2.brand_name_en         as henkel_brand_name_en     --汉高品牌英文名
     , t2.sub_product_function  as henkel_sub_product_function --汉高子品类
     , t2.product_line          as henkel_product_line         --汉高产品线
     , t2.product_pack_ori      as henkel_product_pack_ori     --汉高产品规格
     , t2.retail_price_tax      as henkel_rsp                  --汉高RSP      
     , 'DME-DMALL'              as data_source                 --数据来源
     , cast(t1.sales_qty*t2.retail_price_tax  as decimal(28,6)) as GMV2  --GMV(RSP*QTY)
     , null                     as k1_retailer_name            --K1-零售商名称
     , null                     as k2_store_name               --K2-门店名称 
     ,COALESCE(t1.bu,t2.bu_2,'Beauty Care') as bu_2
     from dme_ods.s_o2o_dmall_sale_info_all t1
left join ${dme_cdm}.dwd_master_data_product_pos_bu t2
       on t1.barcode = t2.product_barcode
      and bcconvert(replace(t1.sales_date,'-','')) = t2.ds
    where t1.ds = max_pt('dme_ods.s_o2o_dmall_sale_info_all') 

;


--插入正式表数据
insert overwrite table ${dme_cdm}.dwd_o2o_platform_sale_info partition (ds)
select    
      case when t1.platform_name='饿了么' then '淘宝闪购'
         else t1.platform_name end as platform_name       --平台名称        
     , t1.sales_date               --销售日期
   --20240229 修改错字段，若'O2O+标准零售商名+mapping'中无法获取京东到家的‘汉高零售商平台',则从 K1K2匹配表中获取K1的零售商平台名称 
     ,coalesce(case when t1.retailer_name  is null then t1.k1_retailer_name
             else t1.retailer_name end,'') as retailer_name --零售商(平台)
     , t1.barcode                  --UPC条码(平台)
     , t1.product_name             --产品名(平台)
     , t1.retailer_rsp             --零售商RSP
     , t1.page_price               --页面价
     , t1.sales_qty                --销量
     , cast(t1.GMV as decimal(28,6)) --GMV
     , t1.province_name            --省份
     , t1.city_name                --城市 
     , t1.henkel_product_name      --汉高产品名
     , t1.henkel_product_name_en   --汉高产品英文名     
     , t1.henkel_category_name     --汉高品类
     , t1.henkel_category_name_en  --汉高品类英文名称
     , t1.henkel_brand_name        --汉高品牌
     , t1.henkel_brand_name_en     --汉高品牌英文名
     , t1.henkel_sub_product_function --汉高子品类
     , t1.henkel_product_line         --汉高产品线
     , t1.henkel_product_pack_ori     --汉高产品规格
     , t1.henkel_rsp                  --汉高RSP     
     --20240229 shiwu 若'O2O+标准零售商名+mapping'中无法获取京东到家的‘汉高零售商平台',则从 K1K2匹配表中获取K1的零售商平台名称 
     --, t2.henkel_retailer_name is null then t1.k1_retailer_name
     --        else t2.henkel_retailer_name end
     --       ,'未匹配')  as henkel_retailer_name     --汉高零售商
     ,case when t1.platform_name in ('美团','淘鲜达','饿了么','京东到家','淘宝闪购') and coalesce(t2.henkel_retailer_name,'未匹配')='未匹配' then 'MPD'
        else coalesce(t2.henkel_retailer_name,'未匹配')  end as henkel_retailer_name   --汉高零售商
     ,case when t1.platform_name in ('美团','淘鲜达','饿了么','京东到家','淘宝闪购') and coalesce(t3.ka_group_name,t2.channel_name,'未匹配')='未匹配' then 'MPD'
        else coalesce(t3.ka_group_name,t2.channel_name,'未匹配')  end as henkel_channel_name              --汉高渠道
     , t1.data_source                 --数据来源
     , cast(t1.GMV2 as decimal(28,6)) --GMV(RSP*QTY)
     , t1.k1_retailer_name            --K1-零售商名称
     , t1.k2_store_name               --K2-门店名称
     ,t4.bu_1
     ,t1.bu_2
     , '${bizdate}'  as ds
from ${dme_cdm}.dwd_o2o_platform_sale_info_temp01 t1
left join (select  trim(retailer_name) as retailer_name
                 , case when lower(trim(henkel_retailer_name)) in ('others') then '未匹配'
                        else trim(henkel_retailer_name) end as henkel_retailer_name
                 , case when lower(trim(channel_name)) in ('others') then '未匹配'
                        when lower(trim(channel_name)) in ('lka') then 'LKA'
                        when lower(trim(channel_name)) in ('hyper') then 'Hyper'
                        when lower(trim(channel_name)) in ('mini') then 'Mini'
                        else trim(channel_name) end as channel_name
                  ,ROW_NUMBER() OVER(PARTITION BY trim(retailer_name) ORDER BY qbi_system_upload_id desc) AS rn
             from ${dme_ods}.s_tmkt_o2o_retailer_mapping
            where ds=max_pt('${dme_ods}.s_tmkt_o2o_retailer_mapping')  
          ) t2
       on lower(trim(coalesce(case when t1.retailer_name  is null then t1.k1_retailer_name
             else t1.retailer_name end,''))) =lower(trim(t2.retailer_name))
       and t2.rn=1 
left join (
    select ka_name,ka_group_name
    from ${dme_cdm}.dwd_master_data_ka
    where ds=max_pt('${dme_cdm}.dwd_master_data_ka') 
    and ka_type_code ='10000006'   -- 限制ka类型为nka,其他类型ka名称有重复的
    group by ka_name,ka_group_name
) t3 
on t2.henkel_retailer_name=t3.ka_name
left join (
  select bu_1,bu_2
  from ${dme_cdm}.dwd_master_data_product_pos_bu
  where ds=max_pt('${dme_cdm}.dwd_master_data_product_pos_bu')
  group by bu_1,bu_2
) t4
 on upper(t1.bu_2) = upper(t4.bu_2)
 ;
