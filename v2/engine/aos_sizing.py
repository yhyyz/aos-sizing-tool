import math
from v2.engine.base_sizing import BaseSizingEngine
from v2.config.constants import (
    AOS_INDEX_OVERHEAD,
    LINUX_RESERVED_SPACE,
    OS_OVERHEAD_PERCENT,
    AOS_OVERHEAD_MAX_GB,
    HOT_TO_WARM_DISK_OVERHEAD,
    HOT_TO_WARM_MAX_INDEX_SIZE,
    BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG,
    AOS_DEDICATED_MASTER_LIST,
    AOS_DEFAULT_MASTER_TYPE,
    DEFAULT_COMPRESSION_RATIO,
)
from v2.config.instance_families import (
    ServiceType,
    OI2_WARM_STORAGE_QUOTA,
    get_family_for_instance,
    parse_instance_type,
)
from v2.models.instance import (
    InstanceSpec,
    HotSizingResult,
    WarmSizingResult,
    ColdStorageResult,
    MasterSizingResult,
)


class AOSSizingEngine(BaseSizingEngine):
    SERVICE_TYPE = ServiceType.AOS

    def _per_node_overhead(self, instance_storage: int) -> float:
        return min(instance_storage * OS_OVERHEAD_PERCENT, AOS_OVERHEAD_MAX_GB)

    def _ebs_provision_for_data(self, data_needed: int) -> int:
        """EBS to provision = data + OS overhead (20% capped at 20 GiB)."""
        if data_needed <= 0:
            return 0
        if data_needed >= 80:
            return data_needed + AOS_OVERHEAD_MAX_GB
        return math.ceil(data_needed / (1 - OS_OVERHEAD_PERCENT))

    def calc_hot_required_storage(self) -> int:
        overhead = self._hot_overhead_factor()
        if self.enable_warm:
            storage = self.daily_data_size * (self.hot_days + 1) * overhead
        else:
            storage = self.daily_data_size * self.hot_days * overhead
        return math.ceil(storage * self.compression_ratio)

    def calc_hot_required_storage_for_cost_save(self) -> int:
        storage = (
            HOT_TO_WARM_MAX_INDEX_SIZE
            * (1 + self.replica_num)
            / (1 - LINUX_RESERVED_SPACE)
        )
        storage = storage * self.compression_ratio * HOT_TO_WARM_DISK_OVERHEAD
        return math.ceil(storage)

    def calc_warm_required_storage(self) -> int:
        if not self.enable_warm:
            return 0
        warm_overhead = 1 + AOS_INDEX_OVERHEAD
        storage = self.daily_data_size * warm_overhead * self.warm_days
        return math.ceil(storage * self.compression_ratio)

    def calc_hot_s3_storage(self) -> int:
        """S3 Managed Storage for Optimized instances (or1/or2/om2/oi2).
        S3 stores one copy: no replica, no linux reserved.
        """
        hot_overhead = 1 + AOS_INDEX_OVERHEAD
        days = (self.hot_days + 1) if self.enable_warm else self.hot_days
        storage = self.daily_data_size * days * hot_overhead
        return math.ceil(storage * self.compression_ratio)

    def calc_cold_required_storage(self) -> int:
        if not self.enable_warm or self.cold_days == 0:
            return 0
        if self.warm_architecture == "multi_tier":
            return 0
        cold_overhead = 1 + AOS_INDEX_OVERHEAD
        storage = self.daily_data_size * self.cold_days * cold_overhead
        return math.ceil(storage * self.compression_ratio)

    def calc_hot_required_shards(self) -> int:
        overhead = (1 + self.replica_num) * (1 + AOS_INDEX_OVERHEAD)
        hot_data = (
            self.daily_data_size * self.hot_days * overhead * self.compression_ratio
        )
        return math.ceil(hot_data / BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG)

    def calc_hot_sizing(self, spec: InstanceSpec) -> HotSizingResult:
        result = HotSizingResult()
        result.instance_type = spec.instance_type
        result.max_storage_gp3 = spec.max_storage_gp3
        result.cpu = spec.cpu
        result.memory = spec.memory

        hot_family = get_family_for_instance(spec.instance_type, self.SERVICE_TYPE)
        is_oi2_hot = hot_family is not None and not hot_family.needs_ebs_config

        hot_required_storage = self.calc_hot_required_storage()
        result.num_by_storage = self.calc_nodes_by_storage(
            hot_required_storage, spec.max_storage_gp3
        )

        hot_required_shards = self.calc_hot_required_shards()
        result.num_by_shard_memory, _ = self.calc_nodes_by_shard_memory(
            hot_required_shards, spec.memory
        )

        result.num_by_shard_cpu = self.calc_nodes_by_cpu_shard(
            hot_required_shards, spec.cpu
        )

        result.num_by_write_throughput, _ = self.calc_nodes_by_write_throughput(
            spec.instance_type, self.SERVICE_TYPE
        )

        result.num_by_max_metric = max(
            result.num_by_storage,
            result.num_by_shard_memory,
            result.num_by_shard_cpu,
            result.num_by_write_throughput,
        )

        if self.hot_days == 0:
            hot_required_storage = self.calc_hot_required_storage_for_cost_save()

        if is_oi2_hot:
            result.required_ebs_per_node = 0
            result.required_ebs_total = 0
        else:
            if result.num_by_max_metric > 0:
                data_per_node = math.ceil(
                    hot_required_storage / result.num_by_max_metric
                )
                result.required_ebs_per_node = self._ebs_provision_for_data(
                    data_per_node
                )
            result.required_ebs_total = math.ceil(
                hot_required_storage
                + self._per_node_overhead(spec.max_storage_gp3)
                * max(result.num_by_max_metric, 1)
            )
        result.node_count = result.num_by_max_metric

        return result

    def calc_warm_sizing(self, spec: InstanceSpec) -> WarmSizingResult:
        result = WarmSizingResult()
        if not self.enable_warm:
            return result

        result.instance_type = spec.instance_type
        result.cpu = spec.cpu
        result.memory = spec.memory

        warm_family_name, warm_size = parse_instance_type(
            spec.instance_type, self.SERVICE_TYPE
        )
        if warm_family_name == "oi2" and warm_size in OI2_WARM_STORAGE_QUOTA:
            result.storage_per_node = OI2_WARM_STORAGE_QUOTA[warm_size]["max_warm_gb"]
        else:
            result.storage_per_node = (
                spec.max_storage_gp3 if spec.max_storage_gp3 > 0 else spec.nvme_storage
            )

        warm_required_storage = self.calc_warm_required_storage()
        result.num_by_storage = self.calc_nodes_by_storage(
            warm_required_storage, result.storage_per_node
        )
        result.num_by_max_metric = result.num_by_storage
        result.node_count = self.fix_warm_node_count(result.num_by_max_metric)

        if result.node_count > 0:
            result.required_storage_per_node = math.ceil(
                warm_required_storage / result.node_count
            )
        result.required_storage_total = math.ceil(warm_required_storage)

        return result

    def calc_master_sizing(
        self, data_node_count: int, total_shards: int
    ) -> MasterSizingResult:
        result = MasterSizingResult()
        result.instance_type = self.select_master_type(
            data_node_count,
            total_shards,
            AOS_DEDICATED_MASTER_LIST,
            AOS_DEFAULT_MASTER_TYPE,
        )
        result.node_count = 3
        return result

    def calc_full_sizing(self, hot_spec: InstanceSpec, warm_spec: InstanceSpec):
        hot = self.calc_hot_sizing(hot_spec)
        warm = self.calc_warm_sizing(warm_spec)

        total_shards = self.calc_hot_required_shards()
        master = self.calc_master_sizing(hot.node_count, total_shards)
        cold = ColdStorageResult(required_storage=self.calc_cold_required_storage())

        hot_reason, warm_reason = self.validate_node_limits(
            hot.node_count, warm.node_count, hot_spec.instance_type, self.SERVICE_TYPE
        )
        hot.unselected_reason = hot_reason
        warm.unselected_reason = warm_reason

        return master, hot, warm, cold
