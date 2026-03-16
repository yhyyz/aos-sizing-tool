import os
import json
import time
import hashlib
import logging
from typing import Optional, Dict, List, Any, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pandas as pd
import numpy as np

from util.ebs_limits import (
    AOS_EBS_LIMITS,
    AOS_OI2_NVME,
    EC2_EBS_LIMITS,
    EC2_VALID_FAMILIES,
    get_aos_ebs_limit,
    get_ec2_ebs_limit,
    get_aos_min_storage,
    get_ec2_min_storage,
)

logger = logging.getLogger(__name__)

BULK_API_BASE = "https://pricing.us-east-1.amazonaws.com"
AOS_REGION_INDEX_URL = (
    BULK_API_BASE + "/offers/v1.0/aws/AmazonES/current/region_index.json"
)
EC2_REGION_INDEX_URL = (
    BULK_API_BASE + "/offers/v1.0/aws/AmazonEC2/current/region_index.json"
)

CHINA_REGIONS = {"cn-north-1", "cn-northwest-1"}

AOS_VALID_PRODUCT_FAMILIES = {
    "Amazon OpenSearch Service Instance",
    "Amazon OpenSearch Service Volume",
}
AOS_VALID_VOLUME_STORAGE_MEDIA = {"GP3", "Managed-Storage"}

AOS_PRICING_COLUMNS = [
    "TermType",
    "PriceDescription",
    "EffectiveDate",
    "StartingRange",
    "EndingRange",
    "Unit",
    "PricePerUnit",
    "Currency",
    "LeaseContractLength",
    "PurchaseOption",
    "OfferingClass",
    "Product Family",
    "serviceCode",
    "Location",
    "Location Type",
    "Instance Type",
    "Current Generation",
    "Instance Family",
    "vCPU",
    "Storage",
    "Storage Media",
    "usageType",
    "operation",
    "Compute type",
    "ECU",
    "Memory (GiB)",
    "Region Code",
    "serviceName",
]

EC2_PRICING_COLUMNS = [
    "TermType",
    "PriceDescription",
    "EffectiveDate",
    "Unit",
    "PricePerUnit",
    "Currency",
    "LeaseContractLength",
    "PurchaseOption",
    "OfferingClass",
    "Location",
    "Instance Type",
    "Instance Family",
    "vCPU",
    "Memory",
    "Storage",
    "Storage Media",
    "Network Performance",
    "Tenancy",
    "Operating System",
    "MarketOption",
    "Region Code",
]

INSTANCE_COLUMNS = [
    "INSTANCE_TYPE",
    "MIN_STORAGE",
    "MAX_STORAGE_GP3",
    "CPU",
    "MEMORY",
    "NVMe_SSD",
    "MAX_STORAGE_GP2",
]

WARM_INSTANCE_COLUMNS = ["INSTANCE_TYPE", "CPU", "MEMORY", "STORAGE"]


