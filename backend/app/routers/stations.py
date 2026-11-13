"""站点与观测查询接口（接口 1-3）。"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import AppError, not_found
from ..models import Observation, Station
from ..schemas import ObservationOut, StationOut
from ..timeutil import to_db

router = APIRouter(prefix="/api", tags=["station"])


@router.get("/stations", response_model=list[StationOut], summary="站点列表")
def list_stations(
    basin_id: str | None = Query(default=None, description="流域编号，如 城西"),
    type: str | None = Query(default=None, description="站点类型 rain/level/waterlog"),
    db: Session = Depends(get_db),
) -> list[Station]:
    stmt = select(Station)
    if basin_id:
        stmt = stmt.where(Station.basin_id == basin_id)
    if type:
        stmt = stmt.where(Station.type == type)
    return list(db.scalars(stmt.order_by(Station.code)))


@router.get(
    "/stations/{station_id}/observations",
    response_model=list[ObservationOut],
    summary="站点历史时序",
)
def list_observations(
    station_id: str,
    from_: str = Query(alias="from", description="起始时间，ISO8601"),
    to: str = Query(description="结束时间，ISO8601"),
    metric: str | None = Query(default=None),
    limit: int = Query(default=5000, ge=1, le=20000),
    db: Session = Depends(get_db),
) -> list[Observation]:
    if db.get(Station, station_id) is None:
        raise not_found("station", station_id)

    try:
        start = to_db(datetime.fromisoformat(from_))
        end = to_db(datetime.fromisoformat(to))
    except ValueError as exc:
        raise AppError("INVALID_TIME_RANGE", f"时间格式无法解析：{exc}", 422) from exc
    if start > end:
        raise AppError("INVALID_TIME_RANGE", "from 不能晚于 to", 422)

    stmt = (
        select(Observation)
        .where(
            Observation.station_id == station_id,
            Observation.ts >= start,
            Observation.ts <= end,
        )
        .order_by(Observation.ts)
        .limit(limit)
    )
    if metric:
        stmt = stmt.where(Observation.metric == metric)
    return list(db.scalars(stmt))


@router.get(
    "/observations/latest",
    response_model=list[ObservationOut],
    summary="多站点最新观测值",
)
def latest_observations(
    station_ids: str = Query(description="逗号分隔，如 R-001,L-001"),
    db: Session = Depends(get_db),
) -> list[Observation]:
    ids = [s.strip() for s in station_ids.split(",") if s.strip()]
    if not ids:
        raise AppError("INVALID_PARAM", "station_ids 不能为空", 422)

    out: list[Observation] = []
    for sid in ids:
        if db.get(Station, sid) is None:
            raise not_found("station", sid)
        newest = db.scalar(
            select(func.max(Observation.ts)).where(Observation.station_id == sid)
        )
        if newest is None:
            continue
        rows = db.scalars(
            select(Observation).where(
                Observation.station_id == sid, Observation.ts == newest
            )
        )
        out.extend(rows)
    return out
