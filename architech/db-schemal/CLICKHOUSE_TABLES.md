# ClickHouse 表结构说明文档

## 概述

本文档描述了云枢业务数据同步到 ClickHouse 的表结构设计，包括远程外部表和本地表的定义。

---

## 数据库说明

- **ClickHouse数据库**: `yovole_dm_clickhouse_prod` - 存储云枢业务数据
- **HDFS数据源**: `hdfs://yovole-nameservice/user/hive/warehouse/yovole_dm_dmp_prod.db/`
- **数据格式**: Parquet

---

## 一、云枢业务表

### 1.1 CK_FACT_YUNSHU_DEVICEPOINT_HBASE

**表名**: `ck_fact_yunshu_devicepoint_hbase`

**用途**: 云枢设备点位事实表

**引擎**: ReplacingMergeTree

**主键**: `rowkey`

**排序键**: `rowkey`

**字段说明**:

| 字段名                 | 类型             | 说明             | 是否可空 |
| ---------------------- | ---------------- | ---------------- | -------- |
| rowkey                 | String           | 主键：设备点位ID | 否       |
| id                     | Nullable(String) | ID               | 是       |
| modedatamodifier       | Nullable(String) | 修改人           | 是       |
| dwmc                   | Nullable(String) | 点位名称         | 是       |
| modedatacreatetime     | Nullable(String) | 创建时间         | 是       |
| modedatacreatertype    | Nullable(String) | 创建人类型       | 是       |
| szwz                   | Nullable(String) | 所在位置         | 是       |
| jf                     | Nullable(String) | 机房(ID)         | 是       |
| modedatacreater        | Nullable(String) | 创建人           | 是       |
| modedatamodifydatetime | Nullable(String) | 修改时间         | 是       |
| sztd                   | Nullable(String) | 所在通道         | 是       |
| requestid              | Nullable(String) | 请求ID           | 是       |
| jc                     | Nullable(String) | 简称             | 是       |
| dyztid                 | Nullable(String) | 对应状态ID       | 是       |
| xgsb                   | Nullable(String) | 相关设备         | 是       |
| modeuuid               | Nullable(String) | -                | 是       |
| form_biz_id            | Nullable(String) | 表单业务ID       | 是       |
| sbjc                   | Nullable(String) | 设备简称         | 是       |
| jjbm                   | Nullable(String) | 机架编码(ID)     | 是       |
| dwid                   | Nullable(String) | 点位ID(OID)      | 是       |
| formmodeid             | Nullable(String) | 表单模式ID       | 是       |
| szlc                   | Nullable(String) | 所在楼层         | 是       |
| dwlx                   | Nullable(String) | 点位类型         | 是       |
| modedatacreatedate     | Nullable(String) | 创建日期         | 是       |
| szmk                   | Nullable(String) | 所在模块         | 是       |
| metric_time            | Nullable(String) | 指标时间         | 是       |
| metric_value           | Nullable(String) | 指标值           | 是       |

**远程外部表**: `remote_ck_fact_yunshu_devicepoint_hbase`

- **引擎**: HDFS
- **路径**: `hdfs://yovole-nameservice/user/hive/warehouse/yovole_dm_dmp_prod.db/tmp_fact_yunshu_devicepoint_hbase/*`
- **格式**: Parquet

**示例数据**:

```sql
SELECT * FROM ck_fact_yunshu_devicepoint_hbase LIMIT 1 \G
```

```
Row 1:
──────
rowkey:                 1
id:                     9
modedatamodifier:       PDUA-2F-1
dwmc:                   进线A相电压
modedatacreatetime:     1000133
modedatacreatertype:    9110bf20-4a63-49f3-a16d-10e80c357cfd
szwz:                   1765861615
jf:                     
modedatacreater:        1748
modedatamodifydatetime: 
sztd:                   
requestid:              82
jc:                     1
dyztid:                 16:25:42
xgsb:                   230.5
modeuuid:               PDUA-2F-1.PDU_Output_Ua
form_biz_id:            
sbjc:                   
jjbm:                   
dwid:                   1
formmodeid:             0
szlc:                   4
dwlx:                   
modedatacreatedate:     34331e65-70e1-c8b6-16de-842c3aa50ffc
szmk:                   2024-11-21
metric_time:            
metric_value:           U-A
```

---

