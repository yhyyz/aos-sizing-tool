from sizing.CalcAOSLogAnalyticsSizing import CalcAOSLogAnalyticsSizing
from sizing.CalcAOSLogAnalyticsPricing import CalcAOSLogAnalyticsPricing
from model.LogAnalytics import LogAnalyticsRequest
from model.Instance import HotInstance, WarmInstance
from operator import itemgetter


class AOSLogAnalyticsSolution(object):
    def __init__(self, pricing_df, hot_df, warm_df, lr: LogAnalyticsRequest):
        self.pricing_df = pricing_df
        self.hot_df = hot_df
        self.warm_df = warm_df
        self.lr = lr
        self.clas = CalcAOSLogAnalyticsSizing(self.lr)
        self.prefixes =['c6', 'm6', 'r6']
        self.count = 3

    def filter_elements(self, input_list):
        result = []
        for prefix in self.prefixes:
            filtered_elements = [element for element in input_list if element["INSTANCE_TYPE"].startswith(prefix)]
            result.extend(filtered_elements[:self.count])
        return result

    def solution(self):
        res_list = []
        for index, hrow in self.hot_df.fillna(0).iterrows():
            hi = HotInstance()
            hi.INSTANCE_TYPE = hrow['INSTANCE_TYPE']
            hi.MAX_STORAGE_GP3 = int(hrow["MAX_STORAGE_GP3"])
            hi.CPU = int(hrow["CPU"])
            hi.MEMORY = int(hrow["MEMORY"])
            for wix, wrow in self.warm_df.fillna(0).iterrows():
                wi = WarmInstance()
                wi.WARM_INSTANCE_TYPE = wrow['INSTANCE_TYPE']
                wi.WARM_CPU = int(wrow["CPU"])
                wi.WARM_MEMORY = int(wrow["MEMORY"])
                wi.STORAGE = int(wrow["STORAGE"])
                master, his, wis, cs = self.clas.calc_sizing_with_limit(hi, wi)
                if len(his.HOT_UNSELECTED) != 0 or len(wis.WARM_UNSELECTED) != 0:
                    continue
                merge_dict = CalcAOSLogAnalyticsPricing(self.lr, his, wis, master, cs, self.pricing_df).calc_pricing_with_sizing()
                if merge_dict["TOTAL_PRICE_MONTH"] != 0:
                    res_list.append(merge_dict)
        res_list = sorted(res_list, key=itemgetter('TOTAL_PRICE_MONTH'), reverse=False)
        filter_res_list = res_list
        # filter_res_list = self.filter_elements(res_list)
        # filter_res_list = sorted(filter_res_list, key=itemgetter('TOTAL_PRICE_MONTH'), reverse=False)
        for i, item in enumerate(filter_res_list):
            filter_res_list[i]["ROW_ID"] = i
        return filter_res_list

