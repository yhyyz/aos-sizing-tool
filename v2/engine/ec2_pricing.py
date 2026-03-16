import math
import pandas as pd
from v2.engine.base_pricing import BasePricingEngine
from v2.models.instance import HotSizingResult, MasterSizingResult, PricingResult


class EC2PricingEngine(BasePricingEngine):
    def __init__(
        self, pricing_df: pd.DataFrame, region: str, purchase_option: str, term: str
    ):
        super().__init__(pricing_df, region, purchase_option, term)

        ec2_base = self._region_df[
            (self._region_df["Tenancy"] == "Shared")
            & (self._region_df["PricePerUnit"] > 0)
        ]

        if purchase_option == "OD":
            filtered = ec2_base[ec2_base["PurchaseOption"].isna()]
        else:
            filtered = ec2_base[
                (ec2_base["OfferingClass"] == "standard")
                & (ec2_base["PurchaseOption"] == purchase_option)
                & (ec2_base["LeaseContractLength"] == term)
            ]

        self._ec2_index: dict[str, pd.DataFrame] = {
            k: v for k, v in filtered.groupby("Instance Type")
        }

    def _filter_ec2_instance_price(self, instance_type: str) -> pd.DataFrame:
        return self._ec2_index.get(instance_type, pd.DataFrame())

    def calc_pricing(
        self,
        ec2: HotSizingResult,
        master: MasterSizingResult,
        hot_storage: int,
        warm_storage: int,
    ) -> PricingResult:
        result = PricingResult()

        ec2_df = self._filter_ec2_instance_price(ec2.instance_type)
        if ec2_df.empty:
            return result

        ec2_price_per_node, ec2_upfront_per_node = self._calc_instance_price_per_month(
            ec2_df
        )
        ec2_total_monthly = ec2_price_per_node * ec2.node_count
        ec2_total_upfront = ec2_upfront_per_node * ec2.node_count
        result.hot_instance_price_month = round(ec2_total_monthly, 2)
        result.hot_upfront = round(ec2_total_upfront, 2)

        master_monthly = 0.0
        master_upfront_total = 0.0
        if master.node_count == 3:
            master_df = self._filter_ec2_instance_price(master.instance_type)
            master_price, master_upfront = self._calc_instance_price_per_month(
                master_df
            )
            master_monthly = master_price * 3
            master_upfront_total = master_upfront * 3
            result.master_instance_price_month = round(master_monthly, 2)
            result.master_upfront = round(master_upfront_total, 2)

        instance_total = self._calc_total_monthly_with_term(
            ec2_total_monthly + master_monthly,
            ec2_total_upfront + master_upfront_total,
        )
        result.instance_total_price_month = round(instance_total, 2)

        ssd_price_per_gb = self._get_storage_price_per_gb("SSD-backed")
        hot_ebs_per_node = (
            math.ceil(hot_storage / ec2.node_count) if ec2.node_count > 0 else 0
        )
        result.hot_storage_price_month = round(
            hot_ebs_per_node * ssd_price_per_gb * ec2.node_count, 2
        )

        if warm_storage > 0:
            hdd_price_per_gb = self._get_storage_price_per_gb("HDD-backed")
            warm_per_node = (
                math.ceil(warm_storage / ec2.node_count) if ec2.node_count > 0 else 0
            )
            result.warm_storage_price_month = round(
                warm_per_node * hdd_price_per_gb * ec2.node_count, 2
            )

        result.total_price_month = round(
            instance_total
            + result.hot_storage_price_month
            + result.warm_storage_price_month,
            2,
        )

        return result
