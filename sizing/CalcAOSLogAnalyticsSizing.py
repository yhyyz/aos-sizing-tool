import math
import pandas as pd
import os
from loguru import logger
import numpy as np
from operator import itemgetter
from model.LogAnalytics import LogAnalyticsRequest
from util.const import Const
from model.Instance import HotInstanceSizing, HotInstance, WarmInstance, WarmInstanceSizing, MasterInstanceSizing,ColdStorage


class CalcAOSLogAnalyticsSizing:
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
        self.enable_warm = True
        if not self.warm_data_retention_period or self.warm_data_retention_period == 0:
            self.enable_warm = False

        # self.source_data_size = self.source_data_size * Const.COMPRESSION_RATIO
        self.daily_data_size = self.daily_data_size
        self.compress_ratio = Const.COMPRESSION_RATIO

        self.MIN_WARM_NODE = Const.MIN_WARM_NODE
        self.AOS_INDEX_OVERHEAD = Const.AOS_INDEX_OVERHEAD
        self.LINUX_RESERVED_SPACE = Const.LINUX_RESERVED_SPACE
        # 0.15 or 0.2
        self.DISK_WATERMARK_THRESHOLD = Const.DISK_WATERMARK_THRESHOLD
        # self.AOS_OVERHEAD = Const.AOS_OVERHEAD
        self.AOS_OVERHEAD_MAX_GB = Const.AOS_OVERHEAD_MAX_GB
        self.SHARDS_NUM_PER_GB_JVM = Const.SHARDS_NUM_PER_GB_JVM
        self.MAX_INSTANCES_PER_DOMAIN = Const.MAX_INSTANCES_PER_DOMAIN
        self.MAX_WARM_INSTANCES_PER_DOMAIN = Const.MAX_WARM_INSTANCES_PER_DOMAIN

        self.MAX_INSTANCES_PER_DOMAIN_FOR_217_AZ1 = Const.MAX_INSTANCES_PER_DOMAIN_FOR_217_AZ1
        self.MAX_INSTANCES_PER_DOMAIN_FOR_217_AZ2 = Const.MAX_INSTANCES_PER_DOMAIN_FOR_217_AZ2
        self.MAX_INSTANCES_PER_DOMAIN_FOR_217_AZ3 = Const.MAX_INSTANCES_PER_DOMAIN_FOR_217_AZ3

        self.MAX_WARM_INSTANCES_PER_DOMAIN_FOR_217_AZ1 = Const.MAX_WARM_INSTANCES_PER_DOMAIN_FOR_217_AZ1
        self.MAX_WARM_INSTANCES_PER_DOMAIN_FOR_217_AZ2 = Const.MAX_WARM_INSTANCES_PER_DOMAIN_FOR_217_AZ2
        self.MAX_WARM_INSTANCES_PER_DOMAIN_FOR_217_AZ3 = Const.MAX_WARM_INSTANCES_PER_DOMAIN_FOR_217_AZ3

        self.MAX_INSTANCES_PER_DOMAIN_FOR_HOT_NOT_OR1_XLARGE_ABOVE = Const.MAX_INSTANCES_PER_DOMAIN_FOR_HOT_NOT_OR1_XLARGE_ABOVE

        self.BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG = Const.BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG
        self.BEST_PRACTICE_SINGLE_CPU_SHARD = Const.BEST_PRACTICE_SINGLE_CPU_SHARD

        self.HOT_TO_WARM_DISK_OVERHEAD = Const.HOT_TO_WARM_DISK_OVERHEAD
        self.HOT_TO_WARM_MAX_INDEX_SIZE = Const.HOT_TO_WARM_MAX_INDEX_SIZE

        self.WRITE_THROUGHPUT = Const.WRITE_THROUGHPUT
        self.DEDICATED_MASTER_LIST = Const.DEDICATED_MASTER_LIST

    def calc_hot_required_storage(self):
        hot_overhead = (1 + self.replica_num) * (1 + self.AOS_INDEX_OVERHEAD) / (1 - self.LINUX_RESERVED_SPACE) / (
                1 - self.DISK_WATERMARK_THRESHOLD)
        if self.warm_data_retention_period == 0:
            hot_storage = (self.daily_data_size * self.hot_data_retention_period * hot_overhead)
        else:
            # 加一天的数据空间用来热转暖
            # Add an extra day of disk space for hot to warm migration
            hot_storage = (self.daily_data_size * self.hot_data_retention_period * hot_overhead) + (
                    self.daily_data_size * hot_overhead)
        hot_storage = self.compress_ratio * hot_storage
        return math.ceil(hot_storage)

    def calc_hot_required_storage_for_cost_save(self):
        storage = (self.HOT_TO_WARM_MAX_INDEX_SIZE * (1 + self.replica_num)) / (1 - self.LINUX_RESERVED_SPACE) / (
                1 - self.DISK_WATERMARK_THRESHOLD)
        storage = self.compress_ratio * storage
        storage_ = storage * self.HOT_TO_WARM_DISK_OVERHEAD
        return math.ceil(storage_)

    def calc_warm_required_storage(self):
        warm_overhead = (1 + self.AOS_INDEX_OVERHEAD)
        warm_storage = self.daily_data_size * warm_overhead * self.warm_data_retention_period
        warm_storage = self.compress_ratio * warm_storage
        return math.ceil(warm_storage)

    def calc_cold_required_storage(self):
        if self.warm_data_retention_period == 0:
            return 0
        cold_overhead = (1 + self.AOS_INDEX_OVERHEAD)
        cold_storage = self.daily_data_size * self.cold_data_retention_period * cold_overhead
        cold_storage = self.compress_ratio * cold_storage
        return math.ceil(cold_storage)

    def calc_hot_required_shards_num(self):
        overhead = (1 + self.replica_num) * (1 + self.AOS_INDEX_OVERHEAD)
        hot_data = self.daily_data_size * self.hot_data_retention_period * overhead
        hot_data = self.compress_ratio * hot_data
        num = math.ceil(hot_data / self.BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG)
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

    def calc_hot_instance_num_by_storage(self, required_storage, instance_storage):
        instance_num = math.ceil(required_storage / instance_storage)
        return self._fix_hot_instance_number_by_az(instance_num)

    def calc_hot_instance_num_by_shards_memory(self, required_shards, instance_memory):
        jvm_heap = math.floor(instance_memory / 2)
        if jvm_heap >= 32:
            jvm_heap = 32
        instance_max_shards_num = jvm_heap * self.SHARDS_NUM_PER_GB_JVM
        instance_num = math.ceil(required_shards / instance_max_shards_num)
        return self._fix_hot_instance_number_by_az(instance_num), instance_max_shards_num

    def calc_hot_instance_num_by_shards_cpu(self, instance_cpu):
        host_shard_num = self.calc_hot_required_shards_num()
        primary_shard = math.ceil(host_shard_num / (1 + self.replica_num))
        activate_shard = primary_shard
        instance_num = math.ceil(activate_shard / (instance_cpu * self.BEST_PRACTICE_SINGLE_CPU_SHARD))
        return self._fix_hot_instance_number_by_az(instance_num), primary_shard

    def calc_host_instance_num_by_write_throughput(self, required_write_throughput, instance_type):
        if instance_type in self.WRITE_THROUGHPUT:
            instance_throughput = self.WRITE_THROUGHPUT[instance_type]
        else:
            logger.warning("There is no throughput test data for this instance_type: {}", instance_type)
            return 0
        if self.replica_num == 0:
            instance_throughput_fix = instance_throughput
        elif self.replica_num == 1:
            instance_throughput_fix = instance_throughput * 0.6
        elif self.replica_num == 2:
            instance_throughput_fix = instance_throughput * 0.5
        else:
            instance_throughput_fix = (instance_throughput / (1 + self.replica_num))
        instance_num = required_write_throughput / instance_throughput_fix
        return self._fix_hot_instance_number_by_az(math.ceil(instance_num)), math.ceil(instance_throughput)

    def _fix_warm_instance_num_by_limit(self, instance_num):
        if self.warm_data_retention_period == 0:
            return 0
        if instance_num < self.MIN_WARM_NODE:
            return self.MIN_WARM_NODE
        else:
            return instance_num

    def calc_warm_instance_num_by_storage(self, required_warm_storage, instance_storage):
        instance_num = math.ceil(required_warm_storage / instance_storage)
        return self._fix_warm_instance_num_by_limit(instance_num)

    def _calc_dedicated_master_type(self, instance_num):
        for item in self.DEDICATED_MASTER_LIST:
            min_v = item["instance_count"].split("-")[0]
            max_v = item["instance_count"].split("-")[1]
            if int(min_v) <= instance_num <= int(max_v):
                return item["instance_type"]
        return "r7g.8xlarge.search"

    def calc_hot_instance_sizing(self, instance: HotInstance):
        his = HotInstanceSizing()
        instance_type = instance.INSTANCE_TYPE
        max_storage_gp3 = instance.MAX_STORAGE_GP3
        cpu = instance.CPU
        memory = instance.MEMORY
        storage = max_storage_gp3

        hot_required_storage = self.calc_hot_required_storage()
        hot_instance_num_by_storage = self.calc_hot_instance_num_by_storage(hot_required_storage, storage)

        hot_required_shards_num = self.calc_hot_required_shards_num()
        hot_instance_num_by_shards_memory, instance_max_shard_num = self.calc_hot_instance_num_by_shards_memory(
            hot_required_shards_num, memory)

        # hot_instance_num_by_shards_cpu, primary_shard = self.calc_hot_instance_num_by_shards_cpu(cpu)
        host_instance_num_by_write_throughput, instance_throughput = self.calc_host_instance_num_by_write_throughput(
            self.write_throughput, instance_type)

        his.INSTANCE_TYPE = instance_type
        his.MAX_STORAGE_GP3 = max_storage_gp3
        his.CPU = cpu
        his.MEMORY = memory
        his.HOT_NUM_BY_STORAGE = hot_instance_num_by_storage
        his.HOT_NUM_BY_SHARD_MEMORY = hot_instance_num_by_shards_memory
        # his.HOT_NUM_BY_SHARD_CPU = hot_instance_num_by_shards_cpu
        his.HOT_NUM_BY_WRITE_THROUGHPUT = host_instance_num_by_write_throughput
        his.HOT_NUM_BY_MAX_METRIC = max(
            [hot_instance_num_by_storage, hot_instance_num_by_shards_memory,
             # hot_instance_num_by_shards_cpu,
             host_instance_num_by_write_throughput])
        if self.hot_data_retention_period == 0:
            hot_required_storage = self.calc_hot_required_storage_for_cost_save()
        his.HOT_REQUIRED_EBS = math.ceil(hot_required_storage / his.HOT_NUM_BY_MAX_METRIC)
        his.HOT_REQUIRED_EBS_TOTAL = math.ceil(hot_required_storage)
        his.HOT_NUM = his.HOT_NUM_BY_MAX_METRIC
        return his

    def calc_warm_instance_sizing(self, instance: WarmInstance):
        wis = WarmInstanceSizing()
        if not self.enable_warm:
            return wis
        instance_type = instance.WARM_INSTANCE_TYPE
        cpu = instance.WARM_CPU
        memory = instance.WARM_MEMORY
        storage = instance.STORAGE

        warm_required_storage = self.calc_warm_required_storage()
        warm_instance_num_by_storage = self.calc_warm_instance_num_by_storage(warm_required_storage, storage)

        wis.WARM_INSTANCE_TYPE = instance_type
        wis.WARM_CPU = cpu
        wis.WARM_MEMORY = memory
        wis.STORAGE = storage
        wis.WARM_NUM_BY_STORAGE = warm_instance_num_by_storage
        wis.WARM_NUM_BY_MAX_METRIC = max([warm_instance_num_by_storage])
        wis.WARM_REQUIRED_STORAGE = math.ceil(warm_required_storage / wis.WARM_NUM_BY_MAX_METRIC)
        wis.WARM_REQUIRED_STORAGE_TOTAL = math.ceil(warm_required_storage)
        wis.WARM_NUM = wis.WARM_NUM_BY_MAX_METRIC
        return wis

    def calc_master_instance_sizing(self, hot_instance_num):
        mis = MasterInstanceSizing()
        mis.DEDICATED_MASTER_TYPE = self._calc_dedicated_master_type(hot_instance_num)
        mis.MASTER_NUM = 3
        return mis

    def calc_sizing_with_limit(self, hot: HotInstance, warm: WarmInstance):
        his = self.calc_hot_instance_sizing(hot)
        wis = self.calc_warm_instance_sizing(warm)
        master = self.calc_master_instance_sizing(his.HOT_NUM)
        cs = ColdStorage()
        cs.COLD_REQUIRED_STORAGE = self.calc_cold_required_storage()
        # max_instance_per_domain = 0
        # max_warm_instance_per_domain = 0
        if self.az_num == 1:
            max_instance_per_domain = self.MAX_INSTANCES_PER_DOMAIN_FOR_217_AZ1
            max_warm_instance_per_domain = self.MAX_WARM_INSTANCES_PER_DOMAIN_FOR_217_AZ1
        elif self.az_num == 2:
            max_instance_per_domain = self.MAX_INSTANCES_PER_DOMAIN_FOR_217_AZ2
            max_warm_instance_per_domain = self.MAX_WARM_INSTANCES_PER_DOMAIN_FOR_217_AZ2
        elif self.az_num == 3:
            max_instance_per_domain = self.MAX_INSTANCES_PER_DOMAIN_FOR_217_AZ3
            max_warm_instance_per_domain = self.MAX_WARM_INSTANCES_PER_DOMAIN_FOR_217_AZ3
        else:
            his.HOT_UNSELECTED = f"AZ为{self.az_num}不支持"
            wis.WARM_UNSELECTED = f"AZ为{self.az_num}不支持"
            return master, his, wis, cs

        if his.INSTANCE_TYPE not in ["or1.xlarge.search", "or1.2xlarge.search", "or1.4xlarge.search",
                                     "or1.8xlarge.search", "or1.12xlarge.search", "or1.16xlarge.search"]:

            if his.HOT_NUM > self.MAX_INSTANCES_PER_DOMAIN_FOR_HOT_NOT_OR1_XLARGE_ABOVE:
                his.HOT_UNSELECTED = "Maximum HOT not or1.xalrge.search above limit exceeded: {}>{}".format(his.HOT_NUM, self.MAX_INSTANCES_PER_DOMAIN_FOR_HOT_NOT_OR1_XLARGE_ABOVE)

        if his.HOT_NUM > max_instance_per_domain:
            his.HOT_UNSELECTED = "Maximum HOT limit exceeded: {}>{}".format(his.HOT_NUM, max_instance_per_domain)
        elif wis.WARM_NUM > max_warm_instance_per_domain:
            wis.WARM_UNSELECTED = "Maximum HOT limit exceeded: {}>{}".format(wis.WARM_NUM,
                                                                             max_warm_instance_per_domain)
        elif his.HOT_NUM + wis.WARM_NUM > max_instance_per_domain:
            reason = "Maximum HOT+WARM limit exceeded: {}>{}".format(wis.WARM_NUM + his.HOT_NUM,
                                                                     max_instance_per_domain)
            his.HOT_UNSELECTED = reason
            wis.WARM_UNSELECTED = reason
        return master, his, wis, cs
