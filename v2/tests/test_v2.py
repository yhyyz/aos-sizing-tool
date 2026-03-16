import pytest
import math
from v2.config.constants import (
    DEFAULT_COMPRESSION_RATIO,
    AOS_INDEX_OVERHEAD,
    LINUX_RESERVED_SPACE,
    DISK_WATERMARK_THRESHOLD,
    OS_OVERHEAD_PERCENT,
    AOS_OVERHEAD_MAX_GB,
    SHARDS_NUM_PER_GB_JVM,
    HARD_LIMIT_SHARDS_PER_NODE,
    BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG,
    BEST_PRACTICE_SINGLE_CPU_SHARD,
)
from v2.config.instance_families import (
    AOS_FAMILIES,
    EC2_FAMILIES,
    OI2_WARM_STORAGE_QUOTA,
    get_write_throughput,
    parse_instance_type,
    get_family_for_instance,
    is_valid_warm_combination,
    ServiceType,
    WarmArchitecture,
)
from v2.engine.aos_sizing import AOSSizingEngine
from v2.engine.ec2_sizing import EC2SizingEngine
from v2.engine.base_pricing import BasePricingEngine
from v2.models.instance import InstanceSpec


class TestInstanceFamilies:
    def test_aos_families_registered(self):
        expected = {
            "or1",
            "or2",
            "om2",
            "oi2",
            "r7g",
            "r8g",
            "m7g",
            "m8g",
            "c7g",
            "c8g",
            "r6g",
            "m6g",
            "c6g",
        }
        assert set(AOS_FAMILIES.keys()) == expected

    def test_ec2_families_registered(self):
        expected = {
            "or1",
            "i8ge",
            "r7g",
            "r8g",
            "m7g",
            "m8g",
            "c7g",
            "c8g",
            "r6g",
            "m6g",
            "c6g",
        }
        assert set(EC2_FAMILIES.keys()) == expected

    def test_parse_instance_type_aos(self):
        family, size = parse_instance_type("or1.4xlarge.search", ServiceType.AOS)
        assert family == "or1"
        assert size == "4xlarge"

    def test_parse_instance_type_ec2(self):
        family, size = parse_instance_type("r7g.medium", ServiceType.EC2)
        assert family == "r7g"
        assert size == "medium"

    def test_get_write_throughput(self):
        tp = get_write_throughput("or1.4xlarge.search", ServiceType.AOS)
        assert tp is not None
        assert tp > 0

    def test_optimized_families_flagged(self):
        for name in ["or1", "or2", "om2", "oi2"]:
            assert AOS_FAMILIES[name].is_optimized is True

    def test_non_optimized_families_flagged(self):
        for name in ["r7g", "m7g", "c7g", "r6g", "m6g", "c6g"]:
            assert AOS_FAMILIES[name].is_optimized is False

    def test_oi2_no_ebs(self):
        assert AOS_FAMILIES["oi2"].needs_ebs_config is False

    def test_oi2_can_be_warm(self):
        assert AOS_FAMILIES["oi2"].can_be_warm is True