### 1.2 CK_FACT_YUNSHU_RESJJ_HBASE

**表名**: `ck_fact_yunshu_resjj_hbase`

**用途**: 云枢机架事实表

**引擎**: ReplacingMergeTree

**主键**: `rowkey`

**排序键**: `rowkey`

**字段说明**:

| 字段名                 | 类型             | 说明             | 是否可空 |
| ---------------------- | ---------------- | ---------------- | -------- |
| rowkey                 | String           | 主键：机架ID     | 否       |
| id                     | Nullable(String) | ID               | 是       |
| jjbmyh                 | Nullable(String) | 机架编码(原有)   | 是       |
| kh                     | Nullable(String) | 客户             | 是       |
| akg                    | Nullable(String) | A路开关          | 是       |
| form_biz_id            | Nullable(String) | 表单业务ID       | 是       |
| ywzx                   | Nullable(String) | 业务中心         | 是       |
| modedatacreatedate     | Nullable(String) | 创建日期         | 是       |
| nbjjsfsd               | Nullable(String) | 内部机架是否锁定 | 是       |
| sfwc                   | Nullable(String) | 是否完成         | 是       |
| ac19                   | Nullable(String) | A路C19           | 是       |
| wdslaxx                | Nullable(String) | 温度数量下限     | 是       |
| dhzt                   | Nullable(String) | 动环状态         | 是       |
| modedatacreatertype    | Nullable(String) | 创建人类型       | 是       |
| bkgzt                  | Nullable(String) | 板块更状态       | 是       |
| formmodeid             | Nullable(String) | 表单模式ID       | 是       |
| ac13                   | Nullable(String) | A路C13           | 是       |
| jfmc                   | Nullable(String) | 机房名称(ID)     | 是       |
| sdslaxx                | Nullable(String) | 湿度数量下限     | 是       |
| col                    | Nullable(String) | 列               | 是       |
| mk                     | Nullable(String) | 模块             | 是       |
| ztsm                   | Nullable(String) | 状态说明         | 是       |
| jjzt                   | Nullable(String) | 机架状态         | 是       |
| akgzt                  | Nullable(String) | A路开关状态      | 是       |
| modeuuid               | Nullable(String) | -                | 是       |
| jjbm                   | Nullable(String) | 机架编码         | 是       |
| modedatamodifydatetime | Nullable(String) | 修改时间         | 是       |
| sdzt                   | Nullable(String) | 锁定状态         | 是       |
| jjbmyys                | Nullable(String) | 机架编码(运营商) | 是       |
| wdslasx                | Nullable(String) | 温度数量上限     | 是       |
| bkg                    | Nullable(String) | B路开关          | 是       |
| modedatacreater        | Nullable(String) | 创建人           | 是       |
| bc13                   | Nullable(String) | B路C13           | 是       |
| requestid              | Nullable(String) | 请求ID           | 是       |
| modedatamodifier       | Nullable(String) | 修改人           | 是       |
| htbm                   | Nullable(String) | 合同编码         | 是       |
| bzdl                   | Nullable(String) | 标准电力         | 是       |
| sddl                   | Nullable(String) | 锁定电力         | 是       |
| pdulx                  | Nullable(String) | PDU类型          | 是       |
| outkey                 | Nullable(String) | 外部键           | 是       |
| zzkh                   | Nullable(String) | 最终客户         | 是       |
| apdu                   | Nullable(String) | A路PDU           | 是       |
| sfzy                   | Nullable(String) | 是否占用         | 是       |
| jjlx                   | Nullable(String) | 机架类型         | 是       |
| khmc                   | Nullable(String) | 客户名称         | 是       |
| bpdu                   | Nullable(String) | B路PDU           | 是       |
| dhztrq                 | Nullable(String) | 动环状态日期     | 是       |
| xnjj                   | Nullable(String) | 虚拟机架         | 是       |
| sdrq                   | Nullable(String) | 锁定日期         | 是       |
| bc19                   | Nullable(String) | B路C19           | 是       |
| sdslasx                | Nullable(String) | 湿度数量上限     | 是       |
| srlx                   | Nullable(String) | 散热类型         | 是       |
| lc                     | Nullable(String) | 楼层             | 是       |
| modedatacreatetime     | Nullable(String) | 创建时间         | 是       |
| zzkhbm                 | Nullable(String) | 最终客户编码     | 是       |
| jfbm                   | Nullable(String) | 机房编码         | 是       |

