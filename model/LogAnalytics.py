from typing import Optional, List

from pydantic import BaseModel, Field, validator


class Base(BaseModel):
    page: int = Field(default=0, description="page")
    pageSize: int = Field(default=0, description="pageSize")


class LogAnalyticsRequest(Base):
    sourceDataSize: int = Field(default=0, description="dailyDataSize")
    dailyDataSize: int = Field(default=0, description="dailyDataSize")
    hotDays: int = Field(default=0, description="hotDays")
    warmDays: int = Field(default=0, description="warmDays")
    coldDays: int = Field(default=0, description="coldDays")
    replicaNum: int = Field(default=0, description="replicaNum")
    writePeak: int = Field(default=0, description="writePeak")
    AZ: int = Field(default=0, description="AZ")
    region: str = Field(default="US East (N. Virginia)", description="region")
    RI: str = Field(default="0yr", description="RI")
    paymentOptions: str = Field(default="OD", description="paymentOptions")
    master: int = Field(default=0, description="master")
    filterData:str = Field(default="", description="filterData")


class EC2LogAnalyticsRequest(LogAnalyticsRequest):
    reqEC2Instance: str = Field(default="", description="REQ_EC2_INSTANCE_TYPE")
    # REQ_EC2_MASTER_TYPE: str = Field(default="", description="REQ_EC2_MASTER_TYPE")