class TestAOSSizingEngine:
    def _make_engine(self, **kwargs):
        defaults = dict(
            daily_data_size=200000,
            hot_days=14,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=2370,
            az_num=2,
            master_count=3,
            compression_ratio=0.4,
        )
        defaults.update(kwargs)
        return AOSSizingEngine(**defaults)

    def test_hot_required_storage_no_warm(self):
        engine = self._make_engine()
        storage = engine.calc_hot_required_storage()
        overhead = (1 + 0) * (1 + AOS_INDEX_OVERHEAD) / (1 - LINUX_RESERVED_SPACE)
        expected = math.ceil(200000 * 14 * overhead * 0.4)
        assert storage == expected

    def test_hot_required_storage_with_warm(self):
        engine = self._make_engine(warm_days=30)
        storage = engine.calc_hot_required_storage()
        overhead = (1 + 0) * (1 + AOS_INDEX_OVERHEAD) / (1 - LINUX_RESERVED_SPACE)
        expected = math.ceil(200000 * (14 + 1) * overhead * 0.4)
        assert storage == expected

    def test_warm_required_storage(self):
        engine = self._make_engine(warm_days=30)
        storage = engine.calc_warm_required_storage()
        expected = math.ceil(200000 * (1 + AOS_INDEX_OVERHEAD) * 30 * 0.4)
        assert storage == expected

    def test_warm_required_storage_zero_when_disabled(self):
        engine = self._make_engine(warm_days=0)
        assert engine.calc_warm_required_storage() == 0

    def test_cold_required_storage(self):
        engine = self._make_engine(warm_days=30, cold_days=60)
        storage = engine.calc_cold_required_storage()
        expected = math.ceil(200000 * 60 * (1 + AOS_INDEX_OVERHEAD) * 0.4)
        assert storage == expected

    def test_cold_requires_warm(self):
        engine = self._make_engine(warm_days=0, cold_days=60)
        assert engine.calc_cold_required_storage() == 0

    def test_fix_node_count_by_az(self):
        engine = self._make_engine(az_num=2)
        assert engine.fix_node_count_by_az(1) == 2
        assert engine.fix_node_count_by_az(3) == 4
        assert engine.fix_node_count_by_az(4) == 4

    def test_fix_node_count_by_az_3(self):
        engine = self._make_engine(az_num=3)
        assert engine.fix_node_count_by_az(1) == 3
        assert engine.fix_node_count_by_az(4) == 6
        assert engine.fix_node_count_by_az(6) == 6

    def test_calc_hot_sizing(self):
        engine = self._make_engine()
        spec = InstanceSpec(
            instance_type="or1.2xlarge.search",
            max_storage_gp3=24576,
            cpu=8,
            memory=64,
        )
        result = engine.calc_hot_sizing(spec)
        assert result.instance_type == "or1.2xlarge.search"
        assert result.node_count > 0
        assert result.num_by_max_metric == max(
            result.num_by_storage,
            result.num_by_shard_memory,
            result.num_by_write_throughput,
        )

    def test_compression_ratio_parameter(self):
        engine_default = self._make_engine()
        engine_custom = self._make_engine(compression_ratio=0.6)
        s1 = engine_default.calc_hot_required_storage()
        s2 = engine_custom.calc_hot_required_storage()
        assert s2 > s1


class TestEC2SizingEngine:
    def _make_engine(self, **kwargs):
        defaults = dict(
            daily_data_size=2000,
            hot_days=1,
            warm_days=7,
            cold_days=14,
            replica_num=1,
            write_peak=24,
            az_num=2,
            master_count=3,
            compression_ratio=0.4,
        )
        defaults.update(kwargs)
        return EC2SizingEngine(**defaults)

    def test_warm_cold_merged(self):
        engine = self._make_engine()
        assert engine.warm_days == 7 + 14
        assert engine.cold_days == 0

    def test_hot_days_zero_forces_one(self):
        engine = self._make_engine(hot_days=0, warm_days=10, cold_days=5)
        assert engine.hot_days == 1
        assert engine.warm_days == (10 - 1) + 5

    def test_warm_storage_includes_replica(self):
        engine = self._make_engine()
        storage = engine.calc_warm_required_storage()
        overhead = (
            (1 + 1)
            * (1 + AOS_INDEX_OVERHEAD)
            / (1 - LINUX_RESERVED_SPACE)
            / (1 - DISK_WATERMARK_THRESHOLD)
        )
        expected = math.ceil(2000 * (7 + 14) * overhead * 0.4)
        assert storage == expected


class TestNodeLimits:
    def test_optimized_instance_limit(self):
        engine = AOSSizingEngine(
            daily_data_size=1,
            hot_days=1,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=0,
            az_num=2,
            master_count=3,
        )
        hot_reason, _ = engine.validate_node_limits(
            500, 0, "or1.4xlarge.search", ServiceType.AOS
        )
        assert hot_reason == ""

    def test_non_optimized_instance_limit(self):
        engine = AOSSizingEngine(
            daily_data_size=1,
            hot_days=1,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=0,
            az_num=2,
            master_count=3,
        )
        hot_reason, _ = engine.validate_node_limits(
            500, 0, "r7g.4xlarge.search", ServiceType.AOS
        )
        assert "limit" in hot_reason