**远程外部表**: `remote_ck_fact_yunshu_resjj_hbase`

- **引擎**: HDFS
- **路径**: `hdfs://yovole-nameservice/user/hive/warehouse/yovole_dm_dmp_prod.db/tmp_fact_yunshu_resjj_hbase/*`
- **格式**: Parquet

**示例数据**:

```sql
SELECT * FROM ck_fact_yunshu_resjj_hbase LIMIT 1 \G
```

```
Row 1:
──────
rowkey:                 1
id:                     1
jjbmyh:                 F5-B09-08-1
kh:                     424
akg:                    
form_biz_id:            
ywzx:                   38
modedatacreatedate:     
nbjjsfsd:               
sfwc:                   0
ac19:                   
wdslaxx:                
dhzt:                   
modedatacreatertype:    
bkgzt:                  
formmodeid:             2
ac13:                   
jfmc:                   9
sdslaxx:                
col:                    B09
mk:                     F5B
ztsm:                   
jjzt:                   2
akgzt:                  
modeuuid:               
jjbm:                   F5-B09-08-1
modedatamodifydatetime: 
sdzt:                   0
jjbmyys:                
wdslasx:                
bkg:                    
modedatacreater:        
bc13:                   
requestid:              
modedatamodifier:       
htbm:                   XSHT-202402-1689
bzdl:                   10A(2.2KW)
sddl:                   
pdulx:                  
outkey:                 2713
zzkh:                   107
apdu:                   
sfzy:                   0
jjlx:                   
khmc:                   107
bpdu:                   
dhztrq:                 
xnjj:                   1
sdrq:                   
bc19:                   
sdslasx:                
srlx:                   
lc:                     F5
modedatacreatetime:     
zzkhbm:                 424
jfbm:                   SH6
```

---

### 1.3 CK_FACT_YUNSHU_RESROOM_HBASE

**表名**: `ck_fact_yunshu_resroom_hbase`

**用途**: 云枢机房事实表

**引擎**: ReplacingMergeTree

**主键**: `rowkey`

**排序键**: `rowkey`

**字段说明**:

| 字段名                 | 类型             | 说明             | 是否可空 |
| ---------------------- | ---------------- | ---------------- | -------- |
| rowkey                 | String           | 主键：机房ID     | 否       |
| id                     | Nullable(String) | ID               | 是       |
| ywzx                   | Nullable(String) | 业务中心         | 是       |
| jgzs                   | Nullable(String) | 机柜总数         | 是       |
| modedatamodifydatetime | Nullable(String) | 修改时间         | 是       |
| sjjfs                  | Nullable(String) | 设计机房数       | 是       |
| sykss                  | Nullable(String) | 使用颗数         | 是       |
| gxqy                   | Nullable(String) | 管辖区域         | 是       |
| jfmc                   | Nullable(String) | 机房名称         | 是       |
| belongmidperiod        | Nullable(String) | -                | 是       |
| yeszjid                | Nullable(String) | YesZjID          | 是       |
| jfbm                   | Nullable(String) | 机房编码         | 是       |
| modeuuid               | Nullable(String) | -                | 是       |
| jfjc                   | Nullable(String) | 机房简称         | 是       |
| bkys                   | Nullable(String) | 板块映射         | 是       |
| yqys                   | Nullable(String) | 园区映射         | 是       |
| yjfs                   | Nullable(String) | 已建机房数       | 是       |
| dz                     | Nullable(String) | 地址             | 是       |
| form_biz_id            | Nullable(String) | 表单业务ID       | 是       |
| outkey                 | Nullable(String) | 外部键           | 是       |
| belongship             | Nullable(String) | -                | 是       |
| nbjys                  | Nullable(String) | 内部简易数       | 是       |
| co                     | Nullable(String) | -                | 是       |
| modedatacreatetime     | Nullable(String) | 创建时间         | 是       |
| bz                     | Nullable(String) | 备注             | 是       |
| requestid              | Nullable(String) | 请求ID           | 是       |
| modedatamodifier       | Nullable(String) | 修改人           | 是       |
| kss                    | Nullable(String) | 颗数             | 是       |
| cc                     | Nullable(String) | -                | 是       |
| kqzt                   | Nullable(String) | 考勤状态         | 是       |
| gsbs                   | Nullable(String) | 公司标识         | 是       |
| modedatacreatedate     | Nullable(String) | 创建日期         | 是       |
| px                     | Nullable(String) | 排序             | 是       |
| khmc                   | Nullable(String) | 客户名称         | 是       |
| modedatacreater        | Nullable(String) | 创建人           | 是       |
| jfzdl                  | Nullable(String) | 机房总电力       | 是       |
| dhjkkqzt               | Nullable(String) | 动环监控考勤状态 | 是       |
| formmodeid             | Nullable(String) | 表单模式ID       | 是       |
| modedatacreatertype    | Nullable(String) | 创建人类型       | 是       |

