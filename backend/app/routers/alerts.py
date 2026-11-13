"""告警查询与处置接口（接口 4-6）。

状态流转只允许：
    pending --confirm--> confirmed --close--> closed
    pending --close--> closed
重复 confirm / close 视为幂等，返回当前对象，不报错。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import AppError, not_found, state_conflict
from ..models import Alert
from ..schemas import AlertOut, AlertPage, CloseIn, ConfirmIn
from ..timeutil import now_utc

router = APIRouter(prefix="/api", tags=["alert"])


@router.get("/alerts", response_model=AlertPage, summary="告警列表")
def list_alerts(
    status: str | None = Query(default=None, description="pending/confirmed/closed"),
    level: str | None = Query(default=None, description="blue/yellow/orange/red"),
    station_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AlertPage:
    conds = []
    if status:
        conds.append(Alert.status == status)
    if level:
        conds.append(Alert.level == level)
    if station_id:
        conds.append(Alert.station_id == station_id)

    total = db.scalar(select(func.count()).select_from(Alert).where(*conds)) or 0
    items = list(
        db.scalars(
            select(Alert)
            .where(*conds)
            .order_by(Alert.triggered_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return AlertPage(
        items=[AlertOut.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/alerts/{alert_id}/confirm", response_model=AlertOut, summary="人工确认告警"
)
def confirm_alert(
    alert_id: str, body: ConfirmIn, db: Session = Depends(get_db)
) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise not_found("alert", alert_id)

    if alert.status == "confirmed":  # 幂等
        return alert
    if alert.status != "pending":
        raise state_conflict(alert.status, "pending")

    alert.status = "confirmed"
    alert.confirmed_by = body.operator
    alert.confirmed_at = now_utc()
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/alerts/{alert_id}/close", response_model=AlertOut, summary="关闭告警")
def close_alert(
    alert_id: str, body: CloseIn, db: Session = Depends(get_db)
) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise not_found("alert", alert_id)

    if alert.status == "closed":  # 幂等
        return alert
    if alert.status not in {"pending", "confirmed"}:
        raise state_conflict(alert.status, "pending/confirmed")

    alert.status = "closed"
    alert.closed_at = now_utc()
    alert.close_reason = f"{body.reason}（操作人：{body.operator}）"
    db.commit()
    db.refresh(alert)
    return alert