class TestMasterSelection:
    def test_small_cluster(self):
        engine = AOSSizingEngine(
            daily_data_size=1,
            hot_days=1,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=0,
            az_num=2,
            master_count=3,
        )
        from v2.config.constants import (
            AOS_DEDICATED_MASTER_LIST,
            AOS_DEFAULT_MASTER_TYPE,
        )

        master_type = engine.select_master_type(
            10, 100, AOS_DEDICATED_MASTER_LIST, AOS_DEFAULT_MASTER_TYPE
        )
        assert master_type == "m7g.large.search"

    def test_large_cluster(self):
        engine = AOSSizingEngine(
            daily_data_size=1,
            hot_days=1,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=0,
            az_num=2,
            master_count=3,
        )
        from v2.config.constants import (
            AOS_DEDICATED_MASTER_LIST,
            AOS_DEFAULT_MASTER_TYPE,
        )

        master_type = engine.select_master_type(
            500, 300000, AOS_DEDICATED_MASTER_LIST, AOS_DEFAULT_MASTER_TYPE
        )
        assert master_type == "r7g.8xlarge.search"


# ============================================================
# 架构兼容性测试
# ============================================================


class TestWarmArchitectureValidation:
    """测试 is_valid_warm_combination 函数"""

    def test_ultrawarm_valid_r7g_with_ultrawarm1(self):
        assert (
            is_valid_warm_combination(
                "r7g.xlarge.search",
                "ultrawarm1.medium.search",
                "ultrawarm",
                ServiceType.AOS,
            )
            is True
        )

    def test_ultrawarm_valid_or1_with_ultrawarm1(self):
        assert (
            is_valid_warm_combination(
                "or1.4xlarge.search",
                "ultrawarm1.large.search",
                "ultrawarm",
                ServiceType.AOS,
            )
            is True
        )

    def test_ultrawarm_invalid_r7g_with_oi2(self):
        """UltraWarm 架构不能用 OI2 做 warm"""
        assert (
            is_valid_warm_combination(
                "r7g.xlarge.search", "oi2.large.search", "ultrawarm", ServiceType.AOS
            )
            is False
        )

    def test_multi_tier_valid_or1_with_oi2(self):
        assert (
            is_valid_warm_combination(
                "or1.4xlarge.search",
                "oi2.2xlarge.search",
                "multi_tier",
                ServiceType.AOS,
            )
            is True
        )

    def test_multi_tier_valid_oi2_with_oi2(self):
        assert (
            is_valid_warm_combination(
                "oi2.4xlarge.search",
                "oi2.2xlarge.search",
                "multi_tier",
                ServiceType.AOS,
            )
            is True
        )

    def test_multi_tier_invalid_r7g_hot(self):
        """multi_tier 架构 hot 必须是 optimized 实例"""
        assert (
            is_valid_warm_combination(
                "r7g.xlarge.search", "oi2.large.search", "multi_tier", ServiceType.AOS
            )
            is False
        )

    def test_multi_tier_invalid_ultrawarm_warm(self):
        """multi_tier 架构 warm 必须是 OI2"""
        assert (
            is_valid_warm_combination(
                "or1.4xlarge.search",
                "ultrawarm1.medium.search",
                "multi_tier",
                ServiceType.AOS,
            )
            is False
        )

    def test_invalid_architecture_returns_false(self):
        assert (
            is_valid_warm_combination(
                "or1.4xlarge.search",
                "ultrawarm1.medium.search",
                "invalid",
                ServiceType.AOS,
            )
            is False
        )


class TestMultiTierColdDisabled:
    """multi_tier 架构禁用 cold tier"""

    def test_cold_zero_in_multi_tier(self):
        engine = AOSSizingEngine(
            daily_data_size=200000,
            hot_days=14,
            warm_days=30,
            cold_days=60,
            replica_num=0,
            write_peak=2370,
            az_num=2,
            master_count=3,
            warm_architecture="multi_tier",
        )
        assert engine.calc_cold_required_storage() == 0

    def test_cold_nonzero_in_ultrawarm(self):
        engine = AOSSizingEngine(
            daily_data_size=200000,
            hot_days=14,
            warm_days=30,
            cold_days=60,
            replica_num=0,
            write_peak=2370,
            az_num=2,
            master_count=3,
            warm_architecture="ultrawarm",
        )
        assert engine.calc_cold_required_storage() > 0

    def test_warm_architecture_default_is_ultrawarm(self):
        engine = AOSSizingEngine(
            daily_data_size=1,
            hot_days=1,
            warm_days=1,
            cold_days=1,
            replica_num=0,
            write_peak=0,
            az_num=2,
            master_count=3,
        )
        assert engine.warm_architecture == "ultrawarm"


