"""应用入口。

启动顺序：建表 → 空库则灌种子数据 → 提供接口。
本地运行：
    cd backend
    uvicorn app.main:app --reload --port 8000
接口文档：http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text

from .config import API_PREFIX, APP_NAME, APP_VERSION, CORS_ORIGINS
from .db import SessionLocal, engine, init_db
from .errors import AppError
from .models import Station
from .routers import alerts, reports, scenarios, stations
from .seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        seeded = seed_if_empty(db)
    if seeded:
        print("[startup] 已灌入种子数据")
    yield


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="防汛监测预警智能体平台 · 后端服务（W1 骨架版）",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "trace_id": uuid.uuid4().hex[:12],
        },
    )


@app.get(f"{API_PREFIX}/health", tags=["system"], summary="健康检查")
def health() -> dict:
    with SessionLocal() as db:
        db.execute(text("select 1"))
        station_count = db.scalar(select(func.count()).select_from(Station)) or 0
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
        "db": engine.dialect.name,
        "stations": station_count,
    }


for module in (stations, alerts, reports, scenarios):
    app.include_router(module.router)