class LoadDataFromAPI:
    def __init__(self, cache_dir: Optional[str] = None, cache_ttl_hours: int = 24):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cache_dir = cache_dir or os.path.join(project_root, ".api_cache")
        self.cache_ttl_seconds = cache_ttl_hours * 3600
        os.makedirs(self.cache_dir, exist_ok=True)

        self._aos_region_data: List[dict] = []
        self._ec2_region_data: List[dict] = []

        self._fetch_all_data()
        self._aos_specs: Optional[Dict[str, Tuple[float, float]]] = None
        self.pricing_df = self.read_aos_pricing()

    def _cache_path(self, url: str) -> str:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.json")

    def _is_cache_valid(self, path: str) -> bool:
        if not os.path.exists(path):
            return False
        age = time.time() - os.path.getmtime(path)
        return age < self.cache_ttl_seconds

    def _fetch_json(self, url: str) -> dict:
        cache_file = self._cache_path(url)
        if self._is_cache_valid(cache_file):
            logger.debug("Cache hit: %s", url)
            with open(cache_file, "r") as f:
                return json.load(f)

        logger.info("Fetching: %s", url)
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        with open(cache_file, "w") as f:
            json.dump(data, f)
        return data

    def _fetch_ec2_filtered(self, url: str) -> dict:
        filtered_key = hashlib.md5((url + ":filtered").encode()).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"{filtered_key}.json")
        if self._is_cache_valid(cache_file):
            logger.debug("Cache hit (filtered EC2): %s", url)
            with open(cache_file, "r") as f:
                return json.load(f)

        logger.info("Fetching EC2 (will filter): %s", url)
        resp = requests.get(url, timeout=180)
        resp.raise_for_status()
        raw = resp.json()

        kept_skus: set = set()
        filtered_products: dict = {}
        for sku, prod in raw.get("products", {}).items():
            family = prod.get("productFamily", "")
            if family == "Storage":
                vol_api = prod.get("attributes", {}).get("volumeApiName", "")
                if vol_api in ("gp3", "st1"):
                    kept_skus.add(sku)
                    filtered_products[sku] = prod
            elif family == "Compute Instance":
                itype = prod.get("attributes", {}).get("instanceType", "")
                if itype and itype.split(".")[0] in EC2_VALID_FAMILIES:
                    kept_skus.add(sku)
                    filtered_products[sku] = prod

        filtered_terms: dict = {}
        for term_type in ("OnDemand", "Reserved"):
            src = raw.get("terms", {}).get(term_type, {})
            filtered_terms[term_type] = {
                sku: offers for sku, offers in src.items() if sku in kept_skus
            }

        data = {"products": filtered_products, "terms": filtered_terms}
        with open(cache_file, "w") as f:
            json.dump(data, f)

        raw_mb = len(json.dumps(raw)) / 1e6
        filtered_mb = os.path.getsize(cache_file) / 1e6
        logger.info(
            "EC2 filtered: %d/%d products kept, %.0fMB → %.1fMB",
            len(filtered_products),
            len(raw.get("products", {})),
            raw_mb,
            filtered_mb,
        )
        return data

    def _fetch_all_data(self):
        aos_index = self._fetch_json(AOS_REGION_INDEX_URL)
        aos_regions = {
            code: info["currentVersionUrl"]
            for code, info in aos_index.get("regions", {}).items()
            if code not in CHINA_REGIONS
        }

        logger.info("Fetching AOS pricing for %d regions...", len(aos_regions))
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {
                pool.submit(self._fetch_json, BULK_API_BASE + url): code
                for code, url in aos_regions.items()
            }
            for future in as_completed(futures):
                code = futures[future]
                try:
                    self._aos_region_data.append(future.result())
                except Exception:
                    logger.warning(
                        "Failed to fetch AOS data for %s", code, exc_info=True
                    )

        ec2_index = self._fetch_json(EC2_REGION_INDEX_URL)
        aos_region_codes = set(aos_regions.keys())
        ec2_regions = {
            code: info["currentVersionUrl"]
            for code, info in ec2_index.get("regions", {}).items()
            if code in aos_region_codes and code not in CHINA_REGIONS
        }

        logger.info("Fetching EC2 pricing for %d regions...", len(ec2_regions))
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {
                pool.submit(self._fetch_ec2_filtered, BULK_API_BASE + url): code
                for code, url in ec2_regions.items()
            }
            for future in as_completed(futures):
                code = futures[future]
                try:
                    self._ec2_region_data.append(future.result())
                except Exception:
                    logger.warning(
                        "Failed to fetch EC2 data for %s", code, exc_info=True
                    )

        logger.info(
            "Data fetch complete: %d AOS regions, %d EC2 regions",
            len(self._aos_region_data),
            len(self._ec2_region_data),
        )

    # ------------------------------------------------------------------
    # AOS Pricing
    # ------------------------------------------------------------------

    def read_aos_pricing(self) -> pd.DataFrame:
        rows: List[dict] = []
        for region_data in self._aos_region_data:
            products = region_data.get("products", {})
            terms = region_data.get("terms", {})

            filtered_products: Dict[str, dict] = {}
            for sku, prod in products.items():
                family = prod.get("productFamily", "")
                if family not in AOS_VALID_PRODUCT_FAMILIES:
                    continue
                attrs = prod.get("attributes", {})
                if family == "Amazon OpenSearch Service Volume":
                    if (
                        attrs.get("storageMedia", "")
                        not in AOS_VALID_VOLUME_STORAGE_MEDIA
                    ):
                        continue
                filtered_products[sku] = prod

            for sku, prod in filtered_products.items():
                attrs = prod.get("attributes", {})
                base = self._build_aos_product_base(prod)

                for term_type in ("OnDemand", "Reserved"):
                    sku_terms = terms.get(term_type, {}).get(sku, {})
                    for offer_key, offer in sku_terms.items():
                        term_attrs = offer.get("termAttributes", {})
                        effective_date = offer.get("effectiveDate", "")
                        for dim_key, dim in offer.get("priceDimensions", {}).items():
                            row = dict(base)
                            row["TermType"] = term_type
                            row["EffectiveDate"] = effective_date
                            row["PriceDescription"] = dim.get("description", "")
                            row["Unit"] = dim.get("unit", "")
                            row["Currency"] = "USD"

                            price_str = dim.get("pricePerUnit", {}).get("USD", "0")
                            row["PricePerUnit"] = float(price_str) if price_str else 0.0

                            begin = dim.get("beginRange", "0")
                            row["StartingRange"] = float(begin) if begin else 0.0

                            end = dim.get("endRange", "Inf")
                            row["EndingRange"] = (
                                float("inf") if end == "Inf" else float(end)
                            )

                            if term_type == "Reserved":
                                row["LeaseContractLength"] = term_attrs.get(
                                    "LeaseContractLength", np.nan
                                )
                                row["PurchaseOption"] = term_attrs.get(
                                    "PurchaseOption", np.nan
                                )
                                row["OfferingClass"] = term_attrs.get(
                                    "OfferingClass", np.nan
                                )
                            else:
                                row["LeaseContractLength"] = np.nan
                                row["PurchaseOption"] = np.nan
                                row["OfferingClass"] = np.nan

                            rows.append(row)

        df = pd.DataFrame(rows, columns=AOS_PRICING_COLUMNS)
        logger.info("AOS pricing DataFrame: %d rows", len(df))
        return df

    @staticmethod
    def _build_aos_product_base(prod: dict) -> dict:
        attrs = prod.get("attributes", {})
        vcpu_str = attrs.get("vcpu", "")
        mem_str = attrs.get("memoryGib", "")
        return {
            "Product Family": prod.get("productFamily", ""),
            "serviceCode": attrs.get("servicecode", ""),
            "Location": attrs.get("location", ""),
            "Location Type": attrs.get("locationType", ""),
            "Instance Type": attrs.get("instanceType", np.nan),
            "Current Generation": attrs.get("currentGeneration", np.nan),
            "Instance Family": attrs.get("instanceFamily", np.nan),
            "vCPU": float(vcpu_str) if vcpu_str else np.nan,
            "Storage": attrs.get("storage", np.nan),
            "Storage Media": attrs.get("storageMedia", np.nan) or np.nan,
            "usageType": attrs.get("usagetype", ""),
            "operation": attrs.get("operation", ""),
            "Compute type": attrs.get("computeType", np.nan) or np.nan,
            "ECU": attrs.get("ecu", np.nan) or np.nan,
            "Memory (GiB)": float(mem_str) if mem_str else np.nan,
            "Region Code": attrs.get("regionCode", ""),
            "serviceName": attrs.get("servicename", ""),
        }

    # ------------------------------------------------------------------
    # AOS Hot Instance
    # ------------------------------------------------------------------

    def read_aos_hot_instance(self) -> pd.DataFrame:
        specs = self._collect_aos_instance_specs()
        rows: List[dict] = []
        for itype in sorted(AOS_EBS_LIMITS.keys()):
            if itype not in specs:
                continue
            vcpu, mem = specs[itype]
            rows.append(
                {
                    "INSTANCE_TYPE": itype,
                    "MIN_STORAGE": get_aos_min_storage(itype),
                    "MAX_STORAGE_GP3": get_aos_ebs_limit(itype),
                    "CPU": int(vcpu),
                    "MEMORY": int(mem),
                    "NVMe_SSD": np.nan,
                    "MAX_STORAGE_GP2": np.nan,
                }
            )
        for itype, nvme_gb in sorted(AOS_OI2_NVME.items()):
            if itype not in specs:
                continue
            vcpu, mem = specs[itype]
            rows.append(
                {
                    "INSTANCE_TYPE": itype,
                    "MIN_STORAGE": get_aos_min_storage(itype),
                    "MAX_STORAGE_GP3": nvme_gb,
                    "CPU": int(vcpu),
                    "MEMORY": int(mem),
                    "NVMe_SSD": nvme_gb,
                    "MAX_STORAGE_GP2": np.nan,
                }
            )
        df = pd.DataFrame(rows, columns=INSTANCE_COLUMNS)
        logger.info("AOS hot instance DataFrame: %d rows", len(df))
        return df

    # ------------------------------------------------------------------
    # AOS Warm Instance
    # ------------------------------------------------------------------

    def read_aos_warm_instance(self) -> pd.DataFrame:
        specs = self._collect_aos_instance_specs()
        rows: List[dict] = []
        for itype, (vcpu, mem) in sorted(specs.items()):
            if not itype.startswith("ultrawarm1."):
                continue
            storage_raw = self._get_ultrawarm_storage(itype)
            rows.append(
                {
                    "INSTANCE_TYPE": itype,
                    "CPU": int(vcpu),
                    "MEMORY": float(mem),
                    "STORAGE": storage_raw,
                }
            )
        for itype, nvme_gb in sorted(AOS_OI2_NVME.items()):
            if itype not in specs:
                continue
            vcpu, mem = specs[itype]
            rows.append(
                {
                    "INSTANCE_TYPE": itype,
                    "CPU": int(vcpu),
                    "MEMORY": float(mem),
                    "STORAGE": nvme_gb,
                }
            )
        df = pd.DataFrame(rows, columns=WARM_INSTANCE_COLUMNS)
        logger.info("AOS warm instance DataFrame: %d rows", len(df))
        return df

    def _get_ultrawarm_storage(self, itype: str) -> int:
        for region_data in self._aos_region_data:
            for sku, prod in region_data.get("products", {}).items():
                attrs = prod.get("attributes", {})
                if attrs.get("instanceType") == itype:
                    storage_str = attrs.get("storage", "0")
                    try:
                        tb_val = float(storage_str)
                        return int(tb_val * 1024)
                    except (ValueError, TypeError):
                        pass
        return 0

    def _collect_aos_instance_specs(self) -> Dict[str, Tuple[float, float]]:
        if self._aos_specs is not None:
            return self._aos_specs
        specs: Dict[str, Tuple[float, float]] = {}
        for region_data in self._aos_region_data:
            for sku, prod in region_data.get("products", {}).items():
                if prod.get("productFamily") != "Amazon OpenSearch Service Instance":
                    continue
                attrs = prod.get("attributes", {})
                itype = attrs.get("instanceType", "")
                if not itype or itype in specs:
                    continue
                vcpu_str = attrs.get("vcpu", "")
                mem_str = attrs.get("memoryGib", "")
                if vcpu_str and mem_str:
                    specs[itype] = (float(vcpu_str), float(mem_str))
        self._aos_specs = specs
        return specs

    # ------------------------------------------------------------------
    # EC2 Pricing
    # ------------------------------------------------------------------

    def read_ec2_pricing(self) -> pd.DataFrame:
        rows: List[dict] = []
        for region_data in self._ec2_region_data:
            products = region_data.get("products", {})
            terms = region_data.get("terms", {})

            filtered_skus: Dict[str, dict] = {}
            for sku, prod in products.items():
                family = prod.get("productFamily", "")
                attrs = prod.get("attributes", {})

                if family == "Compute Instance":
                    itype = attrs.get("instanceType", "")
                    if not itype or itype.split(".")[0] not in EC2_VALID_FAMILIES:
                        continue
                    if attrs.get("tenancy") != "Shared":
                        continue
                    if attrs.get("operatingSystem") != "Linux":
                        continue
                    if attrs.get("preInstalledSw") != "NA":
                        continue
                    if attrs.get("capacitystatus") != "Used":
                        continue
                    filtered_skus[sku] = prod

                elif family == "Storage":
                    vol_api = attrs.get("volumeApiName", "")
                    if vol_api not in ("gp3", "st1"):
                        continue
                    filtered_skus[sku] = prod

            for sku, prod in filtered_skus.items():
                attrs = prod.get("attributes", {})
                base = self._build_ec2_product_base(prod)

                for term_type in ("OnDemand", "Reserved"):
                    sku_terms = terms.get(term_type, {}).get(sku, {})
                    for offer_key, offer in sku_terms.items():
                        term_attrs = offer.get("termAttributes", {})
                        effective_date = offer.get("effectiveDate", "")
                        for dim_key, dim in offer.get("priceDimensions", {}).items():
                            row = dict(base)
                            row["TermType"] = term_type
                            row["EffectiveDate"] = effective_date
                            row["PriceDescription"] = dim.get("description", "")
                            row["Unit"] = dim.get("unit", "")
                            row["Currency"] = "USD"

                            price_str = dim.get("pricePerUnit", {}).get("USD", "0")
                            row["PricePerUnit"] = float(price_str) if price_str else 0.0

                            if term_type == "Reserved":
                                row["LeaseContractLength"] = term_attrs.get(
                                    "LeaseContractLength", np.nan
                                )
                                row["PurchaseOption"] = term_attrs.get(
                                    "PurchaseOption", np.nan
                                )
                                row["OfferingClass"] = term_attrs.get(
                                    "OfferingClass", np.nan
                                )
                            else:
                                row["LeaseContractLength"] = np.nan
                                row["PurchaseOption"] = np.nan
                                row["OfferingClass"] = np.nan

                            rows.append(row)

        df = pd.DataFrame(rows, columns=EC2_PRICING_COLUMNS)
        logger.info("EC2 pricing DataFrame: %d rows", len(df))
        return df

    @staticmethod
    def _build_ec2_product_base(prod: dict) -> dict:
        attrs = prod.get("attributes", {})
        family = prod.get("productFamily", "")
        is_storage = family == "Storage"
        vcpu_str = attrs.get("vcpu", "")
        return {
            "Location": attrs.get("location", ""),
            "Instance Type": np.nan
            if is_storage
            else attrs.get("instanceType", np.nan),
            "Instance Family": np.nan
            if is_storage
            else attrs.get("instanceFamily", np.nan),
            "vCPU": np.nan if is_storage else (float(vcpu_str) if vcpu_str else np.nan),
            "Memory": np.nan if is_storage else attrs.get("memory", np.nan),
            "Storage": np.nan if is_storage else attrs.get("storage", np.nan),
            "Storage Media": attrs.get("storageMedia", np.nan)
            if is_storage
            else np.nan,
            "Network Performance": np.nan
            if is_storage
            else attrs.get("networkPerformance", np.nan),
            "Tenancy": np.nan if is_storage else attrs.get("tenancy", np.nan),
            "Operating System": np.nan
            if is_storage
            else attrs.get("operatingSystem", np.nan),
            "MarketOption": np.nan if is_storage else attrs.get("marketoption", np.nan),
            "Region Code": attrs.get("regionCode", ""),
        }

    # ------------------------------------------------------------------
    # EC2 Instance
    # ------------------------------------------------------------------

    def read_ec2_instance(self) -> pd.DataFrame:
        specs = self._collect_ec2_instance_specs()
        rows: List[dict] = []
        for itype in sorted(EC2_EBS_LIMITS.keys()):
            if itype not in specs:
                continue
            vcpu, mem_gib = specs[itype]
            rows.append(
                {
                    "INSTANCE_TYPE": itype,
                    "MIN_STORAGE": get_ec2_min_storage(itype),
                    "MAX_STORAGE_GP3": get_ec2_ebs_limit(itype),
                    "CPU": int(vcpu),
                    "MEMORY": int(mem_gib),
                    "NVMe_SSD": np.nan,
                    "MAX_STORAGE_GP2": np.nan,
                }
            )
        df = pd.DataFrame(rows, columns=INSTANCE_COLUMNS)
        logger.info("EC2 instance DataFrame: %d rows", len(df))
        return df

    def _collect_ec2_instance_specs(self) -> Dict[str, Tuple[float, float]]:
        specs: Dict[str, Tuple[float, float]] = {}
        for region_data in self._ec2_region_data:
            for sku, prod in region_data.get("products", {}).items():
                if prod.get("productFamily") != "Compute Instance":
                    continue
                attrs = prod.get("attributes", {})
                itype = attrs.get("instanceType", "")
                if itype not in set(EC2_EBS_LIMITS.keys()) or itype in specs:
                    continue
                vcpu_str = attrs.get("vcpu", "")
                mem_str = attrs.get("memory", "")  # e.g. "8 GiB"
                if vcpu_str and mem_str:
                    mem_val = float(
                        mem_str.replace(" GiB", "").replace(",", "").strip()
                    )
                    specs[itype] = (float(vcpu_str), mem_val)
        return specs

    # ------------------------------------------------------------------
    # List helpers
    # ------------------------------------------------------------------

    def get_aws_region_list_from_pricing(self) -> list:
        region_list = self.pricing_df["Location"].unique().tolist()
        if "Africa (Cape Town)" in region_list:
            region_list.remove("Africa (Cape Town)")
        region_list.sort()
        return region_list

    def get_purchase_option_list_from_pricing(self) -> list:
        purchase_list = self.pricing_df["PurchaseOption"].unique().tolist()
        purchase_list = [
            x
            for x in purchase_list
            if x is not np.nan and not (isinstance(x, float) and np.isnan(x))
        ]
        purchase_list.sort()
        return ["OD"] + purchase_list

    def get_term_list_from_pricing(self) -> list:
        term_list = self.pricing_df["LeaseContractLength"].unique().tolist()
        term_list = [
            x
            for x in term_list
            if x is not np.nan and not (isinstance(x, float) and np.isnan(x))
        ]
        term_list.sort()
        return ["0yr"] + term_list