class TestOI2HotSizing:
    """OI2 作为 hot 节点：无 EBS"""

    def test_oi2_hot_no_ebs(self):
        engine = AOSSizingEngine(
            daily_data_size=200000,
            hot_days=14,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=2370,
            az_num=2,
            master_count=3,
        )
        spec = InstanceSpec(
            instance_type="oi2.4xlarge.search",
            max_storage_gp3=0,
            cpu=16,
            memory=128,
        )
        result = engine.calc_hot_sizing(spec)
        assert result.required_ebs_per_node == 0
        assert result.required_ebs_total == 0

    def test_non_oi2_hot_has_ebs(self):
        engine = AOSSizingEngine(
            daily_data_size=200000,
            hot_days=14,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=2370,
            az_num=2,
            master_count=3,
        )
        spec = InstanceSpec(
            instance_type="or1.2xlarge.search",
            max_storage_gp3=24576,
            cpu=8,
            memory=64,
        )
        result = engine.calc_hot_sizing(spec)
        assert result.required_ebs_per_node > 0
        assert result.required_ebs_total > 0


class TestOI2WarmSizing:
    """OI2 作为 warm 节点：使用 NVMe 配额"""

    def test_oi2_warm_uses_nvme_quota(self):
        engine = AOSSizingEngine(
            daily_data_size=200000,
            hot_days=14,
            warm_days=30,
            cold_days=0,
            replica_num=0,
            write_peak=2370,
            az_num=2,
            master_count=3,
            warm_architecture="multi_tier",
        )
        spec = InstanceSpec(
            instance_type="oi2.2xlarge.search",
            cpu=8,
            memory=64,
            max_storage_gp3=0,
        )
        result = engine.calc_warm_sizing(spec)
        assert (
            result.storage_per_node == OI2_WARM_STORAGE_QUOTA["2xlarge"]["max_warm_gb"]
        )
        assert result.storage_per_node == 7500

    def test_ultrawarm_uses_spec_storage(self):
        engine = AOSSizingEngine(
            daily_data_size=200000,
            hot_days=14,
            warm_days=30,
            cold_days=0,
            replica_num=0,
            write_peak=2370,
            az_num=2,
            master_count=3,
            warm_architecture="ultrawarm",
        )
        spec = InstanceSpec(
            instance_type="ultrawarm1.medium.search",
            cpu=2,
            memory=15,
            max_storage_gp3=1536,
        )
        result = engine.calc_warm_sizing(spec)
        assert result.storage_per_node == 1536

    def test_oi2_warm_all_sizes_mapped(self):
        """确保所有 OI2 warm size 都有配额映射"""
        for size in ["large", "xlarge", "2xlarge", "4xlarge", "8xlarge"]:
            assert size in OI2_WARM_STORAGE_QUOTA
            assert OI2_WARM_STORAGE_QUOTA[size]["max_warm_gb"] > 0


class TestInstanceFamilyArchitecture:
    """测试实例家族的架构支持标志"""

    def test_or1_supports_both_architectures(self):
        family = AOS_FAMILIES["or1"]
        assert WarmArchitecture.ULTRAWARM in family.supported_warm_architectures
        assert WarmArchitecture.MULTI_TIER in family.supported_warm_architectures

    def test_oi2_supports_multi_tier_only(self):
        family = AOS_FAMILIES["oi2"]
        assert WarmArchitecture.MULTI_TIER in family.supported_warm_architectures
        assert WarmArchitecture.ULTRAWARM not in family.supported_warm_architectures

    def test_r7g_supports_ultrawarm_only(self):
        family = AOS_FAMILIES["r7g"]
        assert WarmArchitecture.ULTRAWARM in family.supported_warm_architectures
        assert WarmArchitecture.MULTI_TIER not in family.supported_warm_architectures

    def test_oi2_is_only_warm_capable(self):
        """只有 OI2 可以作为 warm 节点"""
        for name, family in AOS_FAMILIES.items():
            if name == "oi2":
                assert family.can_be_warm is True
            else:
                assert family.can_be_warm is False, f"{name} should not be warm-capable"


