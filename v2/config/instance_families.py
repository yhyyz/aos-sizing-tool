"""
机型家族注册表 — 添加新机型的唯一扩展点

设计原则:
- 添加新机型只需在此文件注册一个 InstanceFamily + 在 Excel 中添加规格/定价数据
- 不需要修改任何计算引擎代码

架构说明:
- UltraWarm 架构: 任意 hot 实例 + ultrawarm1 warm 节点 + 可选 cold tier
- 多层存储架构 (OpenSearch 3.3+): OR1/OR2/OM2/OI2 hot + OI2 warm + 不支持 cold tier
  两种架构互斥，不能在同一域中混用
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Mapping, Optional


class StorageBackend(Enum):
    EBS_GP3 = "ebs_gp3"
    LOCAL_NVME = "local_nvme"
    EC2_EBS = "ec2_ebs"


class WarmArchitecture(Enum):
    ULTRAWARM = "ultrawarm"
    MULTI_TIER = "multi_tier"


class ServiceType(Enum):
    AOS = "aos"
    EC2 = "ec2"


@dataclass
class InstanceFamily:
    name: str  # e.g. "or2", "om2", "oi2"
    service_type: ServiceType
    storage_backend: StorageBackend
    is_optimized: bool  # OpenSearch Optimized (S3-backed segment replication)?
    memory_per_vcpu: int  # GiB per vCPU: 4=M系, 8=R系, 2=C系
    needs_ebs_config: bool = True
    can_be_warm: bool = False  # OI2 only (multi-tier architecture)
    supported_warm_architectures: List[WarmArchitecture] = field(
        default_factory=lambda: [WarmArchitecture.ULTRAWARM]
    )
    max_node_limit_small: int = 400  # medium/large (OpenSearch 2.17+)
    max_node_limit_xlarge_up: int = 1002  # xlarge+ (OpenSearch 2.17+)
    available_sizes: List[str] = field(default_factory=list)

    # 写入吞吐量 (MB/s)，key = size name (e.g. "medium", "large", "xlarge")
    # 留空 = 待填入性能测试数据
    write_throughput: Dict[str, float] = field(default_factory=dict)


def _scale_throughput(
    base: Mapping[str, float], multiplier: float, sizes: Optional[List[str]] = None
) -> Dict[str, float]:
    result = {}
    for size, val in base.items():
        if sizes is None or size in sizes:
            result[size] = round(val * multiplier, 1)
    return result


# ============================================================
# 基准吞吐量 (MB/s) — 来自 r6g 实测数据
# ============================================================

_R6G_BASE: Dict[str, float] = {
    "medium": 4.0,
    "large": 6.0,
    "xlarge": 10.0,
    "2xlarge": 15.0,
    "4xlarge": 23.0,
    "8xlarge": 35.0,
    "12xlarge": 44.0,
    "16xlarge": 50.0,
}

_C6G_BASE: Dict[str, float] = {
    "large": 5.0,
    "xlarge": 8.0,
    "2xlarge": 14.0,
    "4xlarge": 18.0,
    "8xlarge": 27.0,
    "12xlarge": 34.0,
    "16xlarge": 38.0,
}

_M6G_BASE: Dict[str, float] = {
    "medium": 4.0,
    "large": 6.0,
    "xlarge": 9.0,
    "2xlarge": 14.0,
    "4xlarge": 21.0,
    "8xlarge": 32.0,
    "12xlarge": 40.0,
    "16xlarge": 45.0,
}

_ALL_SIZES = [
    "medium",
    "large",
    "xlarge",
    "2xlarge",
    "4xlarge",
    "8xlarge",
    "12xlarge",
    "16xlarge",
]
_NO_MEDIUM = [
    "large",
    "xlarge",
    "2xlarge",
    "4xlarge",
    "8xlarge",
    "12xlarge",
    "16xlarge",
]
_OI2_SIZES = [
    "large",
    "xlarge",
    "2xlarge",
    "4xlarge",
    "8xlarge",
    "12xlarge",
    "16xlarge",
    "24xlarge",
]
_OI2_WARM_SIZES = ["large", "xlarge", "2xlarge", "4xlarge", "8xlarge"]


# ============================================================
# AOS 机型家族 (带 .search 后缀)
# ============================================================

AOS_OR1 = InstanceFamily(
    name="or1",
    service_type=ServiceType.AOS,
    storage_backend=StorageBackend.EBS_GP3,
    is_optimized=True,
    memory_per_vcpu=8,
    supported_warm_architectures=[
        WarmArchitecture.ULTRAWARM,
        WarmArchitecture.MULTI_TIER,
    ],
    available_sizes=_ALL_SIZES,
    # or1 vs r6g: +30% (AWS 官方基准测试)
    write_throughput=_scale_throughput(_R6G_BASE, 1.3),
)

AOS_OR2 = InstanceFamily(
    name="or2",
    service_type=ServiceType.AOS,
    storage_backend=StorageBackend.EBS_GP3,
    is_optimized=True,
    memory_per_vcpu=8,
    supported_warm_architectures=[
        WarmArchitecture.ULTRAWARM,
        WarmArchitecture.MULTI_TIER,
    ],
    available_sizes=_ALL_SIZES,
    # or2 vs or1: +26%, or2 vs r7g: +70% (AWS 公告 2025-03)
    # TODO: 待性能测试后替换为实测数据
    write_throughput=_scale_throughput(_R6G_BASE, 1.64),
)

AOS_OM2 = InstanceFamily(
    name="om2",
    service_type=ServiceType.AOS,
    storage_backend=StorageBackend.EBS_GP3,
    is_optimized=True,
    memory_per_vcpu=4,
    supported_warm_architectures=[
        WarmArchitecture.ULTRAWARM,
        WarmArchitecture.MULTI_TIER,
    ],
    available_sizes=_NO_MEDIUM,
    # om2 vs or1: +15%, om2 vs m7g: +66% (AWS 公告 2025-03)
    # TODO: 待性能测试后替换为实测数据
    write_throughput=_scale_throughput(_M6G_BASE, 1.5, sizes=_NO_MEDIUM),
)

AOS_OI2 = InstanceFamily(
    name="oi2",
    service_type=ServiceType.AOS,
    storage_backend=StorageBackend.LOCAL_NVME,
    is_optimized=True,
    memory_per_vcpu=8,
    needs_ebs_config=False,
    can_be_warm=True,
    supported_warm_architectures=[WarmArchitecture.MULTI_TIER],
    available_sizes=_OI2_SIZES,
    # oi2 vs or2: +9%, oi2 vs i8g: +33% (AWS 公告 2025-12)
    # TODO: 待性能测试后替换为实测数据
    write_throughput=_scale_throughput(_R6G_BASE, 1.79, sizes=_OI2_SIZES),
)

AOS_R7G = InstanceFamily(
    name="r7g",
    service_type=ServiceType.AOS,
    storage_backend=StorageBackend.EBS_GP3,
    is_optimized=False,
    memory_per_vcpu=8,
    max_node_limit_xlarge_up=400,
    available_sizes=_ALL_SIZES,
    write_throughput=_scale_throughput(_R6G_BASE, 1.15),
)

AOS_M7G = InstanceFamily(
    name="m7g",
    service_type=ServiceType.AOS,
    storage_backend=StorageBackend.EBS_GP3,
    is_optimized=False,
    memory_per_vcpu=4,
    max_node_limit_xlarge_up=400,
    available_sizes=_ALL_SIZES,
    write_throughput=_scale_throughput(_M6G_BASE, 1.15),
)

AOS_C7G = InstanceFamily(
    name="c7g",
    service_type=ServiceType.AOS,
    storage_backend=StorageBackend.EBS_GP3,
    is_optimized=False,
    memory_per_vcpu=2,
    max_node_limit_xlarge_up=400,
    available_sizes=_NO_MEDIUM,
    write_throughput=_scale_throughput(_C6G_BASE, 1.15),
)

# Graviton4 (8 代) — 无 OpenSearch 专项 indexing benchmark
# AWS 官方通用宣传 "up to 30% vs Graviton3"；RDS 实测 23%；视频编码 12-15%
# 取保守值：r8g/m8g × 1.2 on top of 7g，c8g × 1.15 on top of c7g
# 来源: AWS RDS Graviton4 博客 2025-06, OpenSearch 公告 2025-10

AOS_R8G = InstanceFamily(
    name="r8g",
    service_type=ServiceType.AOS,
    storage_backend=StorageBackend.EBS_GP3,
    is_optimized=False,
    memory_per_vcpu=8,
    max_node_limit_xlarge_up=400,
    available_sizes=_ALL_SIZES,
    # r8g vs r7g: +20% (保守取值, AWS 通用 30%, RDS 实测 23%)
    write_throughput=_scale_throughput(_R6G_BASE, 1.38),
)

AOS_M8G = InstanceFamily(
    name="m8g",
    service_type=ServiceType.AOS,
    storage_backend=StorageBackend.EBS_GP3,
    is_optimized=False,
    memory_per_vcpu=4,
    max_node_limit_xlarge_up=400,
    available_sizes=_ALL_SIZES,
    # m8g vs m7g: +20% (同 r8g 取值逻辑)
    write_throughput=_scale_throughput(_M6G_BASE, 1.38),
)

AOS_C8G = InstanceFamily(
    name="c8g",
    service_type=ServiceType.AOS,
    storage_backend=StorageBackend.EBS_GP3,
    is_optimized=False,
    memory_per_vcpu=2,
    max_node_limit_xlarge_up=400,
    available_sizes=_NO_MEDIUM,
    # c8g vs c7g: +15% (计算密集型场景提升偏低, 视频编码实测 12-15%)
    write_throughput=_scale_throughput(_C6G_BASE, 1.32),
)

# 保留旧代机型
AOS_R6G = InstanceFamily(
    name="r6g",
    service_type=ServiceType.AOS,
    storage_backend=StorageBackend.EBS_GP3,
    is_optimized=False,
    memory_per_vcpu=8,
    max_node_limit_xlarge_up=200,
    available_sizes=["large", "xlarge", "2xlarge", "4xlarge", "8xlarge", "12xlarge"],
    write_throughput={
        k: v for k, v in _R6G_BASE.items() if k != "medium" and k != "16xlarge"
    },
)

AOS_M6G = InstanceFamily(
    name="m6g",
    service_type=ServiceType.AOS,
    storage_backend=StorageBackend.EBS_GP3,
    is_optimized=False,
    memory_per_vcpu=4,
    max_node_limit_xlarge_up=200,
    available_sizes=["large", "xlarge", "2xlarge", "4xlarge", "8xlarge", "12xlarge"],
    write_throughput={
        k: v for k, v in _M6G_BASE.items() if k != "medium" and k != "16xlarge"
    },
)

AOS_C6G = InstanceFamily(
    name="c6g",
    service_type=ServiceType.AOS,
    storage_backend=StorageBackend.EBS_GP3,
    is_optimized=False,
    memory_per_vcpu=2,
    max_node_limit_xlarge_up=200,
    available_sizes=["large", "xlarge", "2xlarge", "4xlarge", "8xlarge", "12xlarge"],
    write_throughput={k: v for k, v in _C6G_BASE.items() if k != "16xlarge"},
)


# ============================================================
# EC2 机型家族 (无 .search 后缀)
# ============================================================

EC2_R7G = InstanceFamily(
    name="r7g",
    service_type=ServiceType.EC2,
    storage_backend=StorageBackend.EC2_EBS,
    is_optimized=False,
    memory_per_vcpu=8,
    available_sizes=_ALL_SIZES,
    write_throughput=_scale_throughput(_R6G_BASE, 1.15),
)

EC2_M7G = InstanceFamily(
    name="m7g",
    service_type=ServiceType.EC2,
    storage_backend=StorageBackend.EC2_EBS,
    is_optimized=False,
    memory_per_vcpu=4,
    available_sizes=_ALL_SIZES,
    write_throughput=_scale_throughput(_M6G_BASE, 1.15),
)

EC2_C7G = InstanceFamily(
    name="c7g",
    service_type=ServiceType.EC2,
    storage_backend=StorageBackend.EC2_EBS,
    is_optimized=False,
    memory_per_vcpu=2,
    available_sizes=_NO_MEDIUM,
    write_throughput=_scale_throughput(_C6G_BASE, 1.15),
)

EC2_R8G = InstanceFamily(
    name="r8g",
    service_type=ServiceType.EC2,
    storage_backend=StorageBackend.EC2_EBS,
    is_optimized=False,
    memory_per_vcpu=8,
    available_sizes=_ALL_SIZES,
    write_throughput=_scale_throughput(_R6G_BASE, 1.38),
)

EC2_M8G = InstanceFamily(
    name="m8g",
    service_type=ServiceType.EC2,
    storage_backend=StorageBackend.EC2_EBS,
    is_optimized=False,
    memory_per_vcpu=4,
    available_sizes=_ALL_SIZES,
    write_throughput=_scale_throughput(_M6G_BASE, 1.38),
)

EC2_C8G = InstanceFamily(
    name="c8g",
    service_type=ServiceType.EC2,
    storage_backend=StorageBackend.EC2_EBS,
    is_optimized=False,
    memory_per_vcpu=2,
    available_sizes=_NO_MEDIUM,
    write_throughput=_scale_throughput(_C6G_BASE, 1.32),
)

# EC2 的 or1 映射到 r6g
EC2_OR1 = InstanceFamily(
    name="or1",
    service_type=ServiceType.EC2,
    storage_backend=StorageBackend.EC2_EBS,
    is_optimized=False,
    memory_per_vcpu=8,
    available_sizes=["large", "xlarge", "2xlarge", "4xlarge", "8xlarge", "12xlarge"],
    write_throughput={
        k: v for k, v in _R6G_BASE.items() if k != "medium" and k != "16xlarge"
    },
)

EC2_I8GE = InstanceFamily(
    name="i8ge",
    service_type=ServiceType.EC2,
    storage_backend=StorageBackend.EC2_EBS,
    is_optimized=False,
    memory_per_vcpu=8,
    available_sizes=_OI2_SIZES,
    write_throughput=_scale_throughput(_R6G_BASE, 1.38, sizes=_OI2_SIZES),
)

EC2_R6G = InstanceFamily(
    name="r6g",
    service_type=ServiceType.EC2,
    storage_backend=StorageBackend.EC2_EBS,
    is_optimized=False,
    memory_per_vcpu=8,
    available_sizes=["large", "xlarge", "2xlarge", "4xlarge", "8xlarge", "12xlarge"],
    write_throughput={
        k: v for k, v in _R6G_BASE.items() if k != "medium" and k != "16xlarge"
    },
)

EC2_M6G = InstanceFamily(
    name="m6g",
    service_type=ServiceType.EC2,
    storage_backend=StorageBackend.EC2_EBS,
    is_optimized=False,
    memory_per_vcpu=4,
    available_sizes=["large", "xlarge", "2xlarge", "4xlarge", "8xlarge", "12xlarge"],
    write_throughput={
        k: v for k, v in _M6G_BASE.items() if k != "medium" and k != "16xlarge"
    },
)

EC2_C6G = InstanceFamily(
    name="c6g",
    service_type=ServiceType.EC2,
    storage_backend=StorageBackend.EC2_EBS,
    is_optimized=False,
    memory_per_vcpu=2,
    available_sizes=["large", "xlarge", "2xlarge", "4xlarge", "8xlarge", "12xlarge"],
    write_throughput={k: v for k, v in _C6G_BASE.items() if k != "16xlarge"},
)


# ============================================================
# 注册表
# ============================================================

AOS_FAMILIES: Dict[str, InstanceFamily] = {
    f.name: f
    for f in [
        AOS_OR1,
        AOS_OR2,
        AOS_OM2,
        AOS_OI2,
        AOS_R7G,
        AOS_R8G,
        AOS_M7G,
        AOS_M8G,
        AOS_C7G,
        AOS_C8G,
        AOS_R6G,
        AOS_M6G,
        AOS_C6G,
    ]
}

EC2_FAMILIES: Dict[str, InstanceFamily] = {
    f.name: f
    for f in [
        EC2_OR1,
        EC2_I8GE,
        EC2_R7G,
        EC2_R8G,
        EC2_M7G,
        EC2_M8G,
        EC2_C7G,
        EC2_C8G,
        EC2_R6G,
        EC2_M6G,
        EC2_C6G,
    ]
}

# OI2 warm 节点存储配额 (本地 NVMe 80% 用于缓存，最大可寻址 = 缓存 × 5)
OI2_WARM_STORAGE_QUOTA: Dict[str, Dict[str, int]] = {
    "large": {"local_gb": 468, "cache_gb": 375, "max_warm_gb": 1_875},
    "xlarge": {"local_gb": 937, "cache_gb": 750, "max_warm_gb": 3_750},
    "2xlarge": {"local_gb": 1_875, "cache_gb": 1_500, "max_warm_gb": 7_500},
    "4xlarge": {"local_gb": 3_750, "cache_gb": 3_000, "max_warm_gb": 15_000},
    "8xlarge": {"local_gb": 7_500, "cache_gb": 6_000, "max_warm_gb": 30_000},
}


def get_aos_family(family_name: str) -> Optional[InstanceFamily]:
    return AOS_FAMILIES.get(family_name)


def get_ec2_family(family_name: str) -> Optional[InstanceFamily]:
    return EC2_FAMILIES.get(family_name)


def parse_instance_type(
    instance_type: str, service_type: ServiceType
) -> tuple[str, str]:
    """
    Parse 'or2.4xlarge.search' → ('or2', '4xlarge')
    Parse 'r7g.medium' → ('r7g', 'medium')
    """
    parts = instance_type.replace(".search", "").split(".")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return instance_type, ""


def get_family_for_instance(
    instance_type: str, service_type: ServiceType
) -> Optional[InstanceFamily]:
    family_name, _ = parse_instance_type(instance_type, service_type)
    if service_type == ServiceType.AOS:
        return get_aos_family(family_name)
    return get_ec2_family(family_name)


def is_valid_warm_combination(
    hot_instance_type: str,
    warm_instance_type: str,
    warm_architecture: str,
    service_type: ServiceType,
) -> bool:
    """
    Check if a hot×warm instance combination is valid for the given warm architecture.

    UltraWarm: warm must be ultrawarm1, hot can be anything
    Multi-tier: hot must be optimized (or1/or2/om2/oi2), warm must be oi2 family
    """
    hot_family = get_family_for_instance(hot_instance_type, service_type)
    warm_family_name, _ = parse_instance_type(warm_instance_type, service_type)

    if warm_architecture == "ultrawarm":
        # UltraWarm: warm must start with "ultrawarm1", hot can be anything
        if not warm_instance_type.startswith("ultrawarm1"):
            return False
        # Hot family must support ultrawarm architecture
        if hot_family is not None:
            return WarmArchitecture.ULTRAWARM in hot_family.supported_warm_architectures
        return True

    if warm_architecture == "multi_tier":
        # Multi-tier: hot must be optimized, warm must be oi2
        if hot_family is None or not hot_family.is_optimized:
            return False
        if WarmArchitecture.MULTI_TIER not in hot_family.supported_warm_architectures:
            return False
        if warm_family_name != "oi2":
            return False
        return True

    return False


def get_write_throughput(
    instance_type: str, service_type: ServiceType
) -> Optional[float]:
    family_name, size = parse_instance_type(instance_type, service_type)
    if service_type == ServiceType.AOS:
        family = get_aos_family(family_name)
    else:
        family = get_ec2_family(family_name)
    if family and size in family.write_throughput:
        return family.write_throughput[size]
    return None
