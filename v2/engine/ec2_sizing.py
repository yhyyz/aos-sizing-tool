import math
from v2.engine.base_sizing import BaseSizingEngine
from v2.config.constants import (
    AOS_INDEX_OVERHEAD,
    LINUX_RESERVED_SPACE,
    DISK_WATERMARK_THRESHOLD,
    BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG,
    EC2_DEDICATED_MASTER_LIST,
    EC2_DEFAULT_MASTER_TYPE,
    DEFAULT_COMPRESSION_RATIO,
)
from v2.config.instance_families import ServiceType
from v2.models.instance import InstanceSpec, HotSizingResult, MasterSizingResult


class EC2SizingEngine(BaseSizingEngine):
    SERVICE_TYPE = ServiceType.EC2

    def __init__(
        self,
        daily_data_size,
        hot_days,
        warm_days,
        cold_days,
        replica_num,
        write_peak,
        az_num,
        master_count,
        compression_ratio=DEFAULT_COMPRESSION_RATIO,
        enable_cpu_shard_check=False,
    ):
        super().__init__(
            daily_data_size,
            hot_days,
            warm_days,
            cold_days,
            replica_num,
            write_peak,
            az_num,
            master_count,
            compression_ratio,
            enable_cpu_shard_check=enable_cpu_shard_check,
        )

        if self.hot_days == 0:
            self.hot_days = 1
            self.warm_days = (warm_days - 1) + cold_days
        else:
            self.warm_days = warm_days + cold_days
        self.cold_days = 0

    def _hot_overhead_factor(self):
        """EC2: includes flat 20% disk watermark (no cap)."""
        return (
            (1 + self.replica_num)
            * (1 + AOS_INDEX_OVERHEAD)
            / (1 - LINUX_RESERVED_SPACE)
            / (1 - DISK_WATERMARK_THRESHOLD)
        )

    def _full_overhead_factor(self):
        return (
            (1 + self.replica_num)
            * (1 + AOS_INDEX_OVERHEAD)
            / (1 - LINUX_RESERVED_SPACE)
            / (1 - DISK_WATERMARK_THRESHOLD)
        )

    def _per_node_overhead(self, instance_storage: int) -> float:
        return 0

    def calc_hot_required_storage(self) -> int:
        overhead = self._hot_overhead_factor()
        storage = self.daily_data_size * self.hot_days * overhead
        return math.ceil(storage * self.compression_ratio)

    def calc_warm_required_storage(self) -> int:
        if self.warm_days <= 0:
            return 0
        overhead = self._full_overhead_factor()
        storage = self.daily_data_size * self.warm_days * overhead
        return math.ceil(storage * self.compression_ratio)

    def calc_cold_required_storage(self) -> int:
        return 0

    def calc_hot_and_warm_shards(self) -> int:
        overhead = (1 + self.replica_num) * (1 + AOS_INDEX_OVERHEAD)
        total = (
            self.daily_data_size
            * (self.hot_days + self.warm_days)
            * overhead
            * self.compression_ratio
        )
        return math.ceil(total / BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG)

    def calc_hot_required_shards(self) -> int:
        overhead = (1 + self.replica_num) * (1 + AOS_INDEX_OVERHEAD)
        hot_data = (
            self.daily_data_size * self.hot_days * overhead * self.compression_ratio
        )
        return math.ceil(hot_data / BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG)

    def calc_ec2_sizing(self, spec: InstanceSpec):
        result = HotSizingResult()
        result.instance_type = spec.instance_type
        result.max_storage_gp3 = spec.max_storage_gp3
        result.cpu = spec.cpu
        result.memory = spec.memory

        hot_storage = self.calc_hot_required_storage()
        warm_storage = self.calc_warm_required_storage()
        total_storage = hot_storage + warm_storage

        result.num_by_storage = self.calc_nodes_by_storage(
            total_storage, spec.max_storage_gp3
        )

        total_shards = self.calc_hot_and_warm_shards()
        result.num_by_shard_memory, _ = self.calc_nodes_by_shard_memory(
            total_shards, spec.memory
        )

        result.num_by_shard_cpu = self.calc_nodes_by_cpu_shard(total_shards, spec.cpu)

        result.num_by_write_throughput, _ = self.calc_nodes_by_write_throughput(
            spec.instance_type, self.SERVICE_TYPE
        )

        result.num_by_max_metric = max(
            result.num_by_storage,
            result.num_by_shard_memory,
            result.num_by_shard_cpu,
            result.num_by_write_throughput,
        )

        node_count = result.num_by_max_metric
        result.node_count = node_count

        if node_count > 0:
            result.required_ebs_per_node = math.ceil(hot_storage / node_count)
        result.required_ebs_total = math.ceil(hot_storage)

        return result, hot_storage, warm_storage

    def calc_master_sizing(
        self, data_node_count: int, total_shards: int
    ) -> MasterSizingResult:
        result = MasterSizingResult()
        result.instance_type = self.select_master_type(
            data_node_count,
            total_shards,
            EC2_DEDICATED_MASTER_LIST,
            EC2_DEFAULT_MASTER_TYPE,
        )
        result.node_count = 3
        return result

    def calc_full_sizing(self, spec: InstanceSpec):
        sizing_result, hot_storage, warm_storage = self.calc_ec2_sizing(spec)
        total_shards = self.calc_hot_and_warm_shards()
        master = self.calc_master_sizing(sizing_result.node_count, total_shards)
        return master, sizing_result, hot_storage, warm_storage
