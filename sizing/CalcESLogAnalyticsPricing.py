from model.LogAnalytics import LogAnalyticsRequest
import pandas as pd
from model.Instance import ESEC2InstanceSizing, ESEC2MasterInstanceSizing,PricingBase,ESEC2PricingBase


class CalcESEC2LogAnalyticsPricing:
    def __init__(self, lr: LogAnalyticsRequest, eeis: ESEC2InstanceSizing, emis:ESEC2MasterInstanceSizing,ec2_pricing_data:pd.DataFrame):
        self.lr = lr
        self.eeis = eeis
        self.emis = emis
        self.ec2_pricing_data = ec2_pricing_data
        self.aws_region = lr.region
        self.purchase_option = lr.paymentOptions
        self.term = lr.RI

    def calc_es_ec2_pricing(self):
        pdf = self.ec2_pricing_data
        ec2_instance_type = self.eeis.EC2_INSTANCE_TYPE
        ec2_num = self.eeis.EC2_NUM
        epb = ESEC2PricingBase()

        if self.purchase_option == "OD":
            ec2_filter_df = pdf[(pdf['Location'] == self.aws_region) & (pdf['Instance Type'] == ec2_instance_type)
                                & (pdf['PurchaseOption'].isna()) & (pdf['Tenancy'] == "Shared") & (pdf['PricePerUnit'] > 0) ]
        else:
            ec2_filter_df = pdf[(pdf['Location'] == self.aws_region) & (pdf['Instance Type'] == ec2_instance_type)  & (pdf['OfferingClass'] == "standard")
                                & (pdf['PurchaseOption'] == self.purchase_option) & (pdf['LeaseContractLength'] == self.term) & (pdf['Tenancy'] == "Shared") & (
                                                pdf['PricePerUnit'] > 0)]
        if ec2_filter_df.empty:
           return epb
        # currency = "".join(hot_filter_df["Currency"].unique().tolist())
        # if currency == "CNY":
        #     currency_format = "￥"
        # elif currency == "USD":
        #     currency_format = "$"
        num_month = 12
        ec2_instance_price_month, ec2_upfront = self._calc_instance_price_per_month(ec2_filter_df, self.purchase_option)
        ec2_instance_total_price_month = ec2_instance_price_month * ec2_num
        ec2_total_upfront = ec2_upfront * ec2_num

        epb.EC2_PRICE_MONTH = round(ec2_instance_total_price_month, 2)
        epb.EC2_Upfront = round(ec2_total_upfront, 2)

        master_total_price_month = 0
        master_total_upfront = 0
        dedicated_master_type = ""
        if self.emis.EC2_MASTER_NUM == 3:
            # DEDICATED_MASTER
            dedicated_master_type = self.emis.EC2_MASTER_TYPE
            if self.purchase_option == "OD":
                dedicated_filter_df = pdf[(pdf['Location'] == self.aws_region) & (pdf['Instance Type'] == ec2_instance_type)
                                    & (pdf['PurchaseOption'].isna()) & (pdf['Tenancy'] == "Shared") & (
                                                pdf['PricePerUnit'] > 0)]
            else:
                dedicated_filter_df = pdf[
                    (pdf['Location'] == self.aws_region) & (pdf['Instance Type'] == dedicated_master_type) & (pdf['OfferingClass'] == "standard")
                    & (pdf['PurchaseOption'] == self.purchase_option) & (pdf['LeaseContractLength'] == self.term) & (pdf['Tenancy'] == "Shared") & (
                                                pdf['PricePerUnit'] > 0) ]
            if dedicated_filter_df.empty:
                epb.MASTER_PRICE_MONTH = 0
            master_price_month, master_upfront = self._calc_instance_price_per_month(dedicated_filter_df,
                                                                                 self.purchase_option)
            master_total_price_month = master_price_month * 3
            master_total_upfront = master_upfront * 3

        total_price_month = 0
        if self.term == "1yr":
            total_price_month = (
                                        master_total_price_month * 12 + master_total_upfront + ec2_instance_total_price_month * 12 + ec2_total_upfront) / 12
        elif self.term == "3yr":
            total_price_month = (
                                        master_total_price_month * 36 + master_total_upfront + ec2_instance_total_price_month * 36 + ec2_total_upfront) / 36
        elif self.term == "0yr":
            total_price_month = (
                                        master_total_price_month + master_total_upfront + ec2_instance_total_price_month + ec2_total_upfront)

        # storage price GP3 Managed-Storage
        gp3_df = pdf[(pdf['Location'] == self.aws_region) & (pdf['Storage Media'] == "SSD-backed")]
        ec2_hot_price_month_per_gb = 0
        for index, row in gp3_df.iterrows():
            ec2_hot_price_month_per_gb = row["PricePerUnit"]
        ec2_hot_storage_price = self.eeis.EC2_REQUIRED_HOT_EBS * ec2_hot_price_month_per_gb * ec2_num

        ec2_warm_storage_price = 0
        if self.eeis.EC2_REQUIRED_WARM_HDD!=0:
            hdd_df = pdf[(pdf['Location'] == self.aws_region) & (pdf['Storage Media'] == "HDD-backed")]
            ec2_warm_price_month_per_gb = 0
            for index, row in hdd_df.iterrows():
                ec2_warm_price_month_per_gb = row["PricePerUnit"]
            ec2_warm_storage_price = self.eeis.EC2_REQUIRED_WARM_HDD * ec2_warm_price_month_per_gb * ec2_num

        total_price_month_instance_and_storage = total_price_month + ec2_hot_storage_price + ec2_warm_storage_price
        epb.TOTAL_PRICE_MONTH = round(total_price_month_instance_and_storage, 2)

        if dedicated_master_type:
            # epb.MASTER_PRICE_MONTH = round(
            #     master_total_price_month + master_total_upfront, 2)
            epb.MASTER_PRICE_MONTH = epb.MASTER_PRICE_MONTH = round(
                master_total_price_month, 2)
            epb.MASTER_EC2_Upfront = round(master_total_upfront, 2)
        epb.INSTANCE_PRICE_MONTH = round(total_price_month, 2)
        epb.HOT_STORAGE_PRICE_MONTH = round(ec2_hot_storage_price, 2)
        epb.WARM_STORAGE_PRICE_MONTH = round(ec2_warm_storage_price, 2)
        return epb


    def _calc_instance_price_per_month(self, filter_df, purchase_option):
        price_month = 0
        upfront = 0
        num_month = 12
        filter_df = filter_df
        if purchase_option == "No Upfront":
            price_hrs = 0
            for index, row in filter_df.iterrows():
                price_hrs = row["PricePerUnit"]
            price_month = (price_hrs * 24 * 365) / num_month
        elif purchase_option == "Partial Upfront":
            quantity = 0
            price_hrs = 0
            for index, row in filter_df.iterrows():
                if row["Unit"] == "Quantity":
                    quantity = row["PricePerUnit"]
                if row["Unit"] == "Hrs":
                    price_hrs = row["PricePerUnit"]
            price_month = (price_hrs * 24 * 365) / num_month
            upfront = quantity
        elif purchase_option == "All Upfront":
            quantity = 0
            for index, row in filter_df.iterrows():
                if row["Unit"] == "Quantity":
                    quantity = row["PricePerUnit"]
            price_month = 0
            upfront = quantity
        elif purchase_option == "OD":
            price_hrs = 0
            for index, row in filter_df.iterrows():
                price_hrs = row["PricePerUnit"]
            price_month = (price_hrs * 24 * 365) / num_month
        return price_month, upfront

    def calc_es_ec2_pricing_with_sizing(self):
        epb = self.calc_es_ec2_pricing()
        epb_dict = epb.dict()
        emis_dict = self.emis.dict()
        eeis_dict = self.eeis.dict()
        merge_dict = {**epb_dict, **emis_dict, **eeis_dict}
        return merge_dict

