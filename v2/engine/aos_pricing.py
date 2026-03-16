import pandas as pd
from v2.engine.base_pricing import BasePricingEngine
from v2.config.instance_families import (
    ServiceType,
    get_family_for_instance,
)
from v2.models.instance import (
    HotSizingResult,
    WarmSizingResult,
    MasterSizingResult,
    ColdStorageResult,
    PricingResult,
)


class AOSPricingEngine(BasePricingEngine):
    def calc_pricing(
        self,
        hot: HotSizingResult,
        warm: WarmSizingResult,
        master: MasterSizingResult,
        cold: ColdStorageResult,
        warm_architecture: str = "ultrawarm",
        hot_s3_required_storage: int = 0,
    ) -> PricingResult:
        result = PricingResult()

        hot_df = self._filter_instance_price(hot.instance_type)
        if hot_df.empty:
            return result

        hot_price_per_node, hot_upfront_per_node = self._calc_instance_price_per_month(
            hot_df
        )
        result.hot_instance_price_month = round(hot_price_per_node * hot.node_count, 2)
        result.hot_upfront = round(hot_upfront_per_node * hot.node_count, 2)

        managed_storage_price_per_gb = self._get_storage_price_per_gb("Managed-Storage")

        if warm.node_count > 0:
            warm_df = self._filter_instance_price(warm.instance_type)
            if not warm_df.empty:
                warm_price_per_node, _ = self._calc_instance_price_per_month(warm_df)
            else:
                warm_df = self._filter_instance_price(
                    warm.instance_type,
                    extra_filters={"PurchaseOption": pd.NA},
                )
                warm_price_per_node, _ = self._calc_instance_price_per_month(warm_df)
            result.warm_instance_price_month = round(
                warm_price_per_node * warm.node_count, 2
            )

            if warm_architecture == "multi_tier":
                result.warm_storage_price_month = round(
                    warm.required_storage_total * managed_storage_price_per_gb, 2
                )
                result.cold_storage_price_month = 0
            else:
                result.warm_storage_price_month = round(
                    warm.required_storage_per_node
                    * managed_storage_price_per_gb
                    * warm.node_count,
                    2,
                )
                result.cold_storage_price_month = round(
                    cold.required_storage * managed_storage_price_per_gb, 2
                )

        master_monthly = 0.0
        master_upfront_total = 0.0
        if master.node_count == 3:
            master_df = self._filter_instance_price(master.instance_type)
            master_price, master_upfront = self._calc_instance_price_per_month(
                master_df
            )
            master_monthly = master_price * 3
            master_upfront_total = master_upfront * 3
            result.master_instance_price_month = round(master_monthly, 2)
            result.master_upfront = round(master_upfront_total, 2)

        instance_total = (
            self._calc_total_monthly_with_term(
                result.hot_instance_price_month + master_monthly,
                result.hot_upfront + master_upfront_total,
            )
            + result.warm_instance_price_month
        )

        result.instance_total_price_month = round(instance_total, 2)

        hot_family = get_family_for_instance(hot.instance_type, ServiceType.AOS)
        if hot_family is not None and not hot_family.needs_ebs_config:
            result.hot_storage_price_month = 0
        else:
            gp3_price_per_gb = self._get_storage_price_per_gb("GP3")
            result.hot_storage_price_month = round(
                hot.required_ebs_per_node * gp3_price_per_gb * hot.node_count, 2
            )

        if (
            hot_family is not None
            and hot_family.is_optimized
            and hot_s3_required_storage > 0
        ):
            result.hot_s3_storage_price_month = round(
                hot_s3_required_storage * managed_storage_price_per_gb, 2
            )

        result.total_price_month = round(
            instance_total
            + result.hot_storage_price_month
            + result.hot_s3_storage_price_month
            + result.warm_storage_price_month
            + result.cold_storage_price_month,
            2,
        )

        return result
