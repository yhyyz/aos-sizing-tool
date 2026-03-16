"""
OpenSearch / Elasticsearch Sizing 通用常量

所有计算公式中的常量集中管理。
参考来源:
- AWS 文档: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/bp-storage.html
- AWS 文档: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/bp-sharding.html
- AWS 博客 (2026-02): https://aws.amazon.com/blogs/big-data/best-practices-for-right-sizing-amazon-opensearch-service-domains/
"""


# ============================================================
# 存储计算相关
# ============================================================

# 默认压缩比：索引后数据 / 原始 JSON 数据
# 对于结构化 JSON 日志（如 CloudWatch、VPC Flow Logs），0.4 是合理值
# 对于非结构化文本日志，建议使用 0.5-0.7
DEFAULT_COMPRESSION_RATIO = 0.4

# 索引开销：OpenSearch 索引元数据（倒排索引、doc values 等）约占源数据 10%
# 来源: AWS 文档 "source data + index ≈ 110% of source"
AOS_INDEX_OVERHEAD = 0.1

# Linux 预留空间：Linux 默认为 root 用户预留 5% 磁盘
LINUX_RESERVED_SPACE = 0.05

# OpenSearch Service 磁盘预留：每个实例预留 20%（最多 20 GiB）用于段合并、日志等
# 来源: AWS bp-storage.html "OpenSearch Service reserves 20% ... (up to 20 GiB)"
OS_OVERHEAD_PERCENT = 0.20
AOS_OVERHEAD_MAX_GB = 20

# EC2 自建集群磁盘规划目标：保留 20% 作为 watermark 缓冲（无上限）
# 来源: AWS bp-sharding.html "stay below 80% disk usage"
DISK_WATERMARK_THRESHOLD = 0.2


# ============================================================
# 分片策略相关
# ============================================================

# 每 GB JVM 堆内存最大分片数
# 来源: AWS bp-sharding.html + Well-Architected Lens (AOSPERF01-BP03)
# "have no more than 25 shards per GiB of Java heap"
SHARDS_NUM_PER_GB_JVM = 25

# 日志分析场景单分片推荐大小 (GB)
# 来源: AWS 文档 "30-50 GiB for write-heavy workloads such as log analytics"
BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG = 50

# 单 CPU 核心可承载的活跃分片数
# 来源: AWS Well-Architected AOSPERF01-BP02 "at least 1.5 vCPU per active shard"
BEST_PRACTICE_SINGLE_CPU_SHARD = 1.5

# 每节点分片硬限制
# 来源: AWS bp-sharding.html
HARD_LIMIT_SHARDS_PER_NODE = 1000


# ============================================================
# 热转暖相关
# ============================================================

# 热转暖磁盘额外开销倍数（滚动索引期间需要额外空间）
HOT_TO_WARM_DISK_OVERHEAD = 3

# 热转暖单索引最大大小 (GB)
HOT_TO_WARM_MAX_INDEX_SIZE = 300


# ============================================================
# 节点数限制 (OpenSearch 2.17+)
# ============================================================

# 传统实例 (Graviton 2/3/4: c7g, m7g, r7g 等)
MAX_NODES_TRADITIONAL = {
    1: 334,  # 单 AZ
    2: 668,  # 双 AZ
    3: 1002,  # 三 AZ
}

# Optimized 实例 medium/large 尺寸
MAX_NODES_OPTIMIZED_SMALL = {
    1: 334,
    2: 668,
    3: 1002,
}

# Optimized 实例 xlarge 及以上
MAX_NODES_OPTIMIZED_XLARGE_UP = {
    1: 334,
    2: 668,
    3: 1002,
}

# 传统实例 (非 or1 xlarge+) 硬上限
MAX_NODES_NON_OPTIMIZED_CAP = 400

# Warm 节点限制
MAX_WARM_NODES = {
    1: 250,
    2: 500,
    3: 750,
}

# 最小 warm 节点数
MIN_WARM_NODES = 2


# ============================================================
# Dedicated Master 配置
# ============================================================

# AOS Dedicated Master 推荐列表（按数据节点数选择 master 机型）
AOS_DEDICATED_MASTER_LIST = [
    {
        "min_nodes": 1,
        "max_nodes": 30,
        "max_shards": 15_000,
        "instance_type": "m8g.large.search",
    },
    {
        "min_nodes": 30,
        "max_nodes": 60,
        "max_shards": 30_000,
        "instance_type": "m8g.xlarge.search",
    },
    {
        "min_nodes": 60,
        "max_nodes": 120,
        "max_shards": 60_000,
        "instance_type": "r8g.xlarge.search",
    },
    {
        "min_nodes": 120,
        "max_nodes": 240,
        "max_shards": 120_000,
        "instance_type": "r8g.2xlarge.search",
    },
    {
        "min_nodes": 240,
        "max_nodes": 480,
        "max_shards": 240_000,
        "instance_type": "r8g.4xlarge.search",
    },
    {
        "min_nodes": 480,
        "max_nodes": 1002,
        "max_shards": 500_000,
        "instance_type": "r8g.8xlarge.search",
    },
]

# EC2 自建 Dedicated Master 推荐列表
EC2_DEDICATED_MASTER_LIST = [
    {
        "min_nodes": 1,
        "max_nodes": 30,
        "max_shards": 15_000,
        "instance_type": "m8g.large",
    },
    {
        "min_nodes": 30,
        "max_nodes": 60,
        "max_shards": 30_000,
        "instance_type": "m8g.xlarge",
    },
    {
        "min_nodes": 60,
        "max_nodes": 120,
        "max_shards": 60_000,
        "instance_type": "r8g.xlarge",
    },
    {
        "min_nodes": 120,
        "max_nodes": 240,
        "max_shards": 120_000,
        "instance_type": "r8g.2xlarge",
    },
    {
        "min_nodes": 240,
        "max_nodes": 480,
        "max_shards": 240_000,
        "instance_type": "r8g.4xlarge",
    },
    {
        "min_nodes": 480,
        "max_nodes": 1002,
        "max_shards": 500_000,
        "instance_type": "r8g.8xlarge",
    },
]

# 默认 fallback master 类型
AOS_DEFAULT_MASTER_TYPE = "r8g.8xlarge.search"
EC2_DEFAULT_MASTER_TYPE = "r8g.8xlarge"