# ============================================================
# Fix 1: OS 20% overhead capped at 20 GiB
# ============================================================


class TestAOSOverheadCap:
    def test_small_instance_overhead_is_20_percent(self):
        engine = AOSSizingEngine(
            daily_data_size=100,
            hot_days=1,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=0,
            az_num=1,
            master_count=3,
        )
        assert engine._per_node_overhead(100) == 20.0

    def test_large_instance_overhead_capped_at_20gb(self):
        engine = AOSSizingEngine(
            daily_data_size=100,
            hot_days=1,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=0,
            az_num=1,
            master_count=3,
        )
        assert engine._per_node_overhead(500) == 20
        assert engine._per_node_overhead(3000) == 20
        assert engine._per_node_overhead(6144) == 20

    def test_nodes_by_storage_uses_usable_capacity(self):
        engine = AOSSizingEngine(
            daily_data_size=100,
            hot_days=1,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=0,
            az_num=1,
            master_count=3,
        )
        usable = 500 - 20  # 480
        data = 960
        expected = math.ceil(data / usable)
        assert engine.calc_nodes_by_storage(data, 500) == expected

    def test_ec2_overhead_is_zero_at_node_level(self):
        engine = EC2SizingEngine(
            daily_data_size=100,
            hot_days=1,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=0,
            az_num=1,
            master_count=3,
        )
        assert engine._per_node_overhead(500) == 0
        assert engine._per_node_overhead(3000) == 0

    def test_ebs_provision_includes_overhead(self):
        engine = AOSSizingEngine(
            daily_data_size=100,
            hot_days=1,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=0,
            az_num=1,
            master_count=3,
        )
        assert engine._ebs_provision_for_data(200) == 220
        assert engine._ebs_provision_for_data(80) == 100
        assert engine._ebs_provision_for_data(50) == math.ceil(50 / 0.8)
        assert engine._ebs_provision_for_data(0) == 0

    def test_aos_storage_formula_no_os_overhead(self):
        engine = AOSSizingEngine(
            daily_data_size=1000,
            hot_days=14,
            warm_days=0,
            cold_days=0,
            replica_num=1,
            write_peak=0,
            az_num=2,
            master_count=3,
        )
        storage = engine.calc_hot_required_storage()
        overhead = (1 + 1) * (1 + AOS_INDEX_OVERHEAD) / (1 - LINUX_RESERVED_SPACE)
        expected = math.ceil(1000 * 14 * overhead * 0.4)
        assert storage == expected


# ============================================================
# Fix 2: CPU × shard check (default off)
# ============================================================


class TestCpuShardCheck:
    def test_disabled_by_default(self):
        engine = AOSSizingEngine(
            daily_data_size=200000,
            hot_days=14,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=0,
            az_num=2,
            master_count=3,
        )
        assert engine.calc_nodes_by_cpu_shard(100, 4) == 0

    def test_enabled_calculates_nodes(self):
        engine = AOSSizingEngine(
            daily_data_size=200000,
            hot_days=14,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=0,
            az_num=2,
            master_count=3,
            enable_cpu_shard_check=True,
        )
        shards = 100  # 100 total = 100 primary (0 replica)
        vcpu = 4
        min_vcpus = 100 * BEST_PRACTICE_SINGLE_CPU_SHARD
        expected = math.ceil(min_vcpus / vcpu)
        expected = engine.fix_node_count_by_az(expected)
        assert engine.calc_nodes_by_cpu_shard(shards, vcpu) == expected

    def test_enabled_with_replicas(self):
        engine = AOSSizingEngine(
            daily_data_size=200000,
            hot_days=14,
            warm_days=0,
            cold_days=0,
            replica_num=1,
            write_peak=0,
            az_num=2,
            master_count=3,
            enable_cpu_shard_check=True,
        )
        total_shards = 200  # 100 primary + 100 replica
        vcpu = 8
        primary = math.ceil(total_shards / 2)
        min_vcpus = primary * BEST_PRACTICE_SINGLE_CPU_SHARD
        expected = engine.fix_node_count_by_az(math.ceil(min_vcpus / vcpu))
        assert engine.calc_nodes_by_cpu_shard(total_shards, vcpu) == expected

    def test_request_model_has_field(self):
        from v2.models.request import SizingRequest

        req = SizingRequest()
        assert req.enableCpuShardCheck is False
        req2 = SizingRequest(enableCpuShardCheck=True)
        assert req2.enableCpuShardCheck is True


