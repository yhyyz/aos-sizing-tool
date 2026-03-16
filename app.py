import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from v2.routes.routes import router as v2_router, init_data as v2_init_data

logger = logging.getLogger(__name__)

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
ASSETS_DIR = os.path.join(DIST_DIR, "assets")
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
templates = Jinja2Templates(directory=DIST_DIR)


async def catch_exceptions_middleware(request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        return JSONResponse(
            content={"code": 500, "error": {"message": f"{type(exc)} {exc}"}}
        )


app.middleware("http")(catch_exceptions_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


DATA_SOURCE = os.environ.get("DATA_SOURCE", "api").lower()

if DATA_SOURCE == "api":
    logger.info("Loading data from AWS Bulk Pricing API...")
    from util.load_from_api import LoadDataFromAPI

    lf = LoadDataFromAPI()
else:
    logger.info("Loading data from Excel files...")
    from util.load_execl_data import LoadDataFromExcel

    lf = LoadDataFromExcel()

price_df = lf.pricing_df
hot_df = lf.read_aos_hot_instance()
warm_df = lf.read_aos_warm_instance()
ec2_df = lf.read_ec2_instance()
ec2_price_df = lf.read_ec2_pricing()
logger.info("Data source: %s — loaded %d pricing rows", DATA_SOURCE, len(price_df))

v2_init_data(
    pricing_df=price_df,
    hot_df=hot_df,
    warm_df=warm_df,
    ec2_pricing_df=ec2_price_df,
    ec2_instance_df=ec2_df,
    region_list=lf.get_aws_region_list_from_pricing(),
)
app.include_router(v2_router)


@app.get("/", response_class=HTMLResponse)
async def root():
    return templates.TemplateResponse("index.html", {"request": {}})


@app.get("/{path:path}", response_class=HTMLResponse)
async def spa_fallback(path: str):
    file_path = os.path.join(DIST_DIR, path)
    if os.path.isfile(file_path):
        from fastapi.responses import FileResponse

        return FileResponse(file_path)
    return templates.TemplateResponse("index.html", {"request": {}})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=9989)
