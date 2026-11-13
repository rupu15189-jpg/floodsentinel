"""场景查询与回放（接口 8）。

W1 只做"回放入口"：校验场景存在、返回 replay_id，真正的按时间轴重演
由黄锰猛（场景数据）和胡子妍（时间轴页面）在 W5 完成。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import not_found
from ..models import Scenario
from ..schemas import ReplayIn, ReplayOut, ScenarioOut
from ..timeutil import now_utc

router = APIRouter(prefix="/api", tags=["scenario"])


@router.get("/scenarios", response_model=list[ScenarioOut], summary="场景列表")
def list_scenarios(db: Session = Depends(get_db)) -> list[Scenario]:
    return list(db.scalars(select(Scenario).order_by(Scenario.id)))


@router.post(
    "/scenarios/{scenario_id}/replay", response_model=ReplayOut, summary="回放场景"
)
def replay_scenario(
    scenario_id: str, body: ReplayIn | None = None, db: Session = Depends(get_db)
) -> ReplayOut:
    if db.get(Scenario, scenario_id) is None:
        raise not_found("scenario", scenario_id)

    speed = body.speed if body else 60.0
    return ReplayOut(
        replay_id=f"RF-{uuid.uuid4().hex[:10].upper()}",
        scenario_id=scenario_id,
        speed=speed,
        started_at=now_utc(),
        status="started",
    )
