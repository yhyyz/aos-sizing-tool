import pandas as pd
from typing import Optional


HOURS_PER_MONTH = 24 * 365 / 12


class BasePricingEngine:
    def __init__(
        self, pricing_df: pd.DataFrame, region: str, purchase_option: str, term: str
    ):
        self.region = region
        self.purchase_option = purchase_option
        self.term = term

        region_df = pricing_df[pricing_df["Location"] == region]

        if purchase_option == "OD":
            base = region_df[region_df["PurchaseOption"].isna()]
        else:
            base = region_df[
                (region_df["PurchaseOption"] == purchase_option)
                & (region_df["LeaseContractLength"] == term)
            ]
        self._price_index: dict[str, pd.DataFrame] = {
            k: v for k, v in base.groupby("Instance Type")
        }

        if purchase_option != "OD":
            od_base = region_df[region_df["PurchaseOption"].isna()]
            self._od_index: dict[str, pd.DataFrame] = {
                k: v for k, v in od_base.groupby("Instance Type")
            }
        else:
            self._od_index = self._price_index

        self._storage_cache: dict[str, float] = {}
        mask = region_df["Storage Media"].notna()
        if mask.any():
            for media, grp in region_df[mask].groupby("Storage Media"):
                self._storage_cache[str(media)] = float(grp.iloc[0]["PricePerUnit"])

        self._region_df = region_df

    def _filter_instance_price(
        self, instance_type: str, extra_filters: Optional[dict] = None
    ) -> pd.DataFrame:
        if extra_filters and "PurchaseOption" in extra_filters:
            return self._od_index.get(instance_type, pd.DataFrame())
        return self._price_index.get(instance_type, pd.DataFrame())

    def _calc_instance_price_per_month(self, filter_df: pd.DataFrame) -> tuple:
        price_month = 0.0
        upfront = 0.0

        if filter_df.empty:
            return price_month, upfront

        if self.purchase_option == "No Upfront":
            if not filter_df.empty:
                price_month = float(filter_df.iloc[0]["PricePerUnit"]) * HOURS_PER_MONTH
        elif self.purchase_option == "Partial Upfront":
            qty_rows = filter_df[filter_df["Unit"] == "Quantity"]
            hrs_rows = filter_df[filter_df["Unit"] == "Hrs"]
            if not qty_rows.empty:
                upfront = float(qty_rows.iloc[0]["PricePerUnit"])
            if not hrs_rows.empty:
                price_month = float(hrs_rows.iloc[0]["PricePerUnit"]) * HOURS_PER_MONTH
        elif self.purchase_option == "All Upfront":
            qty_rows = filter_df[filter_df["Unit"] == "Quantity"]
            if not qty_rows.empty:
                upfront = float(qty_rows.iloc[0]["PricePerUnit"])
        elif self.purchase_option == "OD":
            if not filter_df.empty:
                price_month = float(filter_df.iloc[0]["PricePerUnit"]) * HOURS_PER_MONTH

        return price_month, upfront

    def _get_storage_price_per_gb(self, storage_media: str) -> float:
        return self._storage_cache.get(storage_media, 0.0)

    def _calc_total_monthly_with_term(self, monthly: float, upfront: float) -> float:
        """将 upfront 分摊到月费中"""
        if self.term == "1yr":
            return (monthly * 12 + upfront) / 12
        elif self.term == "3yr":
            return (monthly * 36 + upfront) / 36
        return monthly + upfront
