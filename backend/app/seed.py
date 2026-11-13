"""种子数据：8 个站点 + 48 小时观测 + 2 条告警 + 2 个场景。

设计原则
- 完全确定性：固定随机种子 + 固定时间锚点，每次生成结果一致，方便回放和截图
- 数据"像真的"：一场两小时的暴雨过程，雨量呈钟形，水位滞后 40 分钟响应
- 故意留一点脏数据：L-003 有一段 30 分钟卡死（quality=suspect），用来演示数据质检

注意：真正的模拟器由黄锰猛在 W1 重写，这里只是让接口有数据可返回。
"""

from __future__ import annotations

import random
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import SEED_ANCHOR, SEED_HOURS, SEED_INTERVAL_MIN, SEED_RANDOM_SEED
from .models import Alert, Observation, Report, Scenario, Station
from .timeutil import parse_api, to_db

STATIONS = [
    # id,     code,    name,           type,       lng,     lat,    basin,  warn, guarantee, hist
    ("R-001", "R-001", "城西雨量站", "rain", 113.242, 23.132, "城西", None, None, None),
    ("R-002", "R-002", "城东雨量站", "rain", 113.318, 23.126, "城东", None, None, None),
    ("R-003", "R-003", "上游雨量站", "rain", 113.196, 23.168, "上游", None, None, None),
    ("L-001", "L-001", "城西水位站", "level", 113.248, 23.128, "城西", 5.00, 5.80, 6.20),
    ("L-002", "L-002", "城东水位站", "level", 113.322, 23.122, "城东", 5.00, 5.80, 6.20),
    ("L-003", "L-003", "上游水位站", "level", 113.201, 23.164, "上游", 5.30, 6.10, 6.50),
    ("W-001", "W-001", "城西隧道积水点", "waterlog", 113.252, 23.130, "城西", None, None, None),
    ("W-002", "W-002", "城东下穿积水点", "waterlog", 113.327, 23.119, "城东", None, None, None),
]

# 暴雨过程：相对 t0 的分钟数
STORM_START, STORM_PEAK, STORM_END = 1680, 1815, 1920
# 各站点对暴雨的响应系数
RAIN_FACTOR = {"R-001": 1.00, "R-002": 0.72, "R-003": 1.15}
LEVEL_FACTOR = {"L-001": 1.00, "L-002": 0.78, "L-003": 1.10}
WATERLOG_FACTOR = {"W-001": 1.00, "W-002": 0.85}


def _bell(minute: float, start: float, peak: float, end: float) -> float:
    """三角钟形：0 → 1 → 0。"""
    if minute <= start or minute >= end:
        return 0.0
    if minute < peak:
        return (minute - start) / (peak - start)
    return (end - minute) / (end - peak)


def _lag(minute: float, lag_min: float = 40) -> float:
    return _bell(minute - lag_min, STORM_START, STORM_PEAK, STORM_END + 180)


def build_observations(anchor, rng: random.Random) -> list[Observation]:
    """生成 48h × 5min 的观测序列。"""
    step = timedelta(minutes=SEED_INTERVAL_MIN)
    steps = int(SEED_HOURS * 60 / SEED_INTERVAL_MIN)
    db_anchor = to_db(anchor)
    rows: list[Observation] = []

    # 先算每站的 5 分钟雨量，再滚动求 1 小时累计
    for sid in RAIN_FACTOR:
        window: list[float] = []
        for i in range(steps):
            minute = i * SEED_INTERVAL_MIN
            intensity = 78.0 * _bell(minute, STORM_START, STORM_PEAK, STORM_END)
            intensity *= RAIN_FACTOR[sid]
            mm5 = max(0.0, intensity / 60.0 * SEED_INTERVAL_MIN + rng.gauss(0, 0.15))
            window.append(mm5)
            rain_1h = sum(window[-12:])
            rows.append(
                Observation(
                    station_id=sid,
                    ts=db_anchor + step * i,
                    metric="rainfall_1h",
                    value=round(rain_1h, 1),
                    unit="mm",
                    quality="ok",
                )
            )

    for sid in LEVEL_FACTOR:
        base = 4.20 if sid != "L-003" else 4.55
        for i in range(steps):
            minute = i * SEED_INTERVAL_MIN
            level = base + 1.05 * LEVEL_FACTOR[sid] * _lag(minute) + rng.gauss(0, 0.02)
            quality = "ok"
            # L-003 在 25:00-25:30 之间卡死，用于演示质检
            if sid == "L-003" and 1500 <= minute < 1530:
                level = base + 1.05 * LEVEL_FACTOR[sid] * _lag(1500)
                quality = "suspect"
            rows.append(
                Observation(
                    station_id=sid,
                    ts=db_anchor + step * i,
                    metric="water_level",
                    value=round(level, 2),
                    unit="m",
                    quality=quality,
                )
            )

    for sid in WATERLOG_FACTOR:
        for i in range(steps):
            minute = i * SEED_INTERVAL_MIN
            depth = max(0.0, 52.0 * WATERLOG_FACTOR[sid] * _lag(minute, 55) + rng.gauss(0, 1.2))
            rows.append(
                Observation(
                    station_id=sid,
                    ts=db_anchor + step * i,
                    metric="water_depth",
                    value=round(depth, 1),
                    unit="cm",
                    quality="ok",
                )
            )

    return rows


