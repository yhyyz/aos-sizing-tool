from sizing.CalcESLogAnalyticsSizing import CalcESEC2LogAnalyticsSizing
from sizing.CalcESLogAnalyticsPricing import CalcESEC2LogAnalyticsPricing
from model.LogAnalytics import EC2LogAnalyticsRequest
from model.Instance import ESEC2Instance
from operator import itemgetter


class ESEC2LogAnalyticsSolution(object):
    def __init__(self, ec2_pricing_df, ec2_df, elr: EC2LogAnalyticsRequest):
        self.ec2_pricing_df = ec2_pricing_df
        self.ec2_df = ec2_df
        self.elr = elr
        self.celas = CalcESEC2LogAnalyticsSizing(self.elr)

    def solution(self):
        ec2df = self.ec2_df
        # res_list = []
        eei = ESEC2Instance()
        req_ec2_instance_type = self.elr.reqEC2Instance
        ec2_instance_type = req_ec2_instance_type.replace(".search","")
        for index, hrow in ec2df.fillna(0).iterrows():
            if hrow['INSTANCE_TYPE'] == ec2_instance_type:
                eei.EC2_INSTANCE_TYPE = ec2_instance_type
                eei.EC2_CPU = int(hrow["CPU"])
                eei.EC2_MAX_STORAGE_GP3 = int(hrow["MAX_STORAGE_GP3"])
                eei.EC2_MEMORY = int(hrow["MEMORY"])
                break
        master, eis = self.celas.calc_ec2_sizing_with_limit(eei)
        merge_dict = CalcESEC2LogAnalyticsPricing(self.elr,eis,master,self.ec2_pricing_df).calc_es_ec2_pricing_with_sizing()
        # res_list.append(merge_dict)
        return merge_dict
        # res_list = sorted(res_list, key=itemgetter('TOTAL_PRICE_MONTH'), reverse=False)
        # for i, item in enumerate(res_list):
        #     res_list[i]["ROW_ID"] = i
        # return res_list


