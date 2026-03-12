import pandas as pd
import os
import numpy as np

class LoadDataFromExcel:
    def __init__(self):
        self.pricing_df = self.read_aos_pricing()

    @staticmethod
    def read_aos_hot_instance():
        path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        df = pd.read_excel(path + "/excel/AOS_SIZING.xlsx", sheet_name="AOS_HOT_INSTANCE")
        # print(df.to_dict("records"))
        return df

    @staticmethod
    def read_aos_warm_instance():
        path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        df = pd.read_excel(path + "/excel/AOS_SIZING.xlsx", sheet_name="AOS_WARM_INSTANCE")
        print(df.to_dict("records"))
        return df

    @staticmethod
    def read_aos_pricing():
        path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        df = pd.read_excel(path + "/excel/AOS_SIZING_PRICING.xlsx", sheet_name="ALL")
        # print(df.to_dict("records"))
        return df

    @staticmethod
    def read_ec2_pricing():
        path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        df = pd.read_excel(path + "/excel/EC2_SIZING_PRICING.xlsx", sheet_name="ALL")
        # print(df.to_dict("records"))
        return df
    @staticmethod
    def read_ec2_instance():
        path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        df = pd.read_excel(path + "/excel/EC2_SIZING.xlsx", sheet_name="INSTANCE")
        # print(df.to_dict("records"))
        return df


    def get_aws_region_list_from_pricing(self):
        # region_list = self.pricing_df["Region Code"].unique().tolist()
        # region_list.remove("af-south-1") # Africa (Cape Town)
        region_list = self.pricing_df["Location"].unique().tolist()
        region_list.remove("Africa (Cape Town)")  # Africa (Cape Town)
        region_list.sort()
        # region_list.reverse()
        return region_list

    def get_purchase_option_list_from_pricing(self):
        purchase_list = self.pricing_df["PurchaseOption"].unique().tolist()
        purchase_list.remove(np.nan)
        purchase_list.sort()
        return ["OD"] + purchase_list

    def get_term_list_from_pricing(self):
        term_list = self.pricing_df["LeaseContractLength"].unique().tolist()
        term_list.remove(np.nan)
        term_list.sort()
        return ["0yr"] + term_list
