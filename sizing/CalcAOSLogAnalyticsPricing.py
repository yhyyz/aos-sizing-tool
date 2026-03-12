from model.LogAnalytics import LogAnalyticsRequest
import pandas as pd
from model.Instance import HotInstanceSizing, WarmInstanceSizing, MasterInstanceSizing, PricingBase,ColdStorage


class CalcAOSLogAnalyticsPricing:
    def __init__(self, lr:LogAnalyticsRequest, his: HotInstanceSizing, wis: WarmInstanceSizing, mis: MasterInstanceSizing,cs:ColdStorage,aos_pricing_data:pd.DataFrame):
        self.lr = lr
        self.his = his
        self.wis = wis
        self.mis = mis
        self.aos_pricing_data = aos_pricing_data
        self.aws_region = lr.region
        self.purchase_option = lr.paymentOptions
        self.term = lr.RI
        self.cs = cs

    def calc_pricing(self):
        pdf = self.aos_pricing_data
        hot_instance_type = self.his.INSTANCE_TYPE
        hot_num = self.his.HOT_NUM
        pb = PricingBase()

        if self.purchase_option == "OD":
            hot_filter_df = pdf[(pdf['Location'] == self.aws_region) & (pdf['Instance Type'] == hot_instance_type)
                                & (pdf['PurchaseOption'].isna())]
        else:
            hot_filter_df = pdf[(pdf['Location'] == self.aws_region) & (pdf['Instance Type'] == hot_instance_type)
                                & (pdf['PurchaseOption'] == self.purchase_option) & (pdf['LeaseContractLength'] == self.term)]
        if hot_filter_df.empty:
           return pb
        # currency = "".join(hot_filter_df["Currency"].unique().tolist())
        # if currency == "CNY":
        #     currency_format = "￥"
        # elif currency == "USD":
        #     currency_format = "$"
        num_month = 12

        hot_instance_price_month, hot_upfront = self._calc_instance_price_per_month(hot_filter_df, self.purchase_option)
        hot_instance_total_price_month = hot_instance_price_month * hot_num
        hot_total_upfront = hot_upfront * hot_num

        pb.HOT_PRICE_MONTH = round(hot_instance_total_price_month, 2)
        pb.Upfront = round(hot_total_upfront, 2)

        warm_total_month = 0
        warm_storage_price = 0
        cold_storage_price = 0
        if self.wis.WARM_NUM!=0:
            warm_instance_type =  self.wis.WARM_INSTANCE_TYPE
            warm_num = self.wis.WARM_NUM
            warm_filter_df = pdf[(pdf['Location'] == self.aws_region) & (pdf['Instance Type'] == warm_instance_type)]
            warm_price_hrs = 0
            for index, row in warm_filter_df.iterrows():
                warm_price_hrs = row["PricePerUnit"]
            warm_price_month = (warm_price_hrs * 24 * 365) / num_month
            warm_total_month = warm_price_month * warm_num
            pb.WARM_PRICE_MONTH= round(warm_total_month, 2)

            warm_price_month_per_gb = 0
            managed_storage_df = pdf[(pdf['Location'] == self.aws_region) & (pdf['Storage Media'] == "Managed-Storage")]
            for index, row in managed_storage_df.iterrows():
                warm_price_month_per_gb = row["PricePerUnit"]
            warm_storage_price = self.wis.WARM_REQUIRED_STORAGE * warm_price_month_per_gb * warm_num

            cold_storage_price = self.cs.COLD_REQUIRED_STORAGE * warm_price_month_per_gb
            pb.WARM_STORAGE_PRICE_MONTH = warm_storage_price
            pb.COLD_STORAGE_PRICE_MONTH = warm_storage_price

        master_total_price_month = 0
        master_total_upfront = 0
        dedicated_master_type = ""
        if self.mis.MASTER_NUM == 3:
            # DEDICATED_MASTER
            dedicated_master_type = self.mis.DEDICATED_MASTER_TYPE
            if self.purchase_option == "OD":
                dedicated_filter_df = pdf[
                    (pdf['Location'] == self.aws_region) & (pdf['Instance Type'] == dedicated_master_type)
                    & (pdf['PurchaseOption'].isna())]
            else:
                dedicated_filter_df = pdf[
                    (pdf['Location'] == self.aws_region) & (pdf['Instance Type'] == dedicated_master_type)
                    & (pdf['PurchaseOption'] == self.purchase_option) & (pdf['LeaseContractLength'] == self.term)]
            if dedicated_filter_df.empty:
                pb.MASTER_PRICE_MONTH = 0
            master_price_month, master_upfront = self._calc_instance_price_per_month(dedicated_filter_df,
                                                                                 self.purchase_option)
            master_total_price_month = master_price_month * 3
            master_total_upfront = master_upfront * 3

        total_price_month = 0
        if self.term == "1yr":
            total_price_month = (
                                        master_total_price_month * 12 + master_total_upfront + hot_instance_total_price_month * 12 + hot_total_upfront) / 12 + warm_total_month
        elif self.term == "3yr":
            total_price_month = (
                                        master_total_price_month * 36 + master_total_upfront + hot_instance_total_price_month * 36 + hot_total_upfront) / 36 + warm_total_month
        elif self.term == "0yr":
            total_price_month = (
                                        master_total_price_month + master_total_upfront + hot_instance_total_price_month + hot_total_upfront) + warm_total_month

        # storage price GP3 Managed-Storage
        gp3_df = pdf[(pdf['Location'] == self.aws_region) & (pdf['Storage Media'] == "GP3")]
        hot_price_month_per_gb = 0
        for index, row in gp3_df.iterrows():
            hot_price_month_per_gb = row["PricePerUnit"]
        hot_storage_price = self.his.HOT_REQUIRED_EBS * hot_price_month_per_gb * hot_num

        total_price_month_instance_and_storage = total_price_month + hot_storage_price + warm_storage_price + cold_storage_price
        pb.TOTAL_PRICE_MONTH = round(total_price_month_instance_and_storage, 2)

        if dedicated_master_type:
            pb.MASTER_PRICE_MONTH = round(
                master_total_price_month, 2)
            pb.MASTER_Upfront = round(master_total_upfront,2)
        pb.INSTANCE_PRICE_MONTH = round(total_price_month, 2)
        pb.HOT_STORAGE_PRICE_MONTH = round(hot_storage_price, 2)

        if self.wis.WARM_NUM != 0:
            pb.WARM_STORAGE_PRICE_MONTH = round(warm_storage_price, 2)
            pb.COLD_STORAGE_PRICE_MONTH = round(cold_storage_price, 2)
        return pb


    def _calc_instance_price_per_month(self, hot_filter_df, purchase_option):
        hot_price_month = 0
        upfront = 0
        num_month = 12
        if purchase_option == "No Upfront":
            price_hrs = 0
            for index, row in hot_filter_df.iterrows():
                price_hrs = row["PricePerUnit"]
            hot_price_month = (price_hrs * 24 * 365) / num_month
        elif purchase_option == "Partial Upfront":
            quantity = 0
            price_hrs = 0
            for index, row in hot_filter_df.iterrows():
                if row["Unit"] == "Quantity":
                    quantity = row["PricePerUnit"]
                if row["Unit"] == "Hrs":
                    price_hrs = row["PricePerUnit"]
            hot_price_month = (price_hrs * 24 * 365) / num_month
            upfront = quantity
        elif purchase_option == "All Upfront":
            quantity = 0
            for index, row in hot_filter_df.iterrows():
                if row["Unit"] == "Quantity":
                    quantity = row["PricePerUnit"]
            hot_price_month = 0
            upfront = quantity
        elif purchase_option == "OD":
            price_hrs = 0
            for index, row in hot_filter_df.iterrows():
                price_hrs = row["PricePerUnit"]
            hot_price_month = (price_hrs * 24 * 365) / num_month
        return hot_price_month, upfront

    def calc_pricing_with_sizing(self):
        pb = self.calc_pricing()
        pb_dict = pb.dict()
        mis_dict = self.mis.dict()
        his_dict = self.his.dict()
        wis_dict = self.wis.dict()
        cs_dict = self.cs.dict()
        merge_dict = {**pb_dict, **mis_dict, **his_dict, **wis_dict,**cs_dict}
        return merge_dict

