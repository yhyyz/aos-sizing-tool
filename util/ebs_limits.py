"""
EBS 存储上限映射表

AWS OpenSearch / EC2 实例的 GP3 EBS 最大存储容量（GB）。
此数据不在 AWS Pricing API 中，需要手动维护。
来源: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/limits.html

新增实例类型时只需在对应字典中添加一行。
"""

from typing import Optional


AOS_TO_EC2_FAMILY: dict = {
    "or1": "r6g",
    "or2": "r7g",
    "om2": "m7g",
    "oi2": "i8ge",
}

EC2_VALID_FAMILIES: set = {"r6g", "r7g", "r8g", "m7g", "m8g", "c7g", "c8g", "i8ge"}


# ---------------------------------------------------------------------------
# AOS (Amazon OpenSearch Service) — 实例类型以 .search 结尾
# ---------------------------------------------------------------------------
AOS_EBS_LIMITS: dict = {
    # --- or1 (Memory optimized, OR1) ---
    "or1.medium.search": 768,
    "or1.large.search": 1532,
    "or1.xlarge.search": 3072,
    "or1.2xlarge.search": 6144,
    "or1.4xlarge.search": 12288,
    "or1.8xlarge.search": 16384,
    "or1.12xlarge.search": 24576,
    "or1.16xlarge.search": 36864,
    # --- or2 (Memory optimized, OR2 — 与 or1 同架构) ---
    "or2.medium.search": 768,
    "or2.large.search": 1532,
    "or2.xlarge.search": 3072,
    "or2.2xlarge.search": 6144,
    "or2.4xlarge.search": 12288,
    "or2.8xlarge.search": 16384,
    "or2.12xlarge.search": 24576,
    "or2.16xlarge.search": 36864,
    # --- om2 (General purpose, OM2 — 与 m7g 同级) ---
    "om2.large.search": 1536,
    "om2.xlarge.search": 2048,
    "om2.2xlarge.search": 3072,
    "om2.4xlarge.search": 6144,
    "om2.8xlarge.search": 12288,
    "om2.12xlarge.search": 18432,
    "om2.16xlarge.search": 24576,
    # --- r7g (Memory optimized) ---
    "r7g.medium.search": 768,
    "r7g.large.search": 1536,
    "r7g.xlarge.search": 3072,
    "r7g.2xlarge.search": 6144,
    "r7g.4xlarge.search": 12288,
    "r7g.8xlarge.search": 16384,
    "r7g.12xlarge.search": 24576,
    "r7g.16xlarge.search": 36864,
    # --- r8g (Memory optimized, 下一代 — 与 r7g 同级) ---
    "r8g.medium.search": 768,
    "r8g.large.search": 1536,
    "r8g.xlarge.search": 3072,
    "r8g.2xlarge.search": 6144,
    "r8g.4xlarge.search": 12288,
    "r8g.8xlarge.search": 16384,
    "r8g.12xlarge.search": 24576,
    "r8g.16xlarge.search": 36864,
    # --- m7g (General purpose) ---
    "m7g.medium.search": 768,
    "m7g.large.search": 1536,
    "m7g.xlarge.search": 2048,
    "m7g.2xlarge.search": 3072,
    "m7g.4xlarge.search": 6144,
    "m7g.8xlarge.search": 12288,
    "m7g.12xlarge.search": 18432,
    "m7g.16xlarge.search": 24576,
    # --- m8g (General purpose, 下一代 — 与 m7g 同级) ---
    "m8g.medium.search": 768,
    "m8g.large.search": 1536,
    "m8g.xlarge.search": 2048,
    "m8g.2xlarge.search": 3072,
    "m8g.4xlarge.search": 6144,
    "m8g.8xlarge.search": 12288,
    "m8g.12xlarge.search": 18432,
    "m8g.16xlarge.search": 24576,
    # --- c7g (Compute optimized) ---
    "c7g.large.search": 256,
    "c7g.xlarge.search": 512,
    "c7g.2xlarge.search": 1024,
    "c7g.4xlarge.search": 1536,
    "c7g.8xlarge.search": 3072,
    "c7g.12xlarge.search": 4608,
    "c7g.16xlarge.search": 6144,
    # --- c8g (Compute optimized, 下一代 — 与 c7g 同级) ---
    "c8g.large.search": 256,
    "c8g.xlarge.search": 512,
    "c8g.2xlarge.search": 1024,
    "c8g.4xlarge.search": 1536,
    "c8g.8xlarge.search": 3072,
    "c8g.12xlarge.search": 4608,
    "c8g.16xlarge.search": 6144,
}

# oi2 本地 NVMe 存储容量 (GB) — oi2 无 EBS，sizing 用此值算 storage-based 节点数
# 来源: AWS OpenSearch oi2 实例规格 (2025-12)
AOS_OI2_NVME: dict = {
    "oi2.large.search": 468,
    "oi2.xlarge.search": 937,
    "oi2.2xlarge.search": 1875,
    "oi2.4xlarge.search": 3750,
    "oi2.8xlarge.search": 7500,
    "oi2.12xlarge.search": 11250,
    "oi2.16xlarge.search": 15000,
    "oi2.24xlarge.search": 22500,
}

