import math
from loguru import logger

from v2.config.constants import (
    AOS_INDEX_OVERHEAD,
    LINUX_RESERVED_SPACE,
    SHARDS_NUM_PER_GB_JVM,
    HARD_LIMIT_SHARDS_PER_NODE,
    BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG,
    BEST_PRACTICE_SINGLE_CPU_SHARD,
    HOT_TO_WARM_DISK_OVERHEAD,
    HOT_TO_WARM_MAX_INDEX_SIZE,
    MAX_NODES_TRADITIONAL,
    MAX_NODES_OPTIMIZED_XLARGE_UP,
    MAX_NODES_NON_OPTIMIZED_CAP,
    MAX_WARM_NODES,
    MIN_WARM_NODES,
    AOS_DEDICATED_MASTER_LIST,
    EC2_DEDICATED_MASTER_LIST,
    AOS_DEFAULT_MASTER_TYPE,
    EC2_DEFAULT_MASTER_TYPE,
    DEFAULT_COMPRESSION_RATIO,
)
from v2.config.instance_families import (
    InstanceFamily,
    ServiceType,
    get_family_for_instance,
    get_write_throughput,
    parse_instance_type,
)
from v2.models.instance import (
    InstanceSpec,
    HotSizingResult,
    WarmSizingResult,
    ColdStorageResult,
    MasterSizingResult,
)


class BaseSizingEngine:
    def __init__(
        self,
        daily_data_size: float,
        hot_days: int,
        warm_days: int,
        cold_days: int,
        replica_num: int,
        write_peak: float,
        az_num: int,
        master_count: int,
        compression_ratio: float = DEFAULT_COMPRESSION_RATIO,
        warm_architecture: str = "ultrawarm",
        enable_cpu_shard_check: bool = False,
    ):
        self.daily_data_size = daily_data_size
        self.hot_days = hot_days
        self.warm_days = warm_days
        self.cold_days = cold_days
        self.replica_num = replica_num
        self.write_peak = write_peak
        self.az_num = az_num
        self.master_count = master_count
        self.compression_ratio = compression_ratio
        self.warm_architecture = warm_architecture
        self.enable_cpu_shard_check = enable_cpu_shard_check
        self.enable_warm = warm_days > 0

    def _hot_overhead_factor(self) -> float:
        """Data overhead: replicas + index overhead + linux reserved.
        Does NOT include per-node OS/disk overhead (handled at node level).
        """
        return (
            (1 + self.replica_num)
            * (1 + AOS_INDEX_OVERHEAD)
            / (1 - LINUX_RESERVED_SPACE)
        )

    def _per_node_overhead(self, instance_storage: int) -> float:
        raise NotImplementedError

    def calc_hot_required_storage(self) -> int:
        raise NotImplementedError

    def calc_warm_required_storage(self) -> int:
        raise NotImplementedError

    def calc_cold_required_storage(self) -> int:
        raise NotImplementedError

    def calc_hot_required_shards(self) -> int:
        raise NotImplementedError

    def fix_node_count_by_az(self, node_count: int) -> int:
        if self.az_num == 1:
            return max(node_count, 1)
        if node_count <= self.az_num:
            return self.az_num
        remainder = node_count % self.az_num
        if remainder != 0:
            return node_count + (self.az_num - remainder)
        return node_count

    def calc_nodes_by_storage(
        self, required_storage: int, instance_storage: int
    ) -> int:
        usable = instance_storage - self._per_node_overhead(instance_storage)
        if usable <= 0:
            return 0
        num = math.ceil(required_storage / usable)
        return self.fix_node_count_by_az(num)

    def calc_nodes_by_shard_memory(
        self, required_shards: int, instance_memory: int
    ) -> tuple:
        jvm_heap = min(math.floor(instance_memory / 2), 32)
        max_shards_per_node = min(
            jvm_heap * SHARDS_NUM_PER_GB_JVM,
            HARD_LIMIT_SHARDS_PER_NODE,
        )
        if max_shards_per_node <= 0:
            return 0, 0
        num = math.ceil(required_shards / max_shards_per_node)
        return self.fix_node_count_by_az(num), max_shards_per_node

    def calc_nodes_by_cpu_shard(self, required_shards: int, instance_vcpu: int) -> int:
        if not self.enable_cpu_shard_check or instance_vcpu <= 0:
            return 0
        primary_shards = math.ceil(required_shards / (1 + self.replica_num))
        min_vcpus = primary_shards * BEST_PRACTICE_SINGLE_CPU_SHARD
        num = math.ceil(min_vcpus / instance_vcpu)
        return self.fix_node_count_by_az(num)

    def calc_nodes_by_write_throughput(
        self, instance_type: str, service_type: ServiceType
    ) -> tuple:
        throughput = get_write_throughput(instance_type, service_type)
        if throughput is None or throughput <= 0:
            logger.warning("No throughput data for {}", instance_type)
            return 0, 0

        family = get_family_for_instance(instance_type, service_type)
        if family and family.is_optimized:
            replica_factor = {0: 1.0, 1: 0.7, 2: 0.5}.get(
                self.replica_num, 1 / (1 + self.replica_num)
            )
        else:
            replica_factor = {0: 1.0, 1: 0.6, 2: 0.5}.get(
                self.replica_num, 1 / (1 + self.replica_num)
            )

        effective_throughput = throughput * replica_factor
        if effective_throughput <= 0:
            return 0, 0
        num = math.ceil(self.write_peak / effective_throughput)
        return self.fix_node_count_by_az(num), math.ceil(throughput)

    def fix_warm_node_count(self, node_count: int) -> int:
        if not self.enable_warm:
            return 0
        return max(node_count, MIN_WARM_NODES)

    def select_master_type(
        self,
        data_node_count: int,
        total_shards: int,
        master_list: list,
        default_type: str,
    ) -> str:
        for item in master_list:
            if (
                data_node_count <= item["max_nodes"]
                and total_shards <= item["max_shards"]
            ):
                return item["instance_type"]
        return default_type

    def validate_node_limits(
        self,
        hot_count: int,
        warm_count: int,
        instance_type: str,
        service_type: ServiceType,
    ) -> tuple:
        """Returns (hot_reason, warm_reason) — empty string means OK"""
        family = get_family_for_instance(instance_type, service_type)
        _, size = parse_instance_type(instance_type, service_type)

        if family and family.is_optimized:
            if size in ("medium", "large"):
                max_hot = family.max_node_limit_small
            else:
                max_hot = family.max_node_limit_xlarge_up
        else:
            max_hot = MAX_NODES_NON_OPTIMIZED_CAP

        az_max = MAX_NODES_TRADITIONAL.get(self.az_num)
        if az_max is None:
            return f"AZ={self.az_num} not supported", f"AZ={self.az_num} not supported"

        max_warm = MAX_WARM_NODES.get(self.az_num, 0)

        if hot_count > max_hot:
            return f"HOT nodes {hot_count} > limit {max_hot}", ""
        if hot_count > az_max:
            return f"HOT nodes {hot_count} > AZ limit {az_max}", ""
        if warm_count > max_warm:
            return "", f"WARM nodes {warm_count} > limit {max_warm}"
        if hot_count + warm_count > az_max:
            reason = f"HOT+WARM {hot_count + warm_count} > AZ limit {az_max}"
            return reason, reason

        return "", ""
