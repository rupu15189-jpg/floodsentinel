"""接口出入参模型（= 对前端的契约）。

字段一律 snake_case；时间字段用 field_serializer 统一输出 +08:00。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from .timeutil import to_api


class StationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    type: str
    lng: float
    lat: float
    basin_id: str
    warn_level: float | None = None
    guarantee_level: float | None = None
    history_max: float | None = None
    status: str


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    station_id: str
    ts: datetime
    metric: str
    value: float
    unit: str
    quality: str
    source: str

    @field_serializer("ts")
    def _ts(self, v: datetime) -> str | None:
        return to_api(v)


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    station_id: str
    level: str
    status: str
    title: str
    evidence: list = Field(default_factory=list)
    dedup_key: str
    triggered_at: datetime
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None
    closed_at: datetime | None = None
    close_reason: str | None = None

    @field_serializer("triggered_at", "confirmed_at", "closed_at")
    def _dt(self, v: datetime | None) -> str | None:
        return to_api(v)


class AlertPage(BaseModel):
    items: list[AlertOut]
    total: int
    page: int
    page_size: int


class ConfirmIn(BaseModel):
    operator: str = Field(min_length=1, max_length=32)
    remark: str | None = Field(default=None, max_length=200)


class CloseIn(BaseModel):
    operator: str = Field(min_length=1, max_length=32)
    reason: str = Field(min_length=1, max_length=200)


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    alert_ids: list
    content_md: str
    citations: list
    model: str
    fallback: bool
    latency_ms: int
    generated_at: datetime

    @field_serializer("generated_at")
    def _dt(self, v: datetime) -> str | None:
        return to_api(v)


class GenerateReportIn(BaseModel):
    alert_id: str = Field(min_length=1, max_length=32)


class ScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    duration_min: int
    seed: int
    injections: list
    expected: dict


class ReplayIn(BaseModel):
    speed: float = Field(default=60, gt=0, le=3600)


class ReplayOut(BaseModel):
    replay_id: str
    scenario_id: str
    speed: float
    started_at: datetime
    status: str = "started"

    @field_serializer("started_at")
    def _dt(self, v: datetime) -> str | None:
        return to_api(v)


class ErrorOut(BaseModel):
    code: str
    message: str
    trace_id: str
