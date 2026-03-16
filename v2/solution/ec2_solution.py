import math
import pandas as pd
from v2.engine.ec2_sizing import EC2SizingEngine
from v2.engine.ec2_pricing import EC2PricingEngine
from v2.models.instance import InstanceSpec
from v2.models.request import EC2SizingRequest
from v2.config.constants import DEFAULT_COMPRESSION_RATIO


class EC2Solution:
    def __init__(
        self,
        ec2_pricing_df: pd.DataFrame,
        ec2_instance_df: pd.DataFrame,
        req: EC2SizingRequest,
    ):
        self.ec2_pricing_df = ec2_pricing_df
        self.ec2_instance_df = ec2_instance_df
        self.req = req

    def solve(self) -> dict:
        req = self.req
        ec2_instance_type = req.reqEC2Instance.replace(".search", "")

        spec = InstanceSpec()
        for _, row in self.ec2_instance_df.fillna(0).iterrows():
            if row["INSTANCE_TYPE"] == ec2_instance_type:
                spec.instance_type = ec2_instance_type
                spec.cpu = int(row["CPU"])
                spec.max_storage_gp3 = int(row["MAX_STORAGE_GP3"])
                spec.memory = int(row["MEMORY"])
                break

        engine = EC2SizingEngine(
            daily_data_size=req.dailyDataSize,
            hot_days=req.hotDays,
            warm_days=req.warmDays,
            cold_days=req.coldDays,
            replica_num=req.replicaNum,
            write_peak=req.writePeak,
            az_num=req.AZ,
            master_count=req.master,
            compression_ratio=req.compressionRatio,
            enable_cpu_shard_check=req.enableCpuShardCheck,
        )

        master, ec2_sizing, hot_storage, warm_storage = engine.calc_full_sizing(spec)

        pricing_engine = EC2PricingEngine(
            self.ec2_pricing_df, req.region, req.paymentOptions, req.RI
        )
        pricing = pricing_engine.calc_pricing(
            ec2_sizing, master, hot_storage, warm_storage
        )

        warm_per_node = (
            math.ceil(warm_storage / ec2_sizing.node_count)
            if ec2_sizing.node_count > 0
            else 0
        )

        return {
            "EC2_INSTANCE_TYPE": ec2_sizing.instance_type,
            "EC2_MAX_STORAGE_GP3": ec2_sizing.max_storage_gp3,
            "EC2_CPU": ec2_sizing.cpu,
            "EC2_MEMORY": ec2_sizing.memory,
            "EC2_NUM_BY_STORAGE": ec2_sizing.num_by_storage,
            "EC2_NUM_BY_SHARD_MEMORY": ec2_sizing.num_by_shard_memory,
            "EC2_NUM_BY_SHARD_CPU": ec2_sizing.num_by_shard_cpu,
            "EC2_NUM_BY_WRITE_THROUGHPUT": ec2_sizing.num_by_write_throughput,
            "EC2_NUM_BY_MAX_METRIC": ec2_sizing.num_by_max_metric,
            "EC2_REQUIRED_HOT_EBS": ec2_sizing.required_ebs_per_node,
            "EC2_REQUIRED_HOT_EBS_TOTAL": ec2_sizing.required_ebs_total,
            "EC2_REQUIRED_WARM_HDD": warm_per_node,
            "EC2_REQUIRED_WARM_HDD_TOTAL": math.ceil(warm_storage),
            "EC2_REQUIRED_EBS_TOTAL": math.ceil(hot_storage + warm_storage),
            "EC2_NUM": ec2_sizing.node_count,
            "EC2_UNSELECTED": ec2_sizing.unselected_reason,
            "EC2_MASTER_TYPE": master.instance_type,
            "EC2_MASTER_NUM": master.node_count,
            "EC2_PRICE_MONTH": pricing.hot_instance_price_month,
            "EC2_Upfront": pricing.hot_upfront,
            "TOTAL_PRICE_MONTH": pricing.total_price_month,
            "MASTER_PRICE_MONTH": pricing.master_instance_price_month,
            "MASTER_EC2_Upfront": pricing.master_upfront,
            "INSTANCE_PRICE_MONTH": pricing.instance_total_price_month,
            "HOT_STORAGE_PRICE_MONTH": pricing.hot_storage_price_month,
            "WARM_STORAGE_PRICE_MONTH": pricing.warm_storage_price_month,
        }
