"""
V2 API 路由

新 API 端点：
  POST /v2/sizing/aos          — AOS 托管 OpenSearch sizing + pricing
  POST /v2/sizing/ec2          — EC2 自建 ES sizing + pricing
  GET  /v2/regions             — 可用 region 列表
  GET  /v2/instance-families   — 已注册机型家族列表（方便前端展示）

旧 API 保持不变，由 app.py 直接处理。
"""

import pandas as pd
from typing import Any, List, Optional
from fastapi import APIRouter, Request
from v2.models.request import SizingRequest, EC2SizingRequest
from v2.solution.aos_solution import AOSSolution
from v2.solution.ec2_solution import EC2Solution
from util.ebs_limits import resolve_ec2_instance_type, is_aos_specific_family

router = APIRouter(prefix="/v2", tags=["v2"])

_data: dict[str, Any] = {}


def init_data(
    pricing_df: pd.DataFrame,
    hot_df: pd.DataFrame,
    warm_df: pd.DataFrame,
    ec2_pricing_df: pd.DataFrame,
    ec2_instance_df: pd.DataFrame,
    region_list: list,
):
    global _data
    _data = {
        "pricing_df": pricing_df,
        "hot_df": hot_df,
        "warm_df": warm_df,
        "ec2_pricing_df": ec2_pricing_df,
        "ec2_instance_df": ec2_instance_df,
        "region_list": region_list,
    }


def _apply_filter(res_list: list, filter_data: str) -> list:
    if not filter_data:
        return res_list

    parts = filter_data.split("-")
    hot_families = parts[0].split(",") if len(parts) > 0 and parts[0] else []
    hot_sizes = parts[1].split(",") if len(parts) > 1 and parts[1] else []
    warm_sizes = parts[2].split(",") if len(parts) > 2 and parts[2] else []

    if not hot_families and not hot_sizes and not warm_sizes:
        return res_list

    filtered = []
    for item in res_list:
        inst_parts = item.get("INSTANCE_TYPE", "").split(".")
        warm_parts = item.get("WARM_INSTANCE_TYPE", "").split(".")
        h_family = inst_parts[0] if len(inst_parts) > 0 else ""
        h_size = inst_parts[1] if len(inst_parts) > 1 else ""
        w_size = warm_parts[1] if len(warm_parts) > 1 else ""

        match = True
        if hot_families and h_family not in hot_families:
            match = False
        if hot_sizes and h_size not in hot_sizes:
            match = False
        if warm_sizes and w_size not in warm_sizes:
            match = False

        if match:
            filtered.append(item)

    return filtered


def _paginate(items: list, page_size: int, page: int) -> tuple:
    total_pages = max(1, (len(items) + page_size - 1) // page_size)
    start = (page - 1) * page_size
    end = page * page_size
    return items[start:end], total_pages


@router.post("/sizing/aos")
async def aos_sizing(request: Request, params: SizingRequest):
    solution = AOSSolution(
        _data["pricing_df"], _data["hot_df"], _data["warm_df"], params
    )
    res_list = solution.solve()

    return {
        "code": 200,
        "result": {
            "list": res_list,
        },
    }


@router.post("/sizing/ec2")
async def ec2_sizing(request: Request, params: EC2SizingRequest):
    req = params.model_copy()

    if is_aos_specific_family(req.reqEC2Instance):
        req.reqEC2Instance = resolve_ec2_instance_type(req.reqEC2Instance)

    solution = EC2Solution(_data["ec2_pricing_df"], _data["ec2_instance_df"], req)
    data = solution.solve()

    return {"code": 200, "result": {"list": [data]}}


@router.get("/regions")
async def region_list():
    return {"code": 200, "result": {"list": _data["region_list"]}}


@router.get("/instance-families")
async def instance_families():
    from v2.config.instance_families import AOS_FAMILIES, EC2_FAMILIES

    aos = []
    for name, f in AOS_FAMILIES.items():
        aos.append(
            {
                "name": f.name,
                "is_optimized": f.is_optimized,
                "storage_backend": f.storage_backend.value,
                "available_sizes": f.available_sizes,
                "supported_warm_architectures": [
                    a.value for a in f.supported_warm_architectures
                ],
                "has_throughput_data": bool(f.write_throughput),
            }
        )

    ec2 = []
    for name, f in EC2_FAMILIES.items():
        ec2.append(
            {
                "name": f.name,
                "is_optimized": f.is_optimized,
                "storage_backend": f.storage_backend.value,
                "available_sizes": f.available_sizes,
                "has_throughput_data": bool(f.write_throughput),
            }
        )

    return {"code": 200, "result": {"aos": aos, "ec2": ec2}}
