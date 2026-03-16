# AOS Sizing API

Amazon OpenSearch Service (AOS) 与 EC2 自建 Elasticsearch 的容量规划与成本估算工具。

## 目录

- [快速开始](#快速开始)
- [数据源](#数据源)
- [项目结构](#项目结构)
- [API 接口文档](#api-接口文档)
- [机型吞吐量参考](#机型吞吐量参考)
  - [AOS 机型](#aos-机型)
  - [EC2 机型](#ec2-机型)
  - [吞吐量计算说明](#吞吐量计算说明)
- [Warm 架构](#warm-架构)
- [Sizing 计算逻辑](#sizing-计算逻辑)
  - [输入参数](#输入参数)
  - [Hot 层 — 节点数计算](#hot-层--节点数计算)
  - [Hot 层 — 存储计算](#hot-层--存储计算)
  - [Warm 层 — 节点数与存储计算](#warm-层--节点数与存储计算)
  - [Cold 层 — 存储计算](#cold-层--存储计算)
  - [Master 节点选型](#master-节点选型)
  - [Pricing 费用计算](#pricing-费用计算)
  - [数值计算示例](#数值计算示例)
- [生产部署](#生产部署)
- [测试](#测试)

---

## 快速开始

### 环境要求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (推荐的包管理器)

### 本地开发

```bash
# 1. 创建虚拟环境
uv venv -p 3.12

# 2. 激活虚拟环境
source .venv/bin/activate

# 3. 安装依赖
uv pip install -r requirements.txt

# 4. 启动服务（默认使用 Excel 数据源）
python app.py

# 或使用 AWS Pricing API 数据源
DATA_SOURCE=api python app.py
```

服务启动后访问: http://localhost:9989/

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATA_SOURCE` | `excel` | 数据源: `excel` (本地 Excel) 或 `api` (AWS Bulk Pricing API) |

---

## 数据源

支持两种数据源，API 响应格式完全一致：

| | Excel | API |
|---|---|---|
| 数据来源 | `excel/` 目录下的 xlsx 文件 | AWS Bulk Pricing API 实时拉取 |
| 机型覆盖 | 手动维护的子集 | 全量（包含最新机型） |
| Region 覆盖 | 手动维护 | 全量（不含中国区） |
| 离线可用 | 是 | 否（首次启动需联网，之后使用 `.api_cache/`） |
| 适用场景 | 开发测试、离线演示 | 生产环境 |

---

## 项目结构

```
aos-sizing-api/
├── app.py                     # FastAPI 入口，数据加载 + 静态文件服务
├── requirements.txt           # Python 依赖
├── excel/                     # Excel 数据源文件
│   ├── AOS_SIZING.xlsx        # AOS 实例规格（Hot/Warm）
│   ├── AOS_SIZING_PRICING.xlsx# AOS 定价
│   ├── EC2_SIZING.xlsx        # EC2 实例规格
│   └── EC2_SIZING_PRICING.xlsx# EC2 定价
├── util/
│   ├── ebs_limits.py          # EBS 存储上限 + AOS→EC2 族映射
│   ├── load_execl_data.py     # Excel 数据加载器
│   └── load_from_api.py       # AWS Pricing API 数据加载器
├── v2/                        # 计算引擎
│   ├── config/
│   │   ├── constants.py       # 通用常量（存储、分片、节点限制）
│   │   └── instance_families.py # 机型注册表（添加新机型的唯一入口）
│   ├── models/
│   │   ├── request.py         # 请求模型
│   │   └── instance.py        # 实例规格 + Sizing/Pricing 结果
│   ├── engine/
│   │   ├── base_sizing.py     # 基础 Sizing 引擎（AOS/EC2 共享）
│   │   ├── aos_sizing.py      # AOS 特化
│   │   ├── ec2_sizing.py      # EC2 特化
│   │   ├── base_pricing.py    # 基础 Pricing 引擎
│   │   ├── aos_pricing.py     # AOS Pricing（GP3 + Managed Storage）
│   │   └── ec2_pricing.py     # EC2 Pricing（SSD + HDD）
│   ├── solution/
│   │   ├── aos_solution.py    # AOS 编排：遍历所有 hot x warm 组合
│   │   └── ec2_solution.py    # EC2 编排：指定机型计算
│   ├── routes/routes.py       # API 路由
│   └── tests/test_v2.py       # 单元测试
├── frontend/                  # React + TypeScript 前端源码
└── dist/                      # 前端构建产物（FastAPI 静态服务）
```

---

## API 接口文档

所有接口返回统一格式：

```json
{
  "code": 200,
  "result": { ... }
}
```

### POST `/v2/sizing/aos` — AOS Sizing + Pricing

遍历所有注册的 hot x warm 组合，返回每种组合的 sizing 结果与成本估算。

**请求参数：**

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
  "enableCpuShardCheck": false,
  "filterData": "",
  "pageSize": 1000,
  "page": 1
}
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `dailyDataSize` | float | 0 | 每日写入量 (GB) |
| `hotDays` | int | 0 | Hot 层保留天数 |
| `warmDays` | int | 0 | Warm 层保留天数 |
| `coldDays` | int | 0 | Cold 层保留天数 |
| `replicaNum` | int | 0 | 副本数 |
| `writePeak` | float | 0 | 峰值写入吞吐量 (MB/s) |
| `AZ` | int | 2 | 可用区数量 (1/2/3) |
| `region` | str | `US East (N. Virginia)` | AWS Region |
| `RI` | str | `0yr` | 预留期限: `0yr` / `1yr` / `3yr` |
| `paymentOptions` | str | `OD` | 付费方式: `OD` / `No Upfront` / `Partial Upfront` / `All Upfront` |
| `master` | int | 3 | Dedicated Master 数量 (0 或 3) |
| `compressionRatio` | float | 0.4 | 压缩比 (索引后/原始数据)，结构化 JSON 日志取 0.4 |
| `warmArchitecture` | str | `ultrawarm` | Warm 架构: `ultrawarm` 或 `multi_tier` (OpenSearch 3.3+) |
| `enableCpuShardCheck` | bool | false | CPU-分片比检查 (1.5 vCPU/活跃分片)，保守模式 |
| `filterData` | str | `""` | 过滤: `hotFamily-hotSize-warmSize`，如 `or1,or2-xlarge,2xlarge-large` |
| `pageSize` | int | 1000 | 每页数量 |
| `page` | int | 1 | 页码 |

**curl 示例：**

```bash
curl -X POST http://localhost:9989/v2/sizing/aos \
  -H 'Content-Type: application/json' \
  -d '{
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
    "warmArchitecture": "ultrawarm"
  }'
```

---

### POST `/v2/sizing/ec2` — EC2 Sizing + Pricing

指定 EC2 实例类型，计算单个方案的 sizing 结果与成本。

**请求参数：** 同 AOS 接口，额外增加：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `reqEC2Instance` | str | `""` | 指定 EC2 实例类型，如 `r7g.medium` 或 `or1.2xlarge.search`（AOS 专属族会自动映射到对应 EC2 族） |

**AOS → EC2 族映射：**

| AOS 族 | EC2 对标族 | 说明 |
|--------|-----------|------|
| `or1` | `r6g` | 内存优化型 (Graviton 2) |
| `or2` | `r7g` | 内存优化型 (Graviton 3) |
| `om2` | `m7g` | 通用型 (Graviton 3) |
| `oi2` | `i8ge` | 存储优化型 (Graviton 4, NVMe) |

**curl 示例：**

```bash
curl -X POST http://localhost:9989/v2/sizing/ec2 \
  -H 'Content-Type: application/json' \
  -d '{
    "dailyDataSize": 2000,
    "hotDays": 1,
    "warmDays": 7,
    "coldDays": 14,
    "replicaNum": 1,
    "writePeak": 24,
    "AZ": 2,
    "region": "US East (N. Virginia)",
    "RI": "0yr",
    "paymentOptions": "OD",
    "master": 3,
    "reqEC2Instance": "r7g.medium"
  }'
```

---

### GET `/v2/regions` — Region 列表

```bash
curl http://localhost:9989/v2/regions
```

---

### GET `/v2/instance-families` — 机型家族列表

返回所有已注册的 AOS/EC2 机型家族及其属性。

```bash
curl http://localhost:9989/v2/instance-families
```

---

## 机型吞吐量参考

所有吞吐量数据用于 sizing 引擎的节点数计算（按峰值写入吞吐量估算所需节点数）。

### AOS 机型

#### OpenSearch Optimized 系列（S3-backed segment replication）

| 实例 | medium | large | xlarge | 2xl | 4xl | 8xl | 12xl | 16xl | 24xl | 乘数 | 来源 |
|------|--------|-------|--------|-----|-----|-----|------|------|------|------|------|
| **or1** | 5.2 | 7.8 | 13.0 | 19.5 | 29.9 | 45.5 | 57.2 | 65.0 | — | 1.30x | AWS 官方基准 (+30% vs r6g) |
| **or2** | 6.6 | 9.8 | 16.4 | 24.6 | 37.7 | 57.4 | 72.2 | 82.0 | — | 1.64x | AWS 公告 2025-03 (+26% vs or1) |
| **om2** | — | 9.0 | 13.5 | 21.0 | 31.5 | 48.0 | 60.0 | 67.5 | — | 1.50x | AWS 公告 2025-03 (+15% vs or1) |
| **oi2** | — | 10.7 | 17.9 | 26.9 | 41.2 | 62.6 | 78.8 | 89.5 | — | 1.79x | AWS 公告 2025-12 (+9% vs or2) |

> oi2 为本地 NVMe 存储，无 EBS。24xlarge 吞吐量数据待补充。

#### Graviton 通用系列

**R 系列 (内存优化, 8 GiB/vCPU)**

| 实例 | medium | large | xlarge | 2xl | 4xl | 8xl | 12xl | 16xl | 乘数 | 来源 |
|------|--------|-------|--------|-----|-----|-----|------|------|------|------|
| **r6g** | — | 6.0 | 10.0 | 15.0 | 23.0 | 35.0 | 44.0 | — | 1.00x | 实测基准 |
| **r7g** | 4.6 | 6.9 | 11.5 | 17.2 | 26.4 | 40.2 | 50.6 | 57.5 | 1.15x | Graviton 3 代际估算 |
| **r8g** | 5.5 | 8.3 | 13.8 | 20.7 | 31.7 | 48.3 | 60.7 | 69.0 | 1.38x | 保守取值 (+20% vs r7g) |

**M 系列 (通用, 4 GiB/vCPU)**

| 实例 | medium | large | xlarge | 2xl | 4xl | 8xl | 12xl | 16xl | 乘数 | 来源 |
|------|--------|-------|--------|-----|-----|-----|------|------|------|------|
| **m6g** | — | 6.0 | 9.0 | 14.0 | 21.0 | 32.0 | 40.0 | — | 1.00x | 实测基准 |
| **m7g** | 4.6 | 6.9 | 10.3 | 16.1 | 24.1 | 36.8 | 46.0 | 51.7 | 1.15x | Graviton 3 代际估算 |
| **m8g** | 5.5 | 8.3 | 12.4 | 19.3 | 29.0 | 44.2 | 55.2 | 62.1 | 1.38x | 保守取值 (+20% vs m7g) |

**C 系列 (计算优化, 2 GiB/vCPU)**

| 实例 | large | xlarge | 2xl | 4xl | 8xl | 12xl | 16xl | 乘数 | 来源 |
|------|-------|--------|-----|-----|-----|------|------|------|------|
| **c6g** | 5.0 | 8.0 | 14.0 | 18.0 | 27.0 | 34.0 | — | 1.00x | 实测基准 |
| **c7g** | 5.8 | 9.2 | 16.1 | 20.7 | 31.0 | 39.1 | 43.7 | 1.15x | Graviton 3 代际估算 |
| **c8g** | 6.6 | 10.6 | 18.5 | 23.8 | 35.6 | 44.9 | 50.2 | 1.32x | 保守取值 (+15% vs c7g) |

> 单位: MB/s。"—" 表示该 size 不可用。

### EC2 机型

EC2 自建 Elasticsearch 使用相同的吞吐量基准（同 CPU 架构）。

EC2 中 `or1` 映射到 `r6g` 吞吐量，`or2` 映射到 `r7g`，`om2` 映射到 `m7g`，`oi2` 映射到 `i8ge`，用于 AOS Optimized 实例的 EC2 对比计算。

| 族 | 可用 Size | 吞吐量 |
|------|-----------|--------|
| r7g / r8g | medium ~ 16xlarge | 同 AOS 对应族 |
| m7g / m8g | medium ~ 16xlarge | 同 AOS 对应族 |
| c7g / c8g | large ~ 16xlarge | 同 AOS 对应族 |
| r6g / m6g / c6g | large ~ 12xlarge | 基准值 (1.0x) |

### 吞吐量计算说明

所有吞吐量基于 **r6g/m6g/c6g 实测数据 x 代际乘数**：

| 代际 | 乘数基准 | 数据来源 |
|------|----------|----------|
| Graviton 2 (6g) | 1.00x | 实测 |
| Graviton 3 (7g) | 1.15x | 代际性能估算 |
| Graviton 4 (8g) R/M 系列 | 1.38x (= 1.15 x 1.20) | AWS RDS 实测 23%, 通用宣传 30%, 取保守 20% |
| Graviton 4 (8g) C 系列 | 1.32x (= 1.15 x 1.15) | 视频编码实测 12-15%, 取保守 15% |
| or1 | 1.30x | AWS 官方基准 (+30% vs r6g) |
| or2 | 1.64x | AWS 公告 2025-03 (+26% vs or1, +70% vs r7g) |
| om2 | 1.50x | AWS 公告 2025-03 (+15% vs or1, +66% vs m7g) |
| oi2 | 1.79x | AWS 公告 2025-12 (+9% vs or2, +33% vs i8g) |

> or2/om2/oi2 标记 TODO 待实测数据替换。
> r8g/m8g/c8g 无 OpenSearch 专项 indexing benchmark，基于 AWS 通用数据和 RDS 实测保守取值。

---

## Warm 架构

两种互斥架构，通过 `warmArchitecture` 参数选择：

### `ultrawarm` — UltraWarm 架构（默认）

| 层 | 实例 | 存储 |
|----|------|------|
| Hot | 任意实例 | EBS GP3 |
| Warm | ultrawarm1.medium/large | S3 Managed Storage |
| Cold | — | S3 Cold Storage |

### `multi_tier` — 多层存储架构 (OpenSearch 3.3+)

| 层 | 实例 | 存储 |
|----|------|------|
| Hot | 仅 optimized (or1/or2/om2/oi2) | oi2=本地 NVMe, 其他=EBS GP3 |
| Warm | 仅 oi2 | 本地 NVMe 缓存 (80% NVMe x 5 可寻址) |
| Cold | **不支持** | — |

`multi_tier` 模式下：
- 非 optimized 实例（如 r7g）会被自动过滤
- oi2 hot 节点不计算 EBS 存储费用
- oi2 warm 节点不计算 Managed Storage 费用
- 即使传入 `coldDays > 0`，cold 存储也自动设为 0

---

## Sizing 计算逻辑

引擎遍历所有合法的 **hot × warm** 实例组合，为每种组合独立计算节点数、存储容量和费用，最终按月度总费用升序排列。

### 输入参数

| 符号 | 参数 | 说明 |
|------|------|------|
| `D` | `dailyDataSize` | 每日原始写入量 (GB) |
| `H` | `hotDays` | Hot 层保留天数 |
| `W` | `warmDays` | Warm 层保留天数（>0 启用暖层） |
| `C` | `coldDays` | Cold 层保留天数 |
| `R` | `replicaNum` | 副本数 |
| `P` | `writePeak` | 峰值写入吞吐量 (MB/s) |
| `AZ` | `AZ` | 可用区数量 (1/2/3) |
| `CR` | `compressionRatio` | 压缩比，默认 0.4 |

### 常量定义

| 常量 | 值 | 说明 |
|------|-----|------|
| `INDEX_OVERHEAD` | 0.10 | 索引元数据开销（倒排索引、doc values），源数据 +10% |
| `LINUX_RESERVED` | 0.05 | Linux 为 root 预留 5% 磁盘 |
| `OS_OVERHEAD_PCT` | 0.20 | OpenSearch 每节点预留 20%（段合并、日志等） |
| `OS_OVERHEAD_CAP` | 20 GB | 每节点预留上限 |
| `SHARD_SIZE` | 50 GB | 日志场景推荐单分片大小 |
| `SHARDS_PER_GB_JVM` | 25 | 每 GB JVM 堆最大分片数 |
| `SHARDS_PER_NODE_LIMIT` | 1000 | 单节点分片硬上限 |
| `CPU_PER_SHARD` | 1.5 | 每活跃分片最低 vCPU（可选检查） |
| `MIN_WARM_NODES` | 2 | 暖层最少节点数 |

### Hot 层 — 节点数计算

Hot 节点数 = max(4 个维度)，每个维度独立计算后按 AZ 对齐。

#### 维度 1: 存储容量 (`num_by_storage`)

```
hot_overhead = (1 + R) × (1 + INDEX_OVERHEAD) / (1 - LINUX_RESERVED)

如果启用暖层:
    hot_required_storage = D × (H + 1) × hot_overhead × CR
否则:
    hot_required_storage = D × H × hot_overhead × CR

per_node_overhead = min(max_storage_gp3 × OS_OVERHEAD_PCT, OS_OVERHEAD_CAP)
usable_per_node   = max_storage_gp3 - per_node_overhead

num_by_storage = ⌈hot_required_storage / usable_per_node⌉, AZ 对齐
```

> 启用暖层时 +1 天：Hot→Warm 滚动迁移期间，当天数据同时存在于 Hot 和 Warm。

#### 维度 2: 分片-内存比 (`num_by_shard_memory`)

```
hot_required_shards = ⌈D × H × (1 + R) × (1 + INDEX_OVERHEAD) × CR / SHARD_SIZE⌉

jvm_heap = min(⌊memory / 2⌋, 32) GB
max_shards_per_node = min(jvm_heap × SHARDS_PER_GB_JVM, SHARDS_PER_NODE_LIMIT)

num_by_shard_memory = ⌈hot_required_shards / max_shards_per_node⌉, AZ 对齐
```

#### 维度 3: 分片-CPU 比 (`num_by_shard_cpu`，可选)

仅当 `enableCpuShardCheck = true` 时启用：

```
primary_shards = ⌈hot_required_shards / (1 + R)⌉
min_vcpus      = primary_shards × CPU_PER_SHARD

num_by_shard_cpu = ⌈min_vcpus / instance_vcpu⌉, AZ 对齐
```

#### 维度 4: 写入吞吐量 (`num_by_write_throughput`)

```
effective_throughput = base_throughput × replica_factor

Optimized 实例 (or1/or2/om2/oi2):
    replica_factor = {0副本: 1.0, 1副本: 0.7, 2副本: 0.5}

传统实例 (r7g/m7g/c7g 等):
    replica_factor = {0副本: 1.0, 1副本: 0.6, 2副本: 0.5}

num_by_write_throughput = ⌈P / effective_throughput⌉, AZ 对齐
```

> Optimized 实例副本开销更低（S3 segment replication vs node-to-node），1 副本时 0.7 vs 0.6。

#### 最终 Hot 节点数

```
hot_node_count = max(num_by_storage, num_by_shard_memory, num_by_shard_cpu, num_by_write_throughput)
```

#### AZ 对齐规则

```
如果 AZ = 1: 最少 1 个节点
如果 AZ ≥ 2: 最少 AZ 个节点，且 node_count 向上取整为 AZ 的整数倍
```

### Hot 层 — 存储计算

根据实例类型不同，存在两种存储后端：

#### EBS GP3（传统实例 + or1/or2/om2）

```
data_per_node = ⌈hot_required_storage / hot_node_count⌉

如果 data_per_node ≥ 80 GB:
    required_ebs_per_node = data_per_node + 20 GB
否则:
    required_ebs_per_node = ⌈data_per_node / 0.8⌉

required_ebs_total = hot_required_storage + per_node_overhead × hot_node_count
```

> oi2 实例使用本地 NVMe，`required_ebs_per_node = 0`。

#### S3 Managed Storage（仅 Optimized 实例 or1/or2/om2/oi2）

Optimized 实例使用 S3 Segment Replication，S3 上存一份完整索引数据的持久化副本。**不含 replica、不含 linux reserved**（与 EBS 的计算逻辑不同）：

```
如果启用暖层:
    hot_s3_storage = D × (H + 1) × (1 + INDEX_OVERHEAD) × CR
否则:
    hot_s3_storage = D × H × (1 + INDEX_OVERHEAD) × CR
```

> 传统实例（r7g/m7g/c7g 等）不使用 S3 Segment Replication，无此成本项。

### Warm 层 — 节点数与存储计算

暖层计算在两种架构下有显著差异。暖层存储**不含 replica、不含 linux reserved**（数据已在 S3 上持久化，无需本地冗余）。

#### 通用：暖层总存储需求

```
warm_required_storage = D × (1 + INDEX_OVERHEAD) × W × CR
```

#### UltraWarm 架构

| 项 | 说明 |
|-----|------|
| 实例类型 | `ultrawarm1.medium.search` / `ultrawarm1.large.search` |
| 存储后端 | S3 Managed Storage |
| 单节点容量 | 实例规格的 `max_storage_gp3`（AWS 定义的最大 Managed Storage） |

```
per_node_overhead = min(storage_per_node × OS_OVERHEAD_PCT, OS_OVERHEAD_CAP)
usable_per_node   = storage_per_node - per_node_overhead
num_by_storage    = ⌈warm_required_storage / usable_per_node⌉, AZ 对齐

warm_node_count = max(num_by_storage, MIN_WARM_NODES)

required_storage_per_node = ⌈warm_required_storage / warm_node_count⌉
```

#### Multi-tier 架构 (OpenSearch 3.3+)

| 项 | 说明 |
|-----|------|
| 实例类型 | 仅 `oi2` 系列 |
| 存储后端 | 本地 NVMe 缓存 + S3 Managed Storage 后端 |
| 单节点容量 | `OI2_WARM_STORAGE_QUOTA[size].max_warm_gb`（NVMe 80% 缓存 × 5 可寻址） |

```
OI2 暖层存储配额:
    large:    1,875 GB  (NVMe 468GB → 缓存 375GB → 最大可寻址 1,875GB)
    xlarge:   3,750 GB  (NVMe 937GB → 缓存 750GB → 最大可寻址 3,750GB)
    2xlarge:  7,500 GB  (NVMe 1,875GB → 缓存 1,500GB → 最大可寻址 7,500GB)
    4xlarge: 15,000 GB  (NVMe 3,750GB → 缓存 3,000GB → 最大可寻址 15,000GB)
    8xlarge: 30,000 GB  (NVMe 7,500GB → 缓存 6,000GB → 最大可寻址 30,000GB)

节点数计算同 UltraWarm（只是 storage_per_node 取自上表）。
```

### Cold 层 — 存储计算

| 架构 | 公式 |
|------|------|
| **UltraWarm** | `cold_required_storage = D × C × (1 + INDEX_OVERHEAD) × CR` |
| **Multi-tier** | Cold 层**不支持**，`cold_required_storage = 0`（即使 `coldDays > 0`） |

> Cold 层无实例节点，仅为 S3 存储费用。

### Master 节点选型

根据数据节点总数和总分片数，从推荐列表中选择 Master 机型：

| 数据节点数 | 总分片数上限 | Master 机型 |
|-----------|-------------|------------|
| 1 – 30 | 15,000 | m8g.large.search |
| 30 – 60 | 30,000 | m8g.xlarge.search |
| 60 – 120 | 60,000 | r8g.xlarge.search |
| 120 – 240 | 120,000 | r8g.2xlarge.search |
| 240 – 480 | 240,000 | r8g.4xlarge.search |
| 480 – 1002 | 500,000 | r8g.8xlarge.search |

Master 固定 3 节点。

### Pricing 费用计算

#### 实例费用

```
hot_instance_cost    = hot_price_per_node × hot_node_count
warm_instance_cost   = warm_price_per_node × warm_node_count
master_instance_cost = master_price_per_node × 3

# RI 预付分摊：将 Upfront 均摊到月费
如果 RI = 1yr: instance_monthly = (monthly × 12 + upfront) / 12
如果 RI = 3yr: instance_monthly = (monthly × 36 + upfront) / 36
如果 OD:       instance_monthly = monthly
```

#### 存储费用

| 成本项 | 适用条件 | 公式 |
|--------|---------|------|
| **EBS GP3 (Hot)** | 非 oi2 实例 | `ebs_per_node × gp3_price_per_gb × hot_node_count` |
| **S3 Managed Storage (Hot)** | 仅 Optimized 实例 | `hot_s3_storage × managed_storage_price_per_gb` |
| **S3 Managed Storage (Warm)** | UltraWarm 架构 | `warm_storage_per_node × managed_storage_price_per_gb × warm_node_count` |
| **S3 Managed Storage (Warm)** | Multi-tier 架构 | `warm_required_storage_total × managed_storage_price_per_gb` |
| **S3 Managed Storage (Cold)** | UltraWarm 架构 | `cold_required_storage × managed_storage_price_per_gb` |
| **Cold** | Multi-tier 架构 | 不支持，= 0 |

#### 月度总费用

```
total_monthly = instance_total (含 RI 分摊)
              + hot_ebs_cost
              + hot_s3_cost
              + warm_storage_cost
              + cold_storage_cost
```

### 数值计算示例

**输入**: `D=2000GB, H=7, W=30, C=0, R=1, P=24MB/s, AZ=2, CR=0.4`

#### Hot 层（以 `or1.xlarge.search` 为例）

```
# 存储
hot_overhead = (1+1) × (1+0.1) / (1-0.05) = 2.3158
hot_required_storage = 2000 × (7+1) × 2.3158 × 0.4 = 7,411 GB

max_storage_gp3 = 1,024 GB (or1.xlarge)
per_node_overhead = min(1024 × 0.2, 20) = 20 GB
usable = 1024 - 20 = 1,004 GB
num_by_storage = ⌈7411 / 1004⌉ = 8, AZ 对齐 → 8

# 分片
hot_required_shards = ⌈2000 × 7 × 2 × 1.1 × 0.4 / 50⌉ = ⌈246.4 / 50⌉ = 5
jvm_heap = min(16/2, 32) = 8 GB  (xlarge = 16GB memory)
max_shards_per_node = min(8 × 25, 1000) = 200
num_by_shard_memory = ⌈5 / 200⌉ = 1, AZ 对齐 → 2

# 写入吞吐量
or1.xlarge throughput = 13.0 MB/s
effective = 13.0 × 0.7 = 9.1 MB/s  (1副本, Optimized)
num_by_write_throughput = ⌈24 / 9.1⌉ = 3, AZ 对齐 → 4

hot_node_count = max(8, 2, 0, 4) = 8
```

#### Hot S3 Managed Storage

```
hot_s3_storage = 2000 × 8 × 1.1 × 0.4 = 7,040 GB
费用 = 7040 × $0.024 = $168.96/月
```

#### Warm 层（UltraWarm, `ultrawarm1.medium.search`）

```
warm_required_storage = 2000 × 1.1 × 30 × 0.4 = 26,400 GB

storage_per_node = 1,536 GB (ultrawarm1.medium 规格)
per_node_overhead = min(1536 × 0.2, 20) = 20 GB
usable = 1536 - 20 = 1,516 GB
num_by_storage = ⌈26400 / 1516⌉ = 18, AZ 对齐 → 18

warm_node_count = max(18, 2) = 18
required_storage_per_node = ⌈26400 / 18⌉ = 1,467 GB
费用 = 1467 × $0.024 × 18 = $633.74/月
```

#### Warm 层（Multi-tier, `oi2.2xlarge.search`）

```
warm_required_storage = 26,400 GB  (同上)

storage_per_node = 7,500 GB (oi2.2xlarge max_warm_gb)
per_node_overhead = min(7500 × 0.2, 20) = 20 GB
usable = 7500 - 20 = 7,480 GB
num_by_storage = ⌈26400 / 7480⌉ = 4, AZ 对齐 → 4

warm_node_count = max(4, 2) = 4
required_storage_per_node = ⌈26400 / 4⌉ = 6,600 GB
S3 存储费用 = 26400 × $0.024 = $633.60/月
```

---

## 生产部署

### systemd 服务

```bash
# 创建虚拟环境
cd /opt/app/aos/aos-sizing-api
uv venv -p 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
```

```ini
# /etc/systemd/system/aos-api.service
[Unit]
Description=AOS Sizing API
After=network.target

[Service]
ExecStart=/opt/app/aos/aos-sizing-api/.venv/bin/python /opt/app/aos/aos-sizing-api/app.py
WorkingDirectory=/opt/app/aos/aos-sizing-api/
Restart=always
User=root
Environment="PATH=/opt/app/aos/aos-sizing-api/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
Environment="DATA_SOURCE=api"

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable aos-api.service
sudo systemctl start aos-api.service
sudo systemctl status aos-api.service

# 查看日志
journalctl -u aos-api.service -f
```

### 线上地址

http://aos-sizing-alb-1600186889.us-east-1.elb.amazonaws.com:6688/

---

## 测试

```bash
# 运行全部测试
python -m pytest v2/tests/test_v2.py -v

# 快速运行
python -m pytest -q
```

---

## 添加新机型

只需两步，**不需要修改任何计算引擎代码**：

### 1. 注册机型 (`v2/config/instance_families.py`)

```python
AOS_NEW = InstanceFamily(
    name="new_family",
    service_type=ServiceType.AOS,
    storage_backend=StorageBackend.EBS_GP3,
    is_optimized=True,
    memory_per_vcpu=8,
    available_sizes=_ALL_SIZES,
    write_throughput=_scale_throughput(_R6G_BASE, 1.5),  # 基于基准 x 乘数
)

# 加入 AOS_FAMILIES 注册表
```

### 2. 添加数据

- **Excel 模式**: 在对应 xlsx 文件中添加规格和定价行
- **API 模式**: 自动从 AWS Pricing API 拉取，无需额外操作

### 3. 更新测试

在 `v2/tests/test_v2.py` 的 `test_aos_families_registered` / `test_ec2_families_registered` 断言中添加新族名。