def _peak(rows: list[Observation], station_id: str, metric: str) -> Observation | None:
    picked = [r for r in rows if r.station_id == station_id and r.metric == metric]
    return max(picked, key=lambda r: r.value) if picked else None


def build_alerts(rows: list[Observation]) -> list[Alert]:
    """从数据里挑两条"真实"告警，而不是写死。"""
    alerts: list[Alert] = []

    p = _peak(rows, "R-001", "rainfall_1h")
    if p and p.value >= 50:
        alerts.append(
            Alert(
                id="AL-20260720-0001",
                station_id="R-001",
                level="orange",
                status="pending",
                title=f"城西雨量站 1 小时雨量 {p.value}mm，达橙色预警",
                evidence=[
                    {"metric": "rainfall_1h", "value": p.value, "threshold": 50,
                     "op": ">=", "window": "1h", "note": "1 小时雨量达到橙色阈值"},
                ],
                dedup_key="R-001:orange",
                triggered_at=p.ts,
            )
        )

    p2 = _peak(rows, "L-001", "water_level")
    if p2 and p2.value >= 5.0:
        alerts.append(
            Alert(
                id="AL-20260720-0002",
                station_id="L-001",
                level="yellow",
                status="confirmed",
                title=f"城西水位站水位 {p2.value}m，超警戒水位",
                evidence=[
                    {"metric": "water_level", "value": p2.value, "threshold": 5.0,
                     "op": ">=", "window": "realtime", "note": "超过警戒水位 5.00m"},
                ],
                dedup_key="L-001:yellow",
                triggered_at=p2.ts,
                confirmed_by="值班员-张三",
                confirmed_at=p2.ts + timedelta(minutes=6),
            )
        )

    return alerts


SCENARIOS = [
    Scenario(
        id="SC-2026-0720",
        name="2026-07-20 城西暴雨",
        description="一场持续约 2 小时的强降雨，城西片区 1 小时雨量峰值超过 50mm，触发橙色预警。",
        duration_min=180,
        seed=SEED_RANDOM_SEED,
        injections=[
            {"at": "00:00", "type": "rainfall", "station_ids": ["R-001"], "intensity": 8},
            {"at": "00:30", "type": "rainfall", "station_ids": ["R-001", "R-003"], "intensity": 42},
            {"at": "01:10", "type": "fault", "station_id": "L-003", "fault": "stuck"},
        ],
        expected={"first_alert_at": "00:47", "max_level": "orange", "alert_count": 2},
    ),
    Scenario(
        id="SC-2026-0721",
        name="2026-07-21 城东短时强降雨",
        description="城东片区 40 分钟短时强降雨，积水点水位快速上涨，未达橙色。",
        duration_min=120,
        seed=SEED_RANDOM_SEED + 1,
        injections=[
            {"at": "00:10", "type": "rainfall", "station_ids": ["R-002"], "intensity": 55},
        ],
        expected={"first_alert_at": "00:22", "max_level": "yellow", "alert_count": 1},
    ),
]


def seed_if_empty(db: Session) -> bool:
    """空库才灌数据；返回是否真的灌了。"""
    if db.scalar(select(func.count()).select_from(Station)):
        return False

    rng = random.Random(SEED_RANDOM_SEED)
    anchor = parse_api(SEED_ANCHOR)

    for sid, code, name, stype, lng, lat, basin, warn, guar, hist in STATIONS:
        db.add(
            Station(
                id=sid, code=code, name=name, type=stype, lng=lng, lat=lat,
                basin_id=basin, warn_level=warn, guarantee_level=guar,
                history_max=hist, status="online",
            )
        )

    rows = build_observations(anchor, rng)
    db.add_all(rows)
    db.add_all(build_alerts(rows))
    db.add_all(SCENARIOS)
    db.commit()
    return True