**远程外部表**: `remote_ck_fact_yunshu_resroom_hbase`

- **引擎**: HDFS
- **路径**: `hdfs://yovole-nameservice/user/hive/warehouse/yovole_dm_dmp_prod.db/tmp_fact_yunshu_resroom_hbase/*`
- **格式**: Parquet

**示例数据**:

```sql
SELECT * FROM ck_fact_yunshu_resroom_hbase LIMIT 1 \G
```

```
Row 1:
──────
rowkey:                 10
id:                     10
ywzx:                   38
jgzs:                   1550
modedatamodifydatetime: 2025-09-05 17:42:24
sjjfs:                  1550
sykss:                  903
gxqy:                   16
jfmc:                   上海宁桥云计算数据中心(B7)
belongmidperiod:        1
yeszjid:                21542
jfbm:                   SH2
modeuuid:               
jfjc:                   上海宁桥(B7)
bkys:                   278
yqys:                   552
yjfs:                   449
dz:                     
form_biz_id:            10000016
outkey:                 8
belongship:             1288
nbjys:                  36
co:                     1020
modedatacreatetime:     
bz:                     后期根据签约客户电量调整
requestid:              
modedatamodifier:       1
kss:                    1236
cc:                     1020
kqzt:                   0
gsbs:                   0
modedatacreatedate:     
px:                     1
khmc:                   44,571,152,80,113,6,160,134,229,479,404,5,569,54,450,496,30,28,86,79,547,548,3,381,534,616,584,629,55,61,142,88,38,108
modedatacreater:        
jfzdl:                  9145.0
dhjkkqzt:               
formmodeid:             1
modedatacreatertype:    
```

---

## 二、动环实时表

### 2.1 CK_FACT_DONGHUAN_REAL_METRIC_HBASE

**表名**: `ck_fact_donghuan_real_metric_hbase`

**用途**: 动环实时指标事实表

**引擎**: ReplacingMergeTree

**主键**: `rowkey`

**排序键**: `(rowkey, toYYYYMMDD(toDateTime(toInt64(metric_time))))`

**字段说明**:

| 字段名          | 类型             | 说明             | 是否可空 |
| --------------- | ---------------- | ---------------- | -------- |
| rowkey          | String           | 主键             | 否       |
| c_datacenter_id | Nullable(String) | 数据中心ID       | 是       |
| c_source_ip     | Nullable(String) | 源IP             | 是       |
| c_source_mode   | Nullable(String) | 源模式           | 是       |
| resource_id     | Nullable(String) | 资源ID           | 是       |
| metric_name     | Nullable(String) | 指标名称         | 是       |
| metric_value    | Nullable(String) | 指标值           | 是       |
| metric_unit     | Nullable(String) | 指标单位         | 是       |
| metric_time     | String           | 指标时间(时间戳) | 否       |
| status          | Nullable(String) | 状态             | 是       |

**分区策略**: 按日期分区 (基于 `metric_time` 时间戳字段)

**DDL语句**:

```sql
CREATE TABLE IF NOT EXISTS yovole_dm_clickhouse_prod.ck_fact_donghuan_real_metric_hbase
(
    rowkey                  String COMMENT '主键',
    c_datacenter_id         Nullable(String) COMMENT '数据中心ID',
    c_source_ip             Nullable(String) COMMENT '源IP',
    c_source_mode           Nullable(String) COMMENT '源模式',
    resource_id             Nullable(String) COMMENT '资源ID',
    metric_name             Nullable(String) COMMENT '指标名称',
    metric_value            Nullable(String) COMMENT '指标值',
    metric_unit             Nullable(String) COMMENT '指标单位',
    metric_time             String COMMENT '指标时间(时间戳)',
    status                  Nullable(String) COMMENT '状态'
)
ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMMDD(toDateTime(toInt64(metric_time)))
ORDER BY (rowkey, toYYYYMMDD(toDateTime(toInt64(metric_time))))
PRIMARY KEY rowkey
SETTINGS index_granularity = 8192;
```

