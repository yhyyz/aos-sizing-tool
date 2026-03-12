import math
import pandas as pd
import os
from loguru import logger
import numpy as np
from operator import itemgetter
from model.LogAnalytics import LogAnalyticsRequest
from util.const import Const
from model.Instance import ESEC2Instance,ESEC2InstanceSizing,ESEC2MasterInstanceSizing


class CalcESEC2LogAnalyticsSizing:
    def __init__(self, lar: LogAnalyticsRequest):
        # self.source_data_size = lar.sourceDataSize
        self.daily_data_size = lar.dailyDataSize
        self.hot_data_retention_period = lar.hotDays
        self.warm_data_retention_period = lar.warmDays
        self.cold_data_retention_period = lar.coldDays
        self.replica_num = lar.replicaNum
        self.write_throughput = lar.writePeak
        self.az_num = lar.AZ
        self.dedicated_master = lar.master

        if self.hot_data_retention_period == 0:
            self.hot_data_retention_period = 1
            self.warm_data_retention_period = (self.warm_data_retention_period-1) + self.cold_data_retention_period
        else:
            self.warm_data_retention_period = self.warm_data_retention_period + self.cold_data_retention_period


        # self.source_data_size = self.source_data_size * Const.COMPRESSION_RATIO
        self.daily_data_size = self.daily_data_size
        self.compress_ratio = Const.COMPRESSION_RATIO

        self.AOS_INDEX_OVERHEAD = Const.AOS_INDEX_OVERHEAD
        self.LINUX_RESERVED_SPACE = Const.LINUX_RESERVED_SPACE
        self.DISK_WATERMARK_THRESHOLD = Const.DISK_WATERMARK_THRESHOLD
        # self.AOS_OVERHEAD = Const.AOS_OVERHEAD
        self.AOS_OVERHEAD_MAX_GB = Const.AOS_OVERHEAD_MAX_GB
        self.SHARDS_NUM_PER_GB_JVM = Const.SHARDS_NUM_PER_GB_JVM
        self.MAX_INSTANCES_PER_DOMAIN = Const.MAX_INSTANCES_PER_DOMAIN
        self.BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG = Const.BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG
        self.BEST_PRACTICE_SINGLE_CPU_SHARD = Const.BEST_PRACTICE_SINGLE_CPU_SHARD

        self.WRITE_THROUGHPUT = Const.EC2_WRITE_THROUGHPUT
        self.EC2_MASTER_LIST = Const.EC2_MASTER_LIST

    def calc_hot_required_storage(self):
        hot_overhead = (1 + self.replica_num) * (1 + self.AOS_INDEX_OVERHEAD) / (1 - self.LINUX_RESERVED_SPACE) / (
                1 - self.DISK_WATERMARK_THRESHOLD)
        hot_storage = (self.daily_data_size * self.hot_data_retention_period * hot_overhead)
        hot_storage = self.compress_ratio * hot_storage
        return math.ceil(hot_storage)

    def calc_warm_required_storage(self):
        warm_overhead = (1 + self.replica_num) * (1 + self.AOS_INDEX_OVERHEAD) / (1 - self.LINUX_RESERVED_SPACE) / (
                1 - self.DISK_WATERMARK_THRESHOLD)
        warm_storage = self.daily_data_size * warm_overhead * self.warm_data_retention_period
        warm_storage = self.compress_ratio * warm_storage
        return math.ceil(warm_storage)

    def calc_hot_and_warm_required_shards_num(self):
        overhead = (1 + self.replica_num) * (1 + self.AOS_INDEX_OVERHEAD)
        hot_data = self.daily_data_size * self.hot_data_retention_period * overhead
        hot_data = self.compress_ratio * hot_data
        warm_data = self.daily_data_size * self.warm_data_retention_period * overhead
        warm_data = self.compress_ratio * warm_data
        num = math.ceil((hot_data+warm_data)/ self.BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG)
        return num

    def _calc_hot_shards_num(self):
        overhead = (1 + self.replica_num) * (1 + self.AOS_INDEX_OVERHEAD)
        hot_data = self.daily_data_size * self.hot_data_retention_period * overhead
        hot_data = hot_data * self.compress_ratio
        num = math.ceil(hot_data/self.BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG)
        return num

    def _fix_hot_instance_number_by_az(self, instance_number):
        fix_instance_number = instance_number
        # customer 模式可以单AZ, hot可以是1台
        if self.az_num == 2 and instance_number <= 2:
            fix_instance_number = self.az_num
        elif self.az_num == 2 and instance_number > 2:
            if instance_number % 2 == 1:
                fix_instance_number = instance_number + 1
        elif self.az_num == 3 and instance_number <= 3:
            fix_instance_number = self.az_num
        elif self.az_num == 3 and instance_number > 3:
            if instance_number % 3 != 0:
                fix_instance_number = instance_number + (3 - (instance_number % 3))
        return fix_instance_number

    def calc_instance_num_by_storage(self, required_storage, instance_storage):
        instance_num = math.ceil(required_storage / instance_storage)
        return self._fix_hot_instance_number_by_az(instance_num)

    def calc_instance_num_by_shards_memory(self, required_shards, instance_memory):
        jvm_heap = math.floor(instance_memory / 2)
        if jvm_heap >= 32:
            jvm_heap = 32
        instance_max_shards_num = jvm_heap * self.SHARDS_NUM_PER_GB_JVM
        instance_num = math.ceil(required_shards / instance_max_shards_num)
        return self._fix_hot_instance_number_by_az(instance_num), instance_max_shards_num

    def calc_instance_num_by_shards_cpu(self, instance_cpu):
        hot_shard_num = self._calc_hot_shards_num()
        primary_shard = math.ceil(hot_shard_num / (1 + self.replica_num))
        activate_shard = primary_shard
        instance_num = math.ceil(activate_shard / (instance_cpu * self.BEST_PRACTICE_SINGLE_CPU_SHARD))
        return self._fix_hot_instance_number_by_az(instance_num), primary_shard

    def calc_instance_num_by_write_throughput(self, required_write_throughput, instance_type):
        if instance_type in self.WRITE_THROUGHPUT:
            instance_throughput = self.WRITE_THROUGHPUT[instance_type]
        else:
            logger.warning("There is no throughput test data for this instance_type: {}", instance_type)
            return 0
        if self.replica_num == 0:
            instance_throughput_fix = instance_throughput
        elif self.replica_num == 1:
            instance_throughput_fix = instance_throughput * 0.7
        elif self.replica_num == 2:
            instance_throughput_fix = instance_throughput * 0.5
        else:
            instance_throughput_fix = (instance_throughput / (1 + self.replica_num))
        instance_num = required_write_throughput / instance_throughput_fix
        return self._fix_hot_instance_number_by_az(math.ceil(instance_num)), math.ceil(instance_throughput)

    def _calc_dedicated_master_type(self, instance_num):
        for item in self.EC2_MASTER_LIST:
            min_v = item["instance_count"].split("-")[0]
            max_v = item["instance_count"].split("-")[1]
            if int(min_v) <= instance_num <= int(max_v):
                return item["instance_type"]
        return "r7g.8xlarge"

    def calc_es_instance_sizing(self, instance: ESEC2Instance):
        eis = ESEC2InstanceSizing()
        instance_type = instance.EC2_INSTANCE_TYPE
        max_storage_gp3 = instance.EC2_MAX_STORAGE_GP3
        cpu = instance.EC2_CPU
        memory = instance.EC2_MEMORY
        storage = max_storage_gp3

        hot_required_storage = self.calc_hot_required_storage()
        warm_required_storage = self.calc_warm_required_storage()
        total_storage = hot_required_storage+warm_required_storage
        instance_num_by_storage = self.calc_instance_num_by_storage(total_storage, storage)

        total_shards_num = self.calc_hot_and_warm_required_shards_num()
        instance_num_by_shards_memory, instance_max_shard_num = self.calc_instance_num_by_shards_memory(
            total_shards_num, memory)

        # instance_num_by_shards_cpu, primary_shard = self.calc_instance_num_by_shards_cpu(cpu)

        instance_num_by_write_throughput, instance_throughput = self.calc_instance_num_by_write_throughput(
            self.write_throughput, instance_type)

        eis.EC2_INSTANCE_TYPE = instance_type
        eis.EC2_MAX_STORAGE_GP3 = max_storage_gp3
        eis.EC2_CPU = cpu
        eis.EC2_MEMORY = memory
        eis.EC2_NUM_BY_STORAGE = instance_num_by_storage
        eis.EC2_NUM_BY_SHARD_MEMORY = instance_num_by_shards_memory
        # eis.EC2_NUM_BY_SHARD_CPU = instance_num_by_shards_cpu
        eis.EC2_NUM_BY_WRITE_THROUGHPUT = instance_num_by_write_throughput
        eis.EC2_NUM_BY_MAX_METRIC = max(
            [instance_num_by_storage, instance_num_by_shards_memory,
             # instance_num_by_shards_cpu,
             instance_num_by_write_throughput])
        eis.EC2_REQUIRED_HOT_EBS = math.ceil(hot_required_storage / eis.EC2_NUM_BY_MAX_METRIC)
        eis.EC2_REQUIRED_HOT_EBS_TOTAL = math.ceil(hot_required_storage)
        eis.EC2_REQUIRED_WARM_HDD = math.ceil(warm_required_storage / eis.EC2_NUM_BY_MAX_METRIC)
        eis.EC2_REQUIRED_WARM_HDD_TOTAL = math.ceil(warm_required_storage)
        eis.EC2_REQUIRED_EBS_TOTAL = math.ceil(hot_required_storage+warm_required_storage)
        eis.EC2_NUM = eis.EC2_NUM_BY_MAX_METRIC
        return eis

    def calc_master_instance_sizing(self, hot_instance_num):
        emis = ESEC2MasterInstanceSizing()
        emis.EC2_MASTER_TYPE = self._calc_dedicated_master_type(hot_instance_num)
        emis.EC2_MASTER_NUM = 3
        return emis

    def calc_ec2_sizing_with_limit(self, hot: ESEC2Instance):
        eis = self.calc_es_instance_sizing(hot)
        master = self.calc_master_instance_sizing(eis.EC2_NUM)
        return master, eis
