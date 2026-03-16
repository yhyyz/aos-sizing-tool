# V2 重构说明

## 目录结构

```
v2/
├── config/
│   ├── constants.py           # 通用常量（存储计算、分片策略、节点限制、Master 配置）
│   └── instance_families.py   # 机型家族注册表 — 添加新机型的唯一扩展点
├── models/
│   ├── request.py             # 请求模型（SizingRequest / EC2SizingRequest）
│   └── instance.py            # 实例规格 + Sizing/Pricing 结果模型
├── engine/
│   ├── base_sizing.py         # 基础 Sizing 引擎（AOS/EC2 共享）
│   ├── aos_sizing.py          # AOS 特化（热转暖缓冲、warm 无 replica）
│   ├── ec2_sizing.py          # EC2 特化（warm+cold 合并、warm 有 replica）
│   ├── base_pricing.py        # 基础 Pricing 引擎
│   ├── aos_pricing.py         # AOS Pricing（GP3 + Managed Storage）
│   └── ec2_pricing.py         # EC2 Pricing（SSD + HDD）
├── solution/
│   ├── aos_solution.py        # AOS 编排：遍历所有 hot×warm 组合
│   └── ec2_solution.py        # EC2 编排：指定机型计算
├── routes/
│   └── routes.py              # V2 API 路由
└── tests/
    └── test_v2.py             # 单元测试（46 个）
```

## API 端点

### V2 新端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v2/sizing/aos` | AOS 托管 OpenSearch sizing + pricing |
| POST | `/v2/sizing/ec2` | EC2 自建 ES sizing + pricing |
| GET  | `/v2/regions` | 可用 region 列表 |
| GET  | `/v2/instance-families` | 已注册机型家族信息 |

### V1 旧端点（保持不变）

| 方法 | 路径 |
|------|------|
| POST | `/provisioned/log_analytics_sizing` |
| POST | `/provisioned/es_ec2_sizing` |
| GET  | `/provisioned/region_list` |

### 请求参数

V2 新增参数：
- `compressionRatio`: 压缩比（默认 0.4），可由前端传入
- `warmArchitecture`: warm 架构选择（默认 `"ultrawarm"`）

```json
{
  "dailyDataSize": 200000,
  "hotDays": 14,
  "warmDays": 30,
  "coldDays": 60,
  "replicaNum": 1,
  "writePeak": 2370,
  "AZ": 2,
  "region": "US East (N. Virginia)",
  "RI": "0yr",
  "paymentOptions": "OD",
  "master": 3,
  "compressionRatio": 0.4,
  "warmArchitecture": "ultrawarm",
  "filterData": "",
  "pageSize": 1000,
  "page": 1
}
```

## Warm 架构

两种 warm 架构互斥，通过 `warmArchitecture` 参数选择：

### `"ultrawarm"` — UltraWarm 架构（默认）

| 层级 | 实例类型 | 存储 | 定价 |
|------|---------|------|------|
| Hot | 任意实例 | EBS GP3 | 实例+GP3 |
| Warm | ultrawarm1.medium/large | S3 Managed Storage | 实例+Managed Storage/GB |
| Cold | S3 Cold Storage | S3 | Managed Storage/GB |

### `"multi_tier"` — 多层存储架构（OpenSearch 3.3+）

| 层级 | 实例类型 | 存储 | 定价 |
|------|---------|------|------|
| Hot | 仅 optimized (or1/or2/om2/oi2) | OI2=本地NVMe, 其他=EBS GP3 | 实例+(非OI2加GP3) |
| Warm | 仅 OI2 | 本地 NVMe 缓存 | 仅实例费用 |
| Cold | **不支持** | — | — |

引擎行为差异：
- `multi_tier` 自动将 cold storage 设为 0（即使 `coldDays > 0`）
- OI2 hot 节点不计算 EBS 存储费用
- OI2 warm 节点不计算 Managed Storage 费用（存储成本含在实例价格中）
- OI2 warm 存储容量使用 `OI2_WARM_STORAGE_QUOTA`（NVMe 缓存 × 5 可寻址）
- 非 optimized hot 实例（如 r7g）在 `multi_tier` 模式下会被过滤掉

## 添加新机型

只需两步：

### 1. 注册机型家族 (`v2/config/instance_families.py`)

```python
AOS_NEW_FAMILY = InstanceFamily(
    name="xxx",
    service_type=ServiceType.AOS,
    storage_backend=StorageBackend.EBS_GP3,
    is_optimized=True,
    memory_per_vcpu=8,
    available_sizes=_ALL_SIZES,
    write_throughput=_scale_throughput(_R6G_BASE, 1.5),
)

# 加入注册表
AOS_FAMILIES 字典中添加该实例
```

### 2. 在 Excel 中添加机型规格和定价数据

- `AOS_SIZING.xlsx` → `AOS_HOT_INSTANCE` sheet 添加实例规格行
- `AOS_SIZING_PRICING.xlsx` → `ALL` sheet 添加定价行
- 若为 OI2 warm 节点：`AOS_SIZING.xlsx` → `AOS_WARM_INSTANCE` sheet 添加

**不需要修改任何计算引擎代码。**

## 已修复的 Bug

| Bug | 位置 | 修复 |
|-----|------|------|
| EC2 Master OD 定价查错实例 | 原 `CalcESLogAnalyticsPricing:51` | v2 `ec2_pricing.py` 已修正 |
| cold storage 定价赋值错误 | 原 `CalcAOSLogAnalyticsPricing:68` | v2 `aos_pricing.py` 已修正 |
| EC2 or1 吞吐量基准不一致 | 原 `const.py:183-190` | v2 统一使用 `instance_families.py` 注册表 |
| for 循环取最后一行值 | 原 `base_pricing` 多处 | v2 改用 `iloc[0]` + DataFrame 过滤 |
| UltraWarm 定价未限定 PurchaseOption | 原 `CalcAOSLogAnalyticsPricing:52` | v2 增加 OD fallback 过滤 |
| Hot-Warm 架构不兼容未校验 | 原无校验 | v2 `is_valid_warm_combination()` |
| OI2 错算 EBS/Managed Storage 费用 | 原无处理 | v2 按 `needs_ebs_config` 和架构跳过 |
| multi_tier 错算 cold 存储 | 原无处理 | v2 `calc_cold_required_storage()` 检查架构 |

## 运行测试

```bash
python3 -m pytest v2/tests/test_v2.py -v
```

## 待完成

- [ ] or2/om2/oi2 的 Excel 实例规格和定价数据
- [ ] or2/om2/oi2 实际性能测试后更新 `write_throughput`（当前为估算值，标记了 TODO）