**分区说明**:

- 使用 `toYYYYMMDD(toDateTime(toInt64(metric_time)))` 将时间戳转换为日期分区键
- `metric_time` 为非空字段，存储字符串类型的时间戳（如 "1765852325"）
- 处理流程：
  1. `toInt64(metric_time)` - 将字符串转换为整数
  2. `toDateTime()` - 转换为日期时间
  3. `toYYYYMMDD()` - 提取日期作为分区键
- 分区键格式：YYYYMMDD（如 20251216 表示 2025年12月16日）
- 排序键：`(rowkey, toYYYYMMDD(toDateTime(toInt64(metric_time))))`，主键 rowkey 必须是排序键的前缀
- 支持按日删除历史数据，便于数据管理
- **重要**：`metric_time` 必须为非空类型，确保分区键有效

**示例数据**:

```sql
SELECT * FROM ck_fact_donghuan_real_metric_hbase LIMIT 1 \G
```

```
Row 1:
──────
rowkey:          02100000511-dianliangyi-nrg01.Meter_Output_QL_SH_JQ_02
c_datacenter_id: SH_JQ_02
c_source_ip:     YILI
c_source_mode:   PULL
resource_id:     02100000511-dianliangyi-nrg01.Meter_Output_QL
metric_name:     三相电感性功率
metric_value:    0
metric_unit:     KVar
metric_time:     1765275749
status:          
```

---

### 2.2 CK_FACT_DONGHUAN_EVENT_DETAIL_HBASE

**表名**: `ck_fact_donghuan_event_detail_hbase`

**用途**: 动环告警事件详情表

**引擎**: ReplacingMergeTree

**主键**: `rowkey`

**排序键**: `(event_month, rowkey)`

**字段说明**:

| 字段名              | 类型             | 说明                 | 是否可空 |
| ------------------- | ---------------- | -------------------- | -------- |
| rowkey              | String           | 主键：salt(event_id) | 否       |
| c_datacenter_id     | Nullable(String) | 数据中心ID           | 是       |
| c_source_ip         | Nullable(String) | 源IP                 | 是       |
| c_source_mode       | Nullable(String) | 源模式               | 是       |
| event_id            | Nullable(String) | 事件ID               | 是       |
| resource_id         | Nullable(String) | 资源ID               | 是       |
| resource_name       | Nullable(String) | 资源名称             | 是       |
| event_type          | Nullable(String) | 事件类型             | 是       |
| event_level         | Nullable(String) | 事件等级             | 是       |
| event_message       | Nullable(String) | 事件内容             | 是       |
| event_time          | String           | 发生时间(时间戳)     | 否       |
| event_status        | Nullable(String) | 事件状态             | 是       |
| event_location      | Nullable(String) | 位置                 | 是       |
| event_location_name | Nullable(String) | 位置名称             | 是       |
| event_device_type   | Nullable(String) | 设备类型             | 是       |
| event_snapshot      | Nullable(String) | 快照                 | 是       |
| confirm_time        | Nullable(String) | 确认时间             | 是       |
| confirm_by          | Nullable(String) | 确认人               | 是       |
| confirm_description | Nullable(String) | 确认描述             | 是       |
| recover_time        | Nullable(String) | 恢复时间(时间戳)     | 是       |
| recover_by          | Nullable(String) | 恢复人               | 是       |
| recover_snapshot    | Nullable(String) | 恢复快照             | 是       |
| remove_time         | Nullable(String) | 清除时间             | 是       |
| remove_by           | Nullable(String) | 清除人               | 是       |
| remove_description  | Nullable(String) | 清除描述             | 是       |
| accept_time         | Nullable(String) | 受理时间             | 是       |
| accept_by           | Nullable(String) | 受理人               | 是       |

**分区策略**: 按月分区 (基于 `event_time` 时间戳字段)

**DDL语句**:

