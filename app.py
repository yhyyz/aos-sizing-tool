import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uuid
import time
import api
from model.LogAnalytics import LogAnalyticsRequest, EC2LogAnalyticsRequest
from util.load_execl_data import LoadDataFromExcel
from sizing.AOSLogAnalyticsSolution import AOSLogAnalyticsSolution
from sizing.ESEC2LogAnalyticsSolution import ESEC2LogAnalyticsSolution
import hashlib
import datetime
from fastapi import FastAPI, File, UploadFile

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')
ASSETS_DIR = os.path.join(DIST_DIR, 'assets')
CONF_DIR = os.path.join(DIST_DIR, 'config')
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
# app.mount("/config", StaticFiles(directory=CONF_DIR), name="config")
templates = Jinja2Templates(directory=DIST_DIR)


async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        return JSONResponse(content={"code": 500, "error": {"message": f"{type(exc)} {exc}"}})


app.middleware('http')(catch_exceptions_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



lf = LoadDataFromExcel()
price_df = lf.read_aos_pricing()
hot_df = lf.read_aos_hot_instance()
warm_df = lf.read_aos_warm_instance()
purchase_list = lf.get_purchase_option_list_from_pricing()
term_list = lf.get_term_list_from_pricing()
ec2_df = lf.read_ec2_instance()
ec2_price_df = lf.read_ec2_pricing()

@app.get("/", response_class=HTMLResponse)
async def root():
    return templates.TemplateResponse("index.html", {"request": {}})

def pagination(list,page_size, page_num):
    # page_size = 3  # 每页显示3条数据
    # page_num = 2

    # 获取总页数
    total_page = int(len(list)/page_size)
    if len(list) % page_size != 0:
        total_page = total_page + 1
    # 获取第page_num页的数据
    start = (page_num - 1) * page_size
    end = page_num * page_size
    page_data = list[start:end]
    return page_data, total_page
@app.post("/provisioned/log_analytics_sizing")
async def log_analytics_sizing(request: Request, queryParams: LogAnalyticsRequest):
    # xxxx = request.headers.get('xxxx')
    print(queryParams.dict())
    # asos = AOSSizing(queryParams.sourceDataSize, queryParams.dailyDataSize, queryParams.hotDays, queryParams.warmDays,
    #                  queryParams.coldDays, queryParams.replicaNum, queryParams.writePeak, queryParams.AZ, queryParams.master, hot_df,
    #                  warm_df, price_df)
    # optimized_instance = asos.optimized_instance_choose()
    # print(optimized_instance)
    # optimized_instance_detail = asos.optimized_instance_choose(show_detail=True)
    # pricing_instance = asos.pricing_select(optimized_instance, queryParams.region, queryParams.paymentOptions, queryParams.RI)
    # pricing_instance_detail = asos.pricing_select(optimized_instance_detail, queryParams.region, queryParams.paymentOptions, queryParams.RI)
    # pricing_list = asos.unnest_pricing_instance_list(pricing_instance)
    # thin_list = asos.pricing_list_thin_columns(pricing_list)
    aoss = AOSLogAnalyticsSolution(price_df,hot_df,warm_df,queryParams)
    res_list = aoss.solution()
    print(res_list)
    filter_list = []
    hot_type = []
    hot_size = []
    warm_size = []
    if queryParams.filterData != "":
        arr = queryParams.filterData.split("-")
        if arr[0] != "":
            hot_type = arr[0].split(",")
        if arr[1] != "":
            hot_size = arr[1].split(",")
        if arr[2] != "":
            warm_size = arr[2].split(",")
    for item in res_list:
        if len(hot_type) != 0 and len(hot_size) != 0 and len(warm_size)!=0:
            if item["INSTANCE_TYPE"].split(".")[0] in hot_type and item["INSTANCE_TYPE"].split(".")[1] in hot_size and item["WARM_INSTANCE_TYPE"].split(".")[1] in warm_size:
                filter_list.append(item)
        elif len(hot_type)!= 0 and len(hot_size) != 0:
            if item["INSTANCE_TYPE"].split(".")[0] in hot_type and item["INSTANCE_TYPE"].split(".")[1] in hot_size:
                filter_list.append(item)
        elif len(hot_size) != 0 and len(warm_size) != 0:
            if item["INSTANCE_TYPE"].split(".")[1] in hot_size and item["WARM_INSTANCE_TYPE"].split(".")[
                1] in warm_size:
                filter_list.append(item)
        elif len(hot_type) != 0 and len(warm_size) != 0:
            if item["INSTANCE_TYPE"].split(".")[0] in hot_type and item["WARM_INSTANCE_TYPE"].split(".")[
                1] in warm_size:
                filter_list.append(item)
        elif len(hot_type) == 0 and len(hot_size) == 0 and len(warm_size) == 0:
            filter_list.append(item)
        elif len(hot_type) != 0:
            if item["INSTANCE_TYPE"].split(".")[0] in hot_type:
                filter_list.append(item)
        elif len(hot_size) != 0:
            if item["INSTANCE_TYPE"].split(".")[1] in hot_size:
                filter_list.append(item)
        elif len(warm_size) != 0:
            if item["WARM_INSTANCE_TYPE"].split(".")[1] in warm_size:
                filter_list.append(item)


    data, total_page = pagination(filter_list, queryParams.pageSize, queryParams.page)

    res = {"code":200, "result": {"page": queryParams.page, "pageSize": queryParams.pageSize, "pageCount": total_page, "list":data}}
    return res

@app.post("/provisioned/es_ec2_sizing")
async def es_ec2_sizing(request: Request, queryParams: EC2LogAnalyticsRequest):
    # xxxx = request.headers.get('xxxx')
    print(queryParams.dict())
    # asos = AOSSizing(queryParams.sourceDataSize, queryParams.dailyDataSize, queryParams.hotDays, queryParams.warmDays,
    #                  queryParams.coldDays, queryParams.replicaNum, queryParams.writePeak, queryParams.AZ, queryParams.master, hot_df,
    #                  warm_df, price_df)
    # optimized_instance = asos.optimized_instance_choose()
    # print(optimized_instance)
    # optimized_instance_detail = asos.optimized_instance_choose(show_detail=True)
    # pricing_instance = asos.pricing_select(optimized_instance, queryParams.region, queryParams.paymentOptions, queryParams.RI)
    # pricing_instance_detail = asos.pricing_select(optimized_instance_detail, queryParams.region, queryParams.paymentOptions, queryParams.RI)
    # pricing_list = asos.unnest_pricing_instance_list(pricing_instance)
    # thin_list = asos.pricing_list_thin_columns(pricing_list)
    if "or1" in queryParams.reqEC2Instance:
        queryParams.reqEC2Instance = queryParams.reqEC2Instance.replace("or1","r7g")
        if queryParams.replicaNum == 0:
            # 如果是or1，当or1设置副本为0，而对比自建EC2成本时,则副本数为1
            queryParams.replicaNum = 1
    eels = ESEC2LogAnalyticsSolution(ec2_price_df,ec2_df,queryParams)
    data = eels.solution()
    res = {"code": 200, "result": {"list": [data]}}
    return res

@app.get("/provisioned/region_list")
async def region_list(request: Request):
    # xxxx = request.headers.get('xxxx')
    region_list = lf.get_aws_region_list_from_pricing()
    # res = {"code":200,"result":{"page":1,"pageSize": len(region_list),"pageCount":1,"list":region_list}}
    res = {"code":200, "result": {"list":region_list}}
    return res




if __name__ == '__main__':
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=9989)
