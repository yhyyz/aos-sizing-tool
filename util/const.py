
class Const:
    COMPRESSION_RATIO = 0.4
    MIN_WARM_NODE = 2
    AOS_INDEX_OVERHEAD = 0.1
    LINUX_RESERVED_SPACE = 0.05
    DISK_WATERMARK_THRESHOLD = 0.2
    AOS_OVERHEAD = 0.2
    AOS_OVERHEAD_MAX_GB = 20
    SHARDS_NUM_PER_GB_JVM = 20
    MAX_INSTANCES_PER_DOMAIN = 200
    MAX_INSTANCES_PER_DOMAIN_FOR_217_AZ1 = 334
    MAX_INSTANCES_PER_DOMAIN_FOR_217_AZ2 = 668
    MAX_INSTANCES_PER_DOMAIN_FOR_217_AZ3 = 1002

    MAX_INSTANCES_PER_DOMAIN_FOR_HOT_NOT_OR1_XLARGE_ABOVE = 400



    MAX_WARM_INSTANCES_PER_DOMAIN = 150
    MAX_WARM_INSTANCES_PER_DOMAIN_FOR_217_AZ1 = 250
    MAX_WARM_INSTANCES_PER_DOMAIN_FOR_217_AZ2 = 500
    MAX_WARM_INSTANCES_PER_DOMAIN_FOR_217_AZ3 = 750

    # MAX_STORAGE_TB_PER_DOMAIN = 3072
    BEST_PRACTICE_SINGLE_SHARD_SIZE_FOR_LOG = 50
    BEST_PRACTICE_SINGLE_CPU_SHARD = 1.5  # 0.67
    HOT_TO_WARM_DISK_OVERHEAD = 3
    HOT_TO_WARM_MAX_INDEX_SIZE = 300  # GB
    # WRITE_THROUGHPUT = {
    #     "r6g.large.search": 6,  # 12 * 0.5
    #     "r6g.xlarge.search": 11,  # 18* 0.6
    #     "r6g.2xlarge.search": 18,
    #     "r6g.4xlarge.search": 25,  # 18 * 1.4
    #     "r6g.8xlarge.search": 35,  # cpu=65% 25000 cpu=90% 25000*1.38=35
    #     "r6g.12xlarge.search": 57,  # cpu=60% 38000 cpu=90% 38000*1.5=57
    #
    #     "c6g.large.search": 5,  # 9 * 0.5
    #     "c6g.xlarge.search": 8,  # 13 * 0.6
    #     "c6g.2xlarge.search": 13,  # 19/1.5
    #     "c6g.4xlarge.search": 19,  # 13 * 1.5
    #     "c6g.8xlarge.search": 27,  # 19 * 1.4
    #     "c6g.12xlarge.search": 43,  # 27*1.6
    #
    #     "m6g.large.search": (5+6)/2,  # 9 * 0.5
    #     "m6g.xlarge.search": (8+11)/2,  # 13 * 0.6
    #     "m6g.2xlarge.search": (13+18)/2,  # 19/1.5
    #     "m6g.4xlarge.search": (19+25)/2,  # 13 * 1.5
    #     "m6g.8xlarge.search": (27+35)/2,  # 19 * 1.4
    #     "m6g.12xlarge.search": (57+43)/2,  # 27*1.6
    # }
    WRITE_THROUGHPUT = {
        # "c6g.large.search": 5,  # 8 * 0.6
        # "c6g.xlarge.search": 8,  # 14 * 0.6
        # "c6g.2xlarge.search": 14,  # cpu=75% index_rate= 14MB/S
        # "c6g.4xlarge.search": 18,  # cpu=47% index_rate= 18MB/S
        # "c6g.8xlarge.search": 27,  # 18 * 1.5 = 27
        # "c6g.12xlarge.search": 34,  # 23 * 1.25 = 34
        #
        # "m6g.large.search": 6,  # 9/1.5
        # "m6g.xlarge.search": 9,  # 14 / 1.5
        # "m6g.2xlarge.search": 14,  # cpu=76% index_rate= 14MB/S => cpu=75% index_rate= 14MB/S
        # "m6g.4xlarge.search": 21,  # cpu=52% index_rate= 21MB/S
        # "m6g.8xlarge.search": 32,  # 21 * 1.5
        # "m6g.12xlarge.search": 40, # 32 * 1.25
        #
        # "r6g.large.search": 6 ,  # 10/1.53
        # "r6g.xlarge.search": 10,  # 15/1.53
        # "r6g.2xlarge.search": 15,  # cpu=75% index_rate= 15MB/S
        # "r6g.4xlarge.search": 23,  # cpu=57% index_rate= 23MB/S
        # "r6g.8xlarge.search": 35,  # 23 * 1.53
        # "r6g.12xlarge.search": 44, # 35 * 1.26

        # 7 相比6 官方提升25%，这里按照15算
        "c7g.large.search": 5*1.15,  # 8 * 0.6
        "c7g.xlarge.search": 8*1.15,  # 14 * 0.6
        "c7g.2xlarge.search": 14*1.15,  # cpu=75% index_rate= 14MB/S
        "c7g.4xlarge.search": 18*1.15,  # cpu=47% index_rate= 18MB/S
        "c7g.8xlarge.search": 27*1.15,  # 18 * 1.5 = 27
        "c7g.12xlarge.search": 34*1.15,  # 23 * 1.25 = 34
        "c7g.16xlarge.search": 38*1.15,  # 34 * 1.12 = 38

        "m7g.medium.search": 4*1.15, # 6/1.5
        "m7g.large.search": 6*1.15,  # 9/1.5
        "m7g.xlarge.search": 9*1.15,  # 14 / 1.5
        "m7g.2xlarge.search": 14*1.15,  # cpu=76% index_rate= 14MB/S => cpu=75% index_rate= 14MB/S
        "m7g.4xlarge.search": 21*1.15,  # cpu=52% index_rate= 21MB/S
        "m7g.8xlarge.search": 32*1.15,  # 21 * 1.5
        "m7g.12xlarge.search": 40*1.15,  # 32 * 1.25
        "m7g.16xlarge.search": 45*1.15, #  40 * 1.12

        "r7g.medium.search": 4*1.15, # 6/1.53
        "r7g.large.search": 6*1.15,  # 10/1.53
        "r7g.xlarge.search": 10*1.15,  # 15/1.53
        "r7g.2xlarge.search": 15*1.15,  # cpu=75% index_rate= 15MB/S
        "r7g.4xlarge.search": 23*1.15,  # cpu=57% index_rate= 23MB/S
        "r7g.8xlarge.search": 35*1.15,  # 23 * 1.53
        "r7g.12xlarge.search": 44*1.15,  # 35 * 1.26
        "r7g.16xlarge.search": 50*1.15, # 44 * 1.13

        # or1提升30%性能相比r6g
        "or1.medium.search": 5,  # 6/1.53 * 1.3
        "or1.large.search": 8,  # 10/1.53 * 1.3
        "or1.xlarge.search": 13,  # 15/1.53 * 1.3
        "or1.2xlarge.search": 20,  # cpu=75% index_rate= 15MB/S * 1.3
        "or1.4xlarge.search": 30,  # cpu=57% index_rate= 23MB/S * 1.3
        "or1.8xlarge.search": 46,  # 23 * 1.53 * 1.3
        "or1.12xlarge.search": 57,  # 35 * 1.26 * 1.3
        "or1.16xlarge.search": 65,  # 44 * 1.13 * 1.3

    }
    # EC2_WRITE_THROUGHPUT = {
    #     "r6g.large": 6,  # 12 * 0.5
    #     "r6g.xlarge": 11,  # 18* 0.6
    #     "r6g.2xlarge": 18,
    #     "r6g.4xlarge": 25,  # 18 * 1.4
    #     "r6g.8xlarge": 35,  # cpu=65% 25000 cpu=90% 25000*1.38=35
    #     "r6g.12xlarge": 57,  # cpu=60% 38000 cpu=90% 38000*1.5=57
    #
    #     "c6g.large": 5,  # 9 * 0.5
    #     "c6g.xlarge": 8,  # 13 * 0.6
    #     "c6g.2xlarge": 13,  # 19/1.5
    #     "c6g.4xlarge": 19,  # 13 * 1.5
    #     "c6g.8xlarge": 27,  # 19 * 1.4
    #     "c6g.12xlarge": 43,  # 27*1.6
    #
    #     "m6g.large": (5 + 6) / 2,  # 9 * 0.5
    #     "m6g.xlarge": (8 + 11) / 2,  # 13 * 0.6
    #     "m6g.2xlarge": (13 + 18) / 2,  # 19/1.5
    #     "m6g.4xlarge": (19 + 25) / 2,  # 13 * 1.5
    #     "m6g.8xlarge": (27 + 35) / 2,  # 19 * 1.4
    #     "m6g.12xlarge": (57 + 43) / 2,  # 27*1.6
    # }
    EC2_WRITE_THROUGHPUT = {
        # "c6g.large": 8,  # 7 * 0.5
        # "c6g.xlarge": 11,  # 14 / 1.3
        # "c6g.2xlarge": 14,  # cpu=75% index_rate= 14MB/S
        # "c6g.4xlarge": 18,  # cpu=47% index_rate= 18MB/S
        # "c6g.8xlarge": 23,  # 18 * 1.3 = 23
        # "c6g.12xlarge": 27,  # 23 * 1.17 = 27
        #
        # "m6g.large": 6,  # 7 * 0.5
        # "m6g.xlarge": 9,  # 14 / 1.5
        # "m6g.2xlarge": 14,  # cpu=76% index_rate= 14MB/S => cpu=75% index_rate= 14MB/S
        # "m6g.4xlarge": 21,  # cpu=52% index_rate= 21MB/S
        # "m6g.8xlarge": 32,  # 21 * 1.5
        # "m6g.12xlarge": 40, # 32 * 1.25
        #
        # "r6g.large": 6,  # 10/1.53
        # "r6g.xlarge": 10,  # 15/1.53
        # "r6g.2xlarge": 15,  # cpu=75% index_rate= 15MB/S
        # "r6g.4xlarge": 23,  # cpu=57% index_rate= 23MB/S
        # "r6g.8xlarge": 35,  # 23 * 1.53
        # "r6g.12xlarge": 44, # 35 * 1.26

        # 7 相比6 官方提升25%，这里按照15算
        "c7g.large": 5 * 1.15,  # 8 * 0.6
        "c7g.xlarge": 8 * 1.15,  # 14 * 0.6
        "c7g.2xlarge": 14 * 1.15,  # cpu=75% index_rate= 14MB/S
        "c7g.4xlarge": 18 * 1.15,  # cpu=47% index_rate= 18MB/S
        "c7g.8xlarge": 27 * 1.15,  # 18 * 1.5 = 27
        "c7g.12xlarge": 34 * 1.15,  # 23 * 1.25 = 34
        "c7g.16xlarge": 38 * 1.15,  # 34 * 1.12 = 38

        "m7g.medium": 4 * 1.15,  # 6/1.5
        "m7g.large": 6 * 1.15,  # 9/1.5
        "m7g.xlarge": 9 * 1.15,  # 14 / 1.5
        "m7g.2xlarge": 14 * 1.15,  # cpu=76% index_rate= 14MB/S => cpu=75% index_rate= 14MB/S
        "m7g.4xlarge": 21 * 1.15,  # cpu=52% index_rate= 21MB/S
        "m7g.8xlarge": 32 * 1.15,  # 21 * 1.5
        "m7g.12xlarge": 40 * 1.15,  # 32 * 1.25
        "m7g.16xlarge": 45 * 1.15,  # 40 * 1.12

        "r7g.medium": 4 * 1.15,  # 6/1.53
        "r7g.large": 6 * 1.15,  # 10/1.53
        "r7g.xlarge": 10 * 1.15,  # 15/1.53
        "r7g.2xlarge": 15 * 1.15,  # cpu=75% index_rate= 15MB/S
        "r7g.4xlarge": 23 * 1.15,  # cpu=57% index_rate= 23MB/S
        "r7g.8xlarge": 35 * 1.15,  # 23 * 1.53
        "r7g.12xlarge": 44 * 1.15,  # 35 * 1.26
        "r7g.16xlarge": 50 * 1.15,  # 44 * 1.13

        "or1.medium": 4 * 1.15,  # 6/1.53
        "or1.large": 6 * 1.15,  # 10/1.53
        "or1.xlarge": 10 * 1.15,  # 15/1.53
        "or1.2xlarge": 15 * 1.15,  # cpu=75% index_rate= 15MB/S
        "or1.4xlarge": 23 * 1.15,  # cpu=57% index_rate= 23MB/S
        "or1.8xlarge": 35 * 1.15,  # 23 * 1.53
        "or1.12xlarge": 44 * 1.15,  # 35 * 1.26
        "or1.16xlarge": 50 * 1.15,  # 44 * 1.13
    }
    DEDICATED_MASTER_LIST = [
        # {"instance_count": "1-10", "max_shard_support": 10 * 1000, "instance_type": "r6g.large.search"},
        # {"instance_count": "11-30", "max_shard_support": 30 * 1000, "instance_type": "r6g.xlarge.search"},
        # {"instance_count": "31-75", "max_shard_support": 40 * 1000, "instance_type": "r6g.xlarge.search"},
        # {"instance_count": "76-125", "max_shard_support": 75 * 1000, "instance_type": "r6g.2xlarge.search"},
        # {"instance_count": "126-200", "max_shard_support": 75 * 1000, "instance_type": "r6g.4xlarge.search"},

        # {"instance_count": "1-10", "max_shard_support": 10 * 1000, "instance_type": "m6g.large.search"},
        # {"instance_count": "11-30", "max_shard_support": 30 * 1000, "instance_type": "m6g.xlarge.search"},
        # {"instance_count": "31-75", "max_shard_support": 40 * 1000, "instance_type": "r6g.xlarge.search"},
        # {"instance_count": "76-125", "max_shard_support": 75 * 1000, "instance_type": "r6g.2xlarge.search"},
        # {"instance_count": "126-200", "max_shard_support": 75 * 1000, "instance_type": "r6g.4xlarge.search"},

        {"instance_count": "1-30", "max_shard_support": 15 * 1000, "instance_type": "m7g.large.search"},
        {"instance_count": "30-60", "max_shard_support": 30 * 1000, "instance_type": "m7g.xlarge.search"},
        {"instance_count": "60-120", "max_shard_support": 60 * 1000, "instance_type": "r7g.xlarge.search"},
        {"instance_count": "120-240", "max_shard_support": 120 * 1000, "instance_type": "r7g.2xlarge.search"},
        {"instance_count": "240-480", "max_shard_support": 240 * 1000, "instance_type": "r7g.4xlarge.search"},
        {"instance_count": "480-1002", "max_shard_support": 500 * 1000, "instance_type": "r7g.8xlarge.search"},

    ]

    EC2_MASTER_LIST = [
        # {"instance_count": "1-10", "max_shard_support": 10 * 1000, "instance_type": "r6g.large.search"},
        # {"instance_count": "11-30", "max_shard_support": 30 * 1000, "instance_type": "r6g.xlarge.search"},
        # {"instance_count": "31-75", "max_shard_support": 40 * 1000, "instance_type": "r6g.xlarge.search"},
        # {"instance_count": "76-125", "max_shard_support": 75 * 1000, "instance_type": "r6g.2xlarge.search"},
        # {"instance_count": "126-200", "max_shard_support": 75 * 1000, "instance_type": "r6g.4xlarge.search"},

        # {"instance_count": "1-10", "max_shard_support": 10 * 1000, "instance_type": "m6g.large"},
        # {"instance_count": "11-30", "max_shard_support": 30 * 1000, "instance_type": "m6g.xlarge"},
        # {"instance_count": "31-75", "max_shard_support": 40 * 1000, "instance_type": "r6g.xlarge"},
        # {"instance_count": "76-125", "max_shard_support": 75 * 1000, "instance_type": "r6g.2xlarge"},
        # {"instance_count": "126-200", "max_shard_support": 75 * 1000, "instance_type": "r6g.4xlarge"},


        {"instance_count": "1-30", "max_shard_support": 15 * 1000, "instance_type": "m7g.large"},
        {"instance_count": "30-60", "max_shard_support": 30 * 1000, "instance_type": "m7g.xlarge"},
        {"instance_count": "60-120", "max_shard_support": 60 * 1000, "instance_type": "r7g.xlarge"},
        {"instance_count": "120-240", "max_shard_support": 120 * 1000, "instance_type": "r7g.2xlarge"},
        {"instance_count": "240-480", "max_shard_support": 240 * 1000, "instance_type": "r7g.4xlarge"},
        {"instance_count": "480-1002", "max_shard_support": 500 * 1000, "instance_type": "r7g.8xlarge"},

    ]
