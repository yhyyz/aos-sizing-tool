from typing import Optional
from pydantic import BaseModel, Field


class InstanceSpec(BaseModel):
    instance_type: str = Field(default="")
    max_storage_gp3: int = Field(default=0)
    cpu: int = Field(default=0)
    memory: int = Field(default=0)
    nvme_storage: int = Field(default=0)


class HotSizingResult(BaseModel):
    instance_type: str = ""
    max_storage_gp3: int = 0
    cpu: int = 0
    memory: int = 0
    num_by_storage: int = 0
    num_by_shard_memory: int = 0
    num_by_shard_cpu: int = 0
    num_by_write_throughput: int = 0
    num_by_max_metric: int = 0
    required_ebs_per_node: int = 0
    required_ebs_total: int = 0
    node_count: int = 0
    unselected_reason: str = ""


class WarmSizingResult(BaseModel):
    instance_type: str = ""
    cpu: int = 0
    memory: int = 0
    storage_per_node: int = 0
    num_by_storage: int = 0
    num_by_max_metric: int = 0
    required_storage_per_node: int = 0
    required_storage_total: int = 0
    node_count: int = 0
    unselected_reason: str = ""


class ColdStorageResult(BaseModel):
    required_storage: int = 0


class MasterSizingResult(BaseModel):
    instance_type: str = ""
    node_count: int = 0


class PricingResult(BaseModel):
    hot_instance_price_month: float = 0.0
    hot_upfront: float = 0.0
    warm_instance_price_month: float = 0.0
    master_instance_price_month: float = 0.0
    master_upfront: float = 0.0
    instance_total_price_month: float = 0.0
    hot_storage_price_month: float = 0.0
    hot_s3_storage_price_month: float = 0.0
    warm_storage_price_month: float = 0.0
    cold_storage_price_month: float = 0.0
    total_price_month: float = 0.0


class SizingSolutionItem(BaseModel):
    """Single AOS sizing solution row"""

    ROW_ID: int = 0

    # hot
    INSTANCE_TYPE: str = ""
    MAX_STORAGE_GP3: int = 0
    CPU: int = 0
    MEMORY: int = 0
    HOT_NUM_BY_STORAGE: int = 0
    HOT_NUM_BY_SHARD_MEMORY: int = 0
    HOT_NUM_BY_SHARD_CPU: int = 0
    HOT_NUM_BY_WRITE_THROUGHPUT: int = 0
    HOT_NUM_BY_MAX_METRIC: int = 0
    HOT_REQUIRED_EBS: int = 0
    HOT_REQUIRED_EBS_TOTAL: int = 0
    HOT_NUM: int = 0
    HOT_UNSELECTED: str = ""

    # warm
    WARM_INSTANCE_TYPE: str = ""
    WARM_CPU: int = 0
    WARM_MEMORY: int = 0
    STORAGE: int = 0
    WARM_NUM_BY_STORAGE: int = 0
    WARM_NUM_BY_MAX_METRIC: int = 0
    WARM_REQUIRED_STORAGE: int = 0
    WARM_REQUIRED_STORAGE_TOTAL: int = 0
    WARM_NUM: int = 0
    WARM_UNSELECTED: str = ""

    # cold
    COLD_REQUIRED_STORAGE: int = 0

    # master
    DEDICATED_MASTER_TYPE: str = ""
    MASTER_NUM: int = 0

    # pricing
    HOT_PRICE_MONTH: float = 0.0
    Upfront: float = 0.0
    WARM_PRICE_MONTH: float = 0.0
    TOTAL_PRICE_MONTH: float = 0.0
    MASTER_PRICE_MONTH: float = 0.0
    MASTER_Upfront: float = 0.0
    INSTANCE_PRICE_MONTH: float = 0.0
    HOT_STORAGE_PRICE_MONTH: float = 0.0
    HOT_S3_STORAGE: int = 0
    HOT_S3_STORAGE_PRICE_MONTH: float = 0.0
    WARM_STORAGE_PRICE_MONTH: float = 0.0
    COLD_STORAGE_PRICE_MONTH: float = 0.0


class EC2SizingSolutionItem(BaseModel):
    """Single EC2 sizing solution row"""

    # ec2 instance
    EC2_INSTANCE_TYPE: str = ""
    EC2_MAX_STORAGE_GP3: int = 0
    EC2_CPU: int = 0
    EC2_MEMORY: int = 0
    EC2_NUM_BY_STORAGE: int = 0
    EC2_NUM_BY_SHARD_MEMORY: int = 0
    EC2_NUM_BY_SHARD_CPU: int = 0
    EC2_NUM_BY_WRITE_THROUGHPUT: int = 0
    EC2_NUM_BY_MAX_METRIC: int = 0
    EC2_REQUIRED_HOT_EBS: int = 0
    EC2_REQUIRED_HOT_EBS_TOTAL: int = 0
    EC2_REQUIRED_WARM_HDD: int = 0
    EC2_REQUIRED_WARM_HDD_TOTAL: int = 0
    EC2_REQUIRED_EBS_TOTAL: int = 0
    EC2_NUM: int = 0
    EC2_UNSELECTED: str = ""

    # master
    EC2_MASTER_TYPE: str = ""
    EC2_MASTER_NUM: int = 0

    # pricing
    EC2_PRICE_MONTH: float = 0.0
    EC2_Upfront: float = 0.0
    TOTAL_PRICE_MONTH: float = 0.0
    MASTER_PRICE_MONTH: float = 0.0
    MASTER_EC2_Upfront: float = 0.0
    INSTANCE_PRICE_MONTH: float = 0.0
    HOT_STORAGE_PRICE_MONTH: float = 0.0
    WARM_STORAGE_PRICE_MONTH: float = 0.0
