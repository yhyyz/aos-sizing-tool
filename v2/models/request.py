from typing import Optional
from pydantic import BaseModel, Field


class SizingRequest(BaseModel):
    dailyDataSize: float = Field(default=0, description="Daily ingestion size (GB)")
    hotDays: int = Field(default=0, description="Hot tier retention days")
    warmDays: int = Field(default=0, description="Warm tier retention days")
    coldDays: int = Field(default=0, description="Cold tier retention days")
    replicaNum: int = Field(default=0, description="Number of replicas")
    writePeak: float = Field(default=0, description="Peak write throughput (MB/s)")
    AZ: int = Field(default=2, description="Number of availability zones (1/2/3)")
    region: str = Field(default="US East (N. Virginia)")
    RI: str = Field(
        default="0yr", description="Reserved instance term: 0yr / 1yr / 3yr"
    )
    paymentOptions: str = Field(
        default="OD", description="OD / No Upfront / Partial Upfront / All Upfront"
    )
    master: int = Field(default=3, description="Dedicated master count (0 or 3)")
    compressionRatio: float = Field(
        default=0.4, description="Compression ratio (indexed / raw)"
    )

    warmArchitecture: str = Field(
        default="ultrawarm",
        description="Warm architecture: 'ultrawarm' (UltraWarm+Cold) or 'multi_tier' (OI2 warm, no cold, OpenSearch 3.3+)",
    )

    enableCpuShardCheck: bool = Field(
        default=False,
        description="Enable CPU-to-shard ratio check (1.5 vCPU per active shard). Conservative, disabled by default.",
    )

    filterData: str = Field(
        default="", description="Filter: hotFamily-hotSize-warmSize"
    )
    pageSize: int = Field(default=1000)
    page: int = Field(default=1)


class EC2SizingRequest(SizingRequest):
    reqEC2Instance: str = Field(
        default="", description="Requested EC2 instance type (e.g. r7g.medium.search)"
    )


class LegacyLogAnalyticsRequest(BaseModel):
    """兼容旧 API 的请求模型"""

    sourceDataSize: int = Field(default=0)
    dailyDataSize: int = Field(default=0)
    hotDays: int = Field(default=0)
    warmDays: int = Field(default=0)
    coldDays: int = Field(default=0)
    replicaNum: int = Field(default=0)
    writePeak: int = Field(default=0)
    AZ: int = Field(default=0)
    region: str = Field(default="US East (N. Virginia)")
    RI: str = Field(default="0yr")
    paymentOptions: str = Field(default="OD")
    master: int = Field(default=0)
    filterData: str = Field(default="")
    page: int = Field(default=0)
    pageSize: int = Field(default=0)


class LegacyEC2LogAnalyticsRequest(LegacyLogAnalyticsRequest):
    reqEC2Instance: str = Field(default="")
