from __future__ import annotations

from contextlib import asynccontextmanager

from env_bootstrap import load_local_env

load_local_env()

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from db_common import init_database_and_tables
from fastapi_shared import _check_required_env, clear_dashboard_cache, clear_public_orders_cache, fail_payload
from routers import manage_router, public_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    _check_required_env()
    init_database_and_tables()
    yield


app = FastAPI(
    title="FKS Recharge Verify API",
    version="4.1.0-fastapi",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "openid", "x-user-key", "x-admin-token"],
)


@app.middleware("http")
async def invalidate_caches_on_write(request: Request, call_next):
    if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path != "/api/manage/login":
        clear_dashboard_cache()
        clear_public_orders_cache()
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=422, content=fail_payload(f"参数校验失败: {exc.errors()}"))
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


app.include_router(public_router)
app.include_router(manage_router)


@app.get("/api/{rest_of_path:path}", include_in_schema=False)
def not_found_api(rest_of_path: str):
    return JSONResponse(status_code=404, content=fail_payload("接口不存在"))
