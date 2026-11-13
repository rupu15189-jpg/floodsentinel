"""全局配置：只读环境变量，不在代码里硬编码路径和密钥。"""

from __future__ import annotations

import os
from pathlib import Path

# 项目根目录（backend/app/config.py → 上三级）
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = Path(os.getenv("FLOOD_DB_PATH", str(DATA_DIR / "floodsentinel.db")))
DB_URL = os.getenv("FLOOD_DB_URL", f"sqlite:///{DB_PATH.as_posix()}")

# 前端开发服务器地址，用于 CORS
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "FLOOD_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080",
    ).split(",")
    if o.strip()
]

API_PREFIX = "/api"
APP_NAME = "FloodSentinel"
APP_VERSION = "0.1.0"

# 数据锚点：所有种子数据以此时间点为 0 时刻，保证每次生成完全一致
SEED_ANCHOR = "2026-07-19T00:00:00+08:00"
SEED_HOURS = 48
SEED_INTERVAL_MIN = 5
SEED_RANDOM_SEED = 20260720
