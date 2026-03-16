import pandas as pd
from operator import itemgetter
from v2.engine.aos_sizing import AOSSizingEngine
from v2.engine.aos_pricing import AOSPricingEngine
from v2.models.instance import InstanceSpec, SizingSolutionItem
from v2.models.request import SizingRequest
from v2.config.constants import DEFAULT_COMPRESSION_RATIO
from v2.config.instance_families import is_valid_warm_combination, ServiceType


class AOSSolution:
    def __init__(
        self,
        pricing_df: pd.DataFrame,
        hot_df: pd.DataFrame,
        warm_df: pd.DataFrame,
        req: SizingRequest,
    ):
        self.pricing_df = pricing_df
        self.hot_df = hot_df
        self.warm_df = warm_df
        self.req = req

    def _build_engine(self) -> AOSSizingEngine:
        return AOSSizingEngine(
            daily_data_size=self.req.dailyDataSize,
            hot_days=self.req.hotDays,
            warm_days=self.req.warmDays,
            cold_days=self.req.coldDays,
            replica_num=self.req.replicaNum,
            write_peak=self.req.writePeak,
            az_num=self.req.AZ,
            master_count=self.req.master,
            compression_ratio=self.req.compressionRatio,
            warm_architecture=self.req.warmArchitecture,
            enable_cpu_shard_check=self.req.enableCpuShardCheck,
        )

    def solve(self) -> list:
        engine = self._build_engine()
        pricing_engine = AOSPricingEngine(
            self.pricing_df, self.req.region, self.req.paymentOptions, self.req.RI
        )

        res_list = []
        for _, hrow in self.hot_df.fillna(0).iterrows():
            hot_spec = InstanceSpec(
                instance_type=hrow["INSTANCE_TYPE"],
                max_storage_gp3=int(hrow["MAX_STORAGE_GP3"]),
                cpu=int(hrow["CPU"]),
                memory=int(hrow["MEMORY"]),
            )
            for _, wrow in self.warm_df.fillna(0).iterrows():
                warm_spec = InstanceSpec(
                    instance_type=wrow["INSTANCE_TYPE"],
                    cpu=int(wrow["CPU"]),
                    memory=int(wrow["MEMORY"]),
                    max_storage_gp3=int(wrow["STORAGE"]),
                )

                if not is_valid_warm_combination(
                    hot_spec.instance_type,
                    warm_spec.instance_type,
                    self.req.warmArchitecture,
                    ServiceType.AOS,
                ):
                    continue

                master, hot, warm, cold = engine.calc_full_sizing(hot_spec, warm_spec)

                if hot.unselected_reason or warm.unselected_reason:
                    continue

                hot_s3_storage = engine.calc_hot_s3_storage()

                pricing = pricing_engine.calc_pricing(
                    hot,
                    warm,
                    master,
                    cold,
                    warm_architecture=self.req.warmArchitecture,
                    hot_s3_required_storage=hot_s3_storage,
                )
                if pricing.total_price_month == 0:
                    continue

                item = self._merge_result(
                    hot, warm, master, cold, pricing, hot_s3_storage
                )
                res_list.append(item)

        res_list = sorted(res_list, key=itemgetter("TOTAL_PRICE_MONTH"), reverse=False)
        for i, item in enumerate(res_list):
            item["ROW_ID"] = i

        return res_list

    @staticmethod
    def _merge_result(
        hot, warm, master, cold, pricing, hot_s3_storage: int = 0
    ) -> dict:
        return {
            "ROW_ID": 0,
            "INSTANCE_TYPE": hot.instance_type,
            "MAX_STORAGE_GP3": hot.max_storage_gp3,
            "CPU": hot.cpu,
            "MEMORY": hot.memory,
            "HOT_NUM_BY_STORAGE": hot.num_by_storage,
            "HOT_NUM_BY_SHARD_MEMORY": hot.num_by_shard_memory,
            "HOT_NUM_BY_SHARD_CPU": hot.num_by_shard_cpu,
            "HOT_NUM_BY_WRITE_THROUGHPUT": hot.num_by_write_throughput,
            "HOT_NUM_BY_MAX_METRIC": hot.num_by_max_metric,
            "HOT_REQUIRED_EBS": hot.required_ebs_per_node,
            "HOT_REQUIRED_EBS_TOTAL": hot.required_ebs_total,
            "HOT_NUM": hot.node_count,
            "HOT_UNSELECTED": hot.unselected_reason,
            "WARM_INSTANCE_TYPE": warm.instance_type,
            "WARM_CPU": warm.cpu,
            "WARM_MEMORY": warm.memory,
            "STORAGE": warm.storage_per_node,
            "WARM_NUM_BY_STORAGE": warm.num_by_storage,
            "WARM_NUM_BY_MAX_METRIC": warm.num_by_max_metric,
            "WARM_REQUIRED_STORAGE": warm.required_storage_per_node,
            "WARM_REQUIRED_STORAGE_TOTAL": warm.required_storage_total,
            "WARM_NUM": warm.node_count,
            "WARM_UNSELECTED": warm.unselected_reason,
            "COLD_REQUIRED_STORAGE": cold.required_storage,
            "DEDICATED_MASTER_TYPE": master.instance_type,
            "MASTER_NUM": master.node_count,
            "HOT_PRICE_MONTH": pricing.hot_instance_price_month,
            "Upfront": pricing.hot_upfront,
            "WARM_PRICE_MONTH": pricing.warm_instance_price_month,
            "TOTAL_PRICE_MONTH": pricing.total_price_month,
            "MASTER_PRICE_MONTH": pricing.master_instance_price_month,
            "MASTER_Upfront": pricing.master_upfront,
            "INSTANCE_PRICE_MONTH": pricing.instance_total_price_month,
            "HOT_STORAGE_PRICE_MONTH": pricing.hot_storage_price_month,
            "HOT_S3_STORAGE": hot_s3_storage,
            "HOT_S3_STORAGE_PRICE_MONTH": pricing.hot_s3_storage_price_month,
            "WARM_STORAGE_PRICE_MONTH": pricing.warm_storage_price_month,
            "COLD_STORAGE_PRICE_MONTH": pricing.cold_storage_price_month,
        }