```sql
CREATE TABLE IF NOT EXISTS yovole_dm_clickhouse_prod.ck_fact_donghuan_event_detail_hbase
(
    rowkey                  String COMMENT 'RowKey: salt(event_id)',
    c_datacenter_id         Nullable(String) COMMENT '数据中心ID',
    c_source_ip             Nullable(String) COMMENT '源IP',
    c_source_mode           Nullable(String) COMMENT '源模式',
    event_id                Nullable(String) COMMENT '事件ID',
    resource_id             Nullable(String) COMMENT '资源ID',
    resource_name           Nullable(String) COMMENT '资源名称',
    event_type              Nullable(String) COMMENT '事件类型',
    event_level             Nullable(String) COMMENT '事件等级',
    event_message           Nullable(String) COMMENT '事件内容',
    event_time              String COMMENT '发生时间(时间戳)',
    event_status            Nullable(String) COMMENT '事件状态',
    event_location          Nullable(String) COMMENT '位置',
    event_location_name     Nullable(String) COMMENT '位置名称',
    event_device_type       Nullable(String) COMMENT '设备类型',
    event_snapshot          Nullable(String) COMMENT '快照',
    confirm_time            Nullable(String) COMMENT '确认时间',
    confirm_by              Nullable(String) COMMENT '确认人',
    confirm_description     Nullable(String) COMMENT '确认描述',
    recover_time            Nullable(String) COMMENT '恢复时间(时间戳)',
    recover_by              Nullable(String) COMMENT '恢复人',
    recover_snapshot        Nullable(String) COMMENT '恢复快照',
    remove_time             Nullable(String) COMMENT '清除时间',
    remove_by               Nullable(String) COMMENT '清除人',
    remove_description      Nullable(String) COMMENT '清除描述',
    accept_time             Nullable(String) COMMENT '受理时间',
    accept_by               Nullable(String) COMMENT '受理人'
)
ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMM(toDateTime(toInt64(event_time)))
ORDER BY (rowkey, toYYYYMM(toDateTime(toInt64(event_time))))
PRIMARY KEY rowkey
SETTINGS index_granularity = 8192;
```

**分区说明**:

- 使用 `toYYYYMM(toDateTime(toInt64(event_time)))` 将时间戳转换为月份分区键
- `event_time` 为非空字段，存储字符串类型的时间戳（如 "1765771220"）
- 处理流程：
  1. `toInt64(event_time)` - 将字符串转换为整数
  2. `toDateTime()` - 转换为日期时间
  3. `toYYYYMM()` - 提取年月作为分区键
- 分区键格式：YYYYMM（如 202512 表示 2025年12月）
- 排序键：`(rowkey, toYYYYMM(toDateTime(toInt64(event_time))))`，主键 rowkey 必须是排序键的前缀
- 支持按月删除历史数据，便于数据管理
- **重要**：`event_time` 必须为非空类型，确保分区键有效

**示例数据**:

```sql
SELECT * FROM ck_fact_donghuan_event_detail_hbase LIMIT 1 \G
```

```
Row 1:
──────
rowkey:              00002400-1652-48e0-a908-29ff4e030eb0_SH_LG_02
c_datacenter_id:     SH_LG_02
c_source_ip:         
c_source_mode:       PULL
event_id:            00002400-1652-48e0-a908-29ff4e030eb0
resource_id:         32_0_35_2_3_0
resource_name:       M13-124-13#M215IT机房南侧东门
event_type:          7
event_level:         3
event_message:       M13-124-13#M215IT机房南侧东门-门锁关闭
event_time:          1765480784
event_status:        0
event_location:      project_root/0_4099/0_124/0_2050/32_0_35
event_location_name: 有孚临港大数据平台二期动环监控系统/上海有孚临港/13号楼/系统集成/13#2F弱电间-D3号控制箱
event_device_type:   4.1.1.0.0.0.0
event_snapshot:      
confirm_time:        
confirm_by:          
confirm_description: 
recover_time:        
recover_by:          
recover_snapshot:    
remove_time:         
remove_by:           
remove_description:  
accept_time:         
accept_by:           
```

---

## 三、表关系说明

### 3.1 数据流向

```
HBase (FACT层) → Impala临时表 (Parquet) → ClickHouse远程外表 → ClickHouse本地表
```

### 3.2 同步流程

1. **准备数据** (`dmp_sync2ck_preparedata.sql`)

   - 从 HBase FACT 表读取数据
   - 创建 Impala 临时表（Parquet 格式）
   - 数据存储在 HDFS
