"""值班简报生成（接口 7）。

W1 阶段是**模板版**，不调用大模型：先把链路打通、字段定死。
W3 由李宇露替换成 LLM 版本，接口出入参保持不变，前端不用改。

模板版的三段式结构 = 未来 LLM 版的输出契约：
    结论 / 依据 / 建议 / 数据来源
"""

from __future__ import annotations

import time
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import not_found
from ..models import Alert, Observation, Report, Station
from ..schemas import GenerateReportIn, ReportOut
from ..timeutil import now_utc

router = APIRouter(prefix="/api", tags=["report"])

LEVEL_CN = {"blue": "蓝色", "yellow": "黄色", "orange": "橙色", "red": "红色"}


def _recent_peak(db: Session, station_id: str, metric: str, around) -> Observation | None:
    """取告警前后 2 小时内的峰值观测。"""
    rows = db.scalars(
        select(Observation).where(
            Observation.station_id == station_id,
            Observation.metric == metric,
            Observation.ts >= around - timedelta(hours=2),
            Observation.ts <= around + timedelta(hours=2),
        )
    )
    rows = list(rows)
    return max(rows, key=lambda r: r.value) if rows else None


def _render(alert: Alert, station: Station, peak: Observation | None) -> str:
    level = LEVEL_CN.get(alert.level, alert.level)
    ev = alert.evidence[0] if alert.evidence else {}
    value = ev.get("value", "—")
    threshold = ev.get("threshold", "—")
    window = ev.get("window", "—")

    lines = [
        f"## 研判结论",
        f"{station.name}（{station.code}）在 {alert.triggered_at:%H:%M} 前后达到{level}预警条件，"
        f"当前需要进入{level}响应状态。",
        "",
        "## 判定依据",
        f"- {window} 指标值 {value}，阈值 {threshold}，判定规则：{ev.get('op', '>=')}",
        f"- 触发时间：{alert.triggered_at:%Y-%m-%d %H:%M}（UTC 存储，北京时间展示）",
    ]
    if peak is not None:
        lines.append(f"- 前后两小时峰值：{peak.value}{peak.unit}，出现在 {peak.ts:%H:%M}")
    lines += [
        "",
        "## 处置建议",
        "1. 通知属地街道（乡镇）值守人员到岗，重点巡查低洼路段与地下空间。",
        "2. 加密该站点观测频次至 5 分钟一次，持续观察 1 小时。",
        "3. 若 30 分钟内指标继续上升，提请升级为更高一级预警。",
        "",
        "## 数据来源",
        f"- 站点档案：{station.name}（{station.id}）",
        f"- 观测数据：本系统 observation 表，metric={ev.get('metric', '—')}",
        "- 本简报由规则模板生成（模型未启用），数值未做任何推测。",
    ]
    return "\n".join(lines)


@router.post("/reports/generate", response_model=ReportOut, summary="生成值班简报")
def generate_report(body: GenerateReportIn, db: Session = Depends(get_db)) -> Report:
    started = time.perf_counter()
    alert = db.get(Alert, body.alert_id)
    if alert is None:
        raise not_found("alert", body.alert_id)
    station = db.get(Station, alert.station_id)
    if station is None:
        raise not_found("station", alert.station_id)

    ev = alert.evidence[0] if alert.evidence else {}
    peak = _recent_peak(db, alert.station_id, ev.get("metric", "rainfall_1h"), alert.triggered_at)
    content = _render(alert, station, peak)

    report = Report(
        id=f"RP-{uuid.uuid4().hex[:12].upper()}",
        alert_ids=[alert.id],
        content_md=content,
        citations=[],
        model="template-v1",
        fallback=True,
        latency_ms=int((time.perf_counter() - started) * 1000),
        generated_at=now_utc(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
