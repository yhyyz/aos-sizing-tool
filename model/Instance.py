from typing import Optional, List

from pydantic import BaseModel, Field, validator


class HotInstance(BaseModel):
    INSTANCE_TYPE: str = Field(default="", description="INSTANCE_TYPE")
    MAX_STORAGE_GP3: int = Field(default=0, description="MAX_STORAGE_GP3")
    CPU: int = Field(default=0, description="CPU")
    MEMORY: int = Field(default=0, description="MEMORY")


class HotInstanceSizing(HotInstance):
    HOT_NUM_BY_STORAGE: int = Field(default=0, description="HOT_NUM_BY_STORAGE")
    HOT_NUM_BY_SHARD_MEMORY: int = Field(default=0, description="HOT_NUM_BY_SHARD_MEMORY")
    HOT_NUM_BY_SHARD_CPU: int = Field(default=0, description="HOT_NUM_BY_SHARD_CPU")
    HOT_NUM_BY_WRITE_THROUGHPUT: int = Field(default=0, description="HOT_NUM_BY_WRITE_THROUGHPUT")
    HOT_NUM_BY_MAX_METRIC: int = Field(default=0, description="HOT_NUM_BY_MAX_METRIC")
    HOT_REQUIRED_EBS: int = Field(default=0, description="HOT_REQUIRED_EBS")
    HOT_REQUIRED_EBS_TOTAL: int = Field(default=0, description="HOT_REQUIRED_EBS_TOTAL")
    HOT_NUM:int = Field(default=0, description="HOT_NUM")
    HOT_UNSELECTED: str = Field(default="", description="unselect reason")




class WarmInstance(BaseModel):
    WARM_INSTANCE_TYPE: str = Field(default="", description="WARM_INSTANCE_TYPE")
    STORAGE: int = Field(default=0, description="STORAGE")
    WARM_CPU: int = Field(default=0, description="WARM_CPU")
    WARM_MEMORY: int = Field(default=0, description="WARM_MEMORY")


class WarmInstanceSizing(WarmInstance):
    WARM_NUM_BY_STORAGE: int = Field(default=0, description="WARM_NUM_BY_STORAGE")
    WARM_NUM_BY_MAX_METRIC: int = Field(default=0, description="WARM_NUM_BY_MAX_METRIC")
    WARM_REQUIRED_STORAGE: int = Field(default=0, description="WARM_REQUIRED_STORAGE")
    WARM_REQUIRED_STORAGE_TOTAL: int = Field(default=0, description="WARM_REQUIRED_STORAGE_TOTAL")
    WARM_NUM : int = Field(default=0, description="WARM_NUM")
    WARM_UNSELECTED: str = Field(default="", description="unselect reason")

class ColdStorage(BaseModel):
    COLD_REQUIRED_STORAGE:int = Field(default=0, description="WARM_REQUIRED_STORAGE")


class MasterInstanceSizing(BaseModel):
    DEDICATED_MASTER_TYPE: str = Field(default="", description="MASTER_TYPE")
    MASTER_NUM: int = Field(default=0, description="MASTER_NUM")

class PricingBase(BaseModel):
    HOT_PRICE_MONTH: int = Field(default=0, description="HOT_PRICE_MONTH")
    Upfront: int = Field(default=0, description="HOT_PRICE_MONTH")
    WARM_PRICE_MONTH: int = Field(default=0, description="WARM_PRICE_MONTH")
    TOTAL_PRICE_MONTH: int = Field(default=0, description="TOTAL_PRICE_MONTH")
    MASTER_PRICE_MONTH: int = Field(default=0, description="MASTER_PRICE_MONTH")
    MASTER_Upfront: int = Field(default=0, description="MASTER_Upfront")
    INSTANCE_PRICE_MONTH: int = Field(default=0, description="INSTANCE_PRICE_MONTH")
    HOT_STORAGE_PRICE_MONTH: int = Field(default=0, description="HOT_STORAGE_PRICE_MONTH")
    WARM_STORAGE_PRICE_MONTH: int = Field(default=0, description="WARM_STORAGE_PRICE_MONTH")
    COLD_STORAGE_PRICE_MONTH: int = Field(default=0, description="COLD_STORAGE_PRICE_MONTH")

# class PricingModel(PricingBase):
#     HIS: HotInstanceSizing = Field()
#     WIS: WarmInstanceSizing = Field()
#     MIS: MasterInstanceSizing = Field()
#     CS: ColdStorage = Field()
#     PB: PricingBase = Field()


class ESEC2Instance(BaseModel):
    EC2_INSTANCE_TYPE: str = Field(default="", description="INSTANCE_TYPE")
    EC2_MAX_STORAGE_GP3: int = Field(default=0, description="MAX_STORAGE_GP3")
    EC2_CPU: int = Field(default=0, description="CPU")
    EC2_MEMORY: int = Field(default=0, description="MEMORY")

class ESEC2MasterInstanceSizing(BaseModel):
    EC2_MASTER_TYPE: str = Field(default="", description="EC2_MASTER_TYPE")
    EC2_MASTER_NUM: int = Field(default=0, description="EC2_MASTER_NUM")



class ESEC2InstanceSizing(ESEC2Instance):
    EC2_NUM_BY_STORAGE: int = Field(default=0, description="EC2_NUM_BY_STORAGE")
    EC2_NUM_BY_SHARD_MEMORY: int = Field(default=0, description="EC2_NUM_BY_SHARD_MEMORY")
    EC2_NUM_BY_SHARD_CPU: int = Field(default=0, description="EC2_NUM_BY_SHARD_CPU")
    EC2_NUM_BY_WRITE_THROUGHPUT: int = Field(default=0, description="EC2_NUM_BY_WRITE_THROUGHPUT")
    EC2_NUM_BY_MAX_METRIC: int = Field(default=0, description="EC2_NUM_BY_MAX_METRIC")
    EC2_REQUIRED_HOT_EBS: int = Field(default=0, description="EC2_REQUIRED_HOT_EBS")
    EC2_REQUIRED_HOT_EBS_TOTAL: int = Field(default=0, description="EC2_REQUIRED_HOT_EBS_TOTAL")
    EC2_REQUIRED_WARM_HDD: int = Field(default=0, description="EC2_REQUIRED_WARM_EBS")
    EC2_REQUIRED_WARM_HDD_TOTAL: int = Field(default=0, description="EC2_REQUIRED_WARM_EBS_TOTAL")
    EC2_REQUIRED_EBS_TOTAL : int = Field(default=0, description="EC2_REQUIRED_EBS_TOTAL")
    EC2_NUM: int = Field(default=0, description="EC2_NUM")
    EC2_UNSELECTED: str = Field(default="", description="ec2 unselect reason")

class ESEC2PricingBase(BaseModel):
    EC2_PRICE_MONTH: int = Field(default=0, description="EC2_PRICE_MONTH")
    EC2_Upfront: int = Field(default=0, description="EC2_Upfront")
    TOTAL_PRICE_MONTH: int = Field(default=0, description="TOTAL_PRICE_MONTH")
    MASTER_PRICE_MONTH: int = Field(default=0, description="MASTER_PRICE_MONTH")
    MASTER_EC2_Upfront: int = Field(default=0, description="MASTER_Upfront")
    INSTANCE_PRICE_MONTH: int = Field(default=0, description="MASTER_EC2_Upfront")
    HOT_STORAGE_PRICE_MONTH: int = Field(default=0, description="HOT_STORAGE_PRICE_MONTH")
    WARM_STORAGE_PRICE_MONTH: int = Field(default=0, description="WARM_STORAGE_PRICE_MONTH")