# AOS 最小存储 (GB)
AOS_MIN_STORAGE: dict = {
    "or1": 20,
    "or2": 20,
}
AOS_MIN_STORAGE_DEFAULT = 10

# ---------------------------------------------------------------------------
# EC2 — 实例类型不带 .search 后缀
# ---------------------------------------------------------------------------
EC2_EBS_LIMITS: dict = {
    "r6g.large": 1536,
    "r6g.xlarge": 3072,
    "r6g.2xlarge": 6144,
    "r6g.4xlarge": 12288,
    "r6g.8xlarge": 16384,
    "r6g.12xlarge": 24576,
    "r7g.medium": 768,
    "r7g.large": 1536,
    "r7g.xlarge": 3072,
    "r7g.2xlarge": 6144,
    "r7g.4xlarge": 12288,
    "r7g.8xlarge": 16384,
    "r7g.12xlarge": 24576,
    "r7g.16xlarge": 36864,
    "r8g.medium": 768,
    "r8g.large": 1536,
    "r8g.xlarge": 3072,
    "r8g.2xlarge": 6144,
    "r8g.4xlarge": 12288,
    "r8g.8xlarge": 16384,
    "r8g.12xlarge": 24576,
    "r8g.16xlarge": 36864,
    "m7g.medium": 768,
    "m7g.large": 1536,
    "m7g.xlarge": 2048,
    "m7g.2xlarge": 3072,
    "m7g.4xlarge": 6144,
    "m7g.8xlarge": 12288,
    "m7g.12xlarge": 18432,
    "m7g.16xlarge": 24576,
    "m8g.medium": 768,
    "m8g.large": 1536,
    "m8g.xlarge": 2048,
    "m8g.2xlarge": 3072,
    "m8g.4xlarge": 6144,
    "m8g.8xlarge": 12288,
    "m8g.12xlarge": 18432,
    "m8g.16xlarge": 24576,
    "c7g.large": 256,
    "c7g.xlarge": 512,
    "c7g.2xlarge": 1024,
    "c7g.4xlarge": 1536,
    "c7g.8xlarge": 3072,
    "c7g.12xlarge": 4608,
    "c7g.16xlarge": 6144,
    "c8g.large": 256,
    "c8g.xlarge": 512,
    "c8g.2xlarge": 1024,
    "c8g.4xlarge": 1536,
    "c8g.8xlarge": 3072,
    "c8g.12xlarge": 4608,
    "c8g.16xlarge": 6144,
    # i8ge — 本地 NVMe 容量 (GB)，EC2 对比时作为最大可用存储
    "i8ge.large": 468,
    "i8ge.xlarge": 937,
    "i8ge.2xlarge": 1875,
    "i8ge.4xlarge": 3750,
    "i8ge.8xlarge": 7500,
    "i8ge.12xlarge": 11250,
    "i8ge.16xlarge": 15000,
    "i8ge.24xlarge": 22500,
}

EC2_MIN_STORAGE_DEFAULT = 10


# ---------------------------------------------------------------------------
# 查询接口
# ---------------------------------------------------------------------------


def get_aos_ebs_limit(instance_type: str) -> Optional[int]:
    """返回 AOS 实例的 GP3 EBS 最大存储 (GB)，不存在返回 None"""
    return AOS_EBS_LIMITS.get(instance_type)


def get_ec2_ebs_limit(instance_type: str) -> Optional[int]:
    """返回 EC2 实例的 GP3 EBS 最大存储 (GB)，不存在返回 None"""
    return EC2_EBS_LIMITS.get(instance_type)


def get_aos_min_storage(instance_type: str) -> int:
    """返回 AOS 实例的最小存储 (GB)"""
    family = instance_type.split(".")[0]
    return AOS_MIN_STORAGE.get(family, AOS_MIN_STORAGE_DEFAULT)


def get_ec2_min_storage(instance_type: str) -> int:
    """返回 EC2 实例的最小存储 (GB)"""
    return EC2_MIN_STORAGE_DEFAULT


def resolve_ec2_instance_type(aos_instance: str) -> str:
    """'or1.large.search' → 'r6g.large', 'r7g.xlarge.search' → 'r7g.xlarge'"""
    name = aos_instance.replace(".search", "")
    parts = name.split(".")
    ec2_family = AOS_TO_EC2_FAMILY.get(parts[0])
    if ec2_family:
        parts[0] = ec2_family
    return ".".join(parts)


def is_aos_specific_family(instance_type: str) -> bool:
    """or1/or2/om2 等 AOS 专属族在 EC2 中不存在，对比时需要调整副本数"""
    family = instance_type.split(".")[0]
    return family in AOS_TO_EC2_FAMILY