2. **同步数据** (`dmp_sync2ck_syncdata.sql`)

   - 创建 ClickHouse 远程外部表（HDFS引擎）
   - 创建 ClickHouse 本地表（ReplacingMergeTree引擎）
   - 从远程外表导入数据到本地表
3. **清理数据** (`dmp_sync2ck_clean.sql`)

   - 删除 Impala 临时表
   - 释放 HDFS 存储空间

### 3.3 业务关系

**云枢业务表关系**:

- **机房表** (`ck_fact_yunshu_resroom_hbase`) ← **机架表** (`ck_fact_yunshu_resjj_hbase`)

  - 通过 `jfmc` (机房名称ID) 关联
- **机架表** (`ck_fact_yunshu_resjj_hbase`) ← **设备点位表** (`ck_fact_yunshu_devicepoint_hbase`)

  - 通过 `jjbm` (机架编码ID) 关联

**动环业务表关系**:

- **事件表** (`ck_fact_donghuan_event_detail_hbase`)
  - 包含完整的事件生命周期信息（发生、确认、恢复、清除、受理）
  - 通过 `resource_id` 关联资源信息
  - 支持事件状态追踪和处理流程分析
  - 按月分区存储，便于历史数据管理

---

## 四、使用说明

### 4.1 数据同步

使用同步脚本执行完整的数据同步流程：

```bash
./dmp_sync2ck.sh <impala_host> <impala_port> <ods_db> <dw_dmp_db> \
  <pdatatype> <intervalValue> <dateValue> <startDate> <endDate> \
  <ck_host> <ck_port> <ck_dbname>
```

**参数说明**:

- `impala_host`: Impala 服务器地址
- `impala_port`: Impala 端口
- `ods_db`: ODS 数据库名称
- `dw_dmp_db`: DW DMP 数据库名称
- `pdatatype`: 数据类型
- `intervalValue`: 间隔值
- `dateValue`: 日期值
- `startDate`: 开始日期
- `endDate`: 结束日期
- `ck_host`: ClickHouse 服务器地址
- `ck_port`: ClickHouse 端口
- `ck_dbname`: ClickHouse 数据库名称

### 4.2 查看分区信息

查询表的分区状态、数据量和存储占用：

```sql
-- 查看动环事件表分区
SELECT
    partition,
    count() AS parts,
    sum(rows) AS total_rows,
    formatReadableSize(sum(bytes_on_disk)) AS size_on_disk,
    min(min_date) AS min_date,
    max(max_date) AS max_date
FROM
    system.parts
WHERE
    database = 'yovole_dm_clickhouse_prod'
    AND table = 'ck_fact_donghuan_event_detail_hbase'
    AND active
GROUP BY
    partition
ORDER BY
    partition DESC;

-- 查看动环实时指标表分区
SELECT
    partition,
    count() AS parts,
    sum(rows) AS total_rows,
    formatReadableSize(sum(bytes_on_disk)) AS size_on_disk,
    min(min_date) AS min_date,
    max(max_date) AS max_date
FROM
    system.parts
WHERE
    database = 'yovole_dm_clickhouse_prod'
    AND table = 'ck_fact_donghuan_real_metric_hbase'
    AND active
GROUP BY
    partition
ORDER BY
    partition DESC;
```

**返回字段说明**:

- `partition`: 分区值（按月：YYYYMM 或 按日：YYYYMMDD）
- `parts`: 分区内的数据块数量
- `total_rows`: 分区内总行数
- `size_on_disk`: 分区占用磁盘大小
- `min_date`/`max_date`: 分区数据的时间范围

### 4.3 分区维护

#### 4.3.1 自动清理过期分区（TTL）

为表设置 TTL 可以自动删除过期数据，推荐方式：

```sql
-- 为动环实时指标表设置 TTL（保留 90 天）
ALTER TABLE yovole_dm_clickhouse_prod.ck_fact_donghuan_real_metric_hbase 
MODIFY TTL toDateTime(toInt64(metric_time)) + INTERVAL 90 DAY;

-- 为动环事件表设置 TTL（保留 180 天）
ALTER TABLE yovole_dm_clickhouse_prod.ck_fact_donghuan_event_detail_hbase 
MODIFY TTL toDateTime(toInt64(event_time)) + INTERVAL 180 DAY;
```