# ============================================================
# Fix 3: SHARDS_NUM_PER_GB_JVM = 25 + hard limit
# ============================================================


class TestShardConstants:
    def test_shards_per_gb_jvm_is_25(self):
        assert SHARDS_NUM_PER_GB_JVM == 25

    def test_hard_limit_is_1000(self):
        assert HARD_LIMIT_SHARDS_PER_NODE == 1000

    def test_shard_memory_applies_hard_limit(self):
        engine = AOSSizingEngine(
            daily_data_size=100,
            hot_days=1,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=0,
            az_num=1,
            master_count=3,
        )
        # 256 GB RAM → 32 GB heap → 32 * 25 = 800 (< 1000, no cap)
        _, max_per_node = engine.calc_nodes_by_shard_memory(100, 256)
        assert max_per_node == 800

    def test_shard_memory_caps_at_hard_limit(self):
        engine = AOSSizingEngine(
            daily_data_size=100,
            hot_days=1,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=0,
            az_num=1,
            master_count=3,
        )
        # 512 GB RAM → 32 GB heap (capped) → 32 * 25 = 800 (< 1000, no cap)
        # To hit the limit, we'd need heap > 40 GB, but heap caps at 32
        # So with the 25 shards/GB and 32 GB max heap, max is 800
        _, max_per_node = engine.calc_nodes_by_shard_memory(100, 512)
        assert max_per_node == min(
            32 * SHARDS_NUM_PER_GB_JVM, HARD_LIMIT_SHARDS_PER_NODE
        )


# ============================================================
# Fix 4: Master selection by both nodes AND shards
# ============================================================


class TestMasterSelectionDual:
    def _make_engine(self):
        return AOSSizingEngine(
            daily_data_size=1,
            hot_days=1,
            warm_days=0,
            cold_days=0,
            replica_num=0,
            write_peak=0,
            az_num=2,
            master_count=3,
        )

    def test_small_nodes_small_shards(self):
        from v2.config.constants import (
            AOS_DEDICATED_MASTER_LIST,
            AOS_DEFAULT_MASTER_TYPE,
        )

        engine = self._make_engine()
        result = engine.select_master_type(
            10, 5000, AOS_DEDICATED_MASTER_LIST, AOS_DEFAULT_MASTER_TYPE
        )
        assert result == "m7g.large.search"

    def test_small_nodes_large_shards(self):
        from v2.config.constants import (
            AOS_DEDICATED_MASTER_LIST,
            AOS_DEFAULT_MASTER_TYPE,
        )

        engine = self._make_engine()
        result = engine.select_master_type(
            10, 50000, AOS_DEDICATED_MASTER_LIST, AOS_DEFAULT_MASTER_TYPE
        )
        assert result == "r7g.xlarge.search"

    def test_large_nodes_small_shards(self):
        from v2.config.constants import (
            AOS_DEDICATED_MASTER_LIST,
            AOS_DEFAULT_MASTER_TYPE,
        )

        engine = self._make_engine()
        result = engine.select_master_type(
            100, 1000, AOS_DEDICATED_MASTER_LIST, AOS_DEFAULT_MASTER_TYPE
        )
        assert result == "r7g.xlarge.search"

    def test_both_exceed_returns_default(self):
        from v2.config.constants import (
            AOS_DEDICATED_MASTER_LIST,
            AOS_DEFAULT_MASTER_TYPE,
        )

        engine = self._make_engine()
        result = engine.select_master_type(
            2000, 600000, AOS_DEDICATED_MASTER_LIST, AOS_DEFAULT_MASTER_TYPE
        )
        assert result == AOS_DEFAULT_MASTER_TYPE