**TTL 说明**:

- 实时指标表（按日分区）：建议保留 30-90 天
- 事件表（按月分区）：建议保留 6-12 个月（180-365 天）
- ClickHouse 会在后台自动合并和清理过期分区
- TTL 基于数据的时间字段，而非写入时间

#### 4.3.2 手动删除指定分区

当需要手动清理特定分区时：

```sql
-- 删除实时指标表的某日分区（如 2025年12月1日）
ALTER TABLE yovole_dm_clickhouse_prod.ck_fact_donghuan_real_metric_hbase 
DROP PARTITION '20251201';

-- 删除事件表的某月分区（如 2025年11月）
ALTER TABLE yovole_dm_clickhouse_prod.ck_fact_donghuan_event_detail_hbase 
DROP PARTITION '202511';

-- 批量删除多个分区
ALTER TABLE yovole_dm_clickhouse_prod.ck_fact_donghuan_real_metric_hbase 
DROP PARTITION '20251201',
DROP PARTITION '20251202',
DROP PARTITION '20251203';
```

#### 4.3.3 查看 TTL 设置

查询表的 TTL 配置：

```sql
SELECT 
    database,
    table,
    engine,
    create_table_query
FROM system.tables
WHERE database = 'yovole_dm_clickhouse_prod'
  AND table IN ('ck_fact_donghuan_real_metric_hbase', 'ck_fact_donghuan_event_detail_hbase');
```

#### 4.3.4 删除 TTL 设置

如果需要取消自动清理：

```sql
ALTER TABLE yovole_dm_clickhouse_prod.ck_fact_donghuan_real_metric_hbase 
REMOVE TTL;

ALTER TABLE yovole_dm_clickhouse_prod.ck_fact_donghuan_event_detail_hbase 
REMOVE TTL;
```

### 4.4 表优化

定期执行表优化以合并数据分片：

```sql
-- 云枢表优化
optimize table ck_fact_yunshu_devicepoint_hbase final;
optimize table ck_fact_yunshu_resjj_hbase final;
optimize table ck_fact_yunshu_resroom_hbase final;

-- 动环表优化
optimize table ck_fact_donghuan_event_detail_hbase final;
optimize table ck_fact_donghuan_real_metric_hbase final;
```

### 4.5 注意事项

1. **引擎特性**: ReplacingMergeTree 引擎会自动去重，保留最新版本的数据
2. **幂等性**: 所有建表语句支持重复执行（使用 `IF NOT EXISTS`）
3. **远程外表**: HDFS 引擎的远程表用于数据导入，不存储数据
4. **数据清理**: 同步完成后及时清理 Impala 临时表，避免占用存储空间

---

## 五、性能优化建议

### 5.1 表引擎优化

- **ReplacingMergeTree**: 自动去重，适合有更新的业务数据
- **主键设计**: 使用业务主键（rowkey）作为 PRIMARY KEY
- **排序键**: 与主键一致，优化查询性能

### 5.2 查询优化

1. **主键查询**: 利用主键进行快速点查询
2. **字段过滤**: ClickHouse 列式存储，只查询需要的字段
3. **批量插入**: 使用 INSERT INTO SELECT 进行批量数据导入

### 5.3 存储优化

- **Parquet 中间格式**: 列式存储，压缩比高
- **定期优化**: 使用 OPTIMIZE TABLE 合并数据分片
- **分区策略**: 动环事件表已采用按月分区策略，支持高效的历史数据管理和查询优化
- **分区管理**: 可通过 `ALTER TABLE DROP PARTITION` 删除过期分区，释放存储空间

---

## 六、版本历史

| 日期       | 版本 | 变更内容                             |
| ---------- | ---- | ------------------------------------ |
| 2025-12-15 | 1.0  | 初始版本，包含云枢三个核心业务表     |
| 2025-12-16 | 1.1  | 新增动环事件明细表                   |
| 2025-12-16 | 1.2  | 新增动环实时指标表，增加分区查询和维护说明 |

---

**文档生成时间**: 2025-12-15

**相关文件**:

- `dmp_sync2ck_preparedata.sql`
- `dmp_sync2ck_syncdata.sql`
- `dmp_sync2ck_clean.sql`
- `dmp_sync2ck.sh`
