"""数据模型：5 张表。

station     站点档案
observation 观测数据（时序）
alert       告警记录
report      值班简报
scenario    回放场景

约定：
- 主键：station/alert/report/scenario 用可读字符串，observation 用自增整数
- 时间：一律存 UTC 的 naive datetime，出参时经 timeutil.to_api 转 +08:00
- JSON：evidence / citations / injections 用 JSON 列，SQLite 也支持
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Station(Base):
    __tablename__ = "station"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(16), index=True)  # rain/level/waterlog
    lng: Mapped[float] = mapped_column(Float)
    lat: Mapped[float] = mapped_column(Float)
    basin_id: Mapped[str] = mapped_column(String(32), index=True)
    warn_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    guarantee_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    history_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="online")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Station {self.code} {self.name}>"


class Observation(Base):
    __tablename__ = "observation"
    __table_args__ = (
        Index("ix_obs_station_ts", "station_id", "ts"),
        Index("ix_obs_metric_ts", "metric", "ts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[str] = mapped_column(ForeignKey("station.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    metric: Mapped[str] = mapped_column(String(32))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(8))
    quality: Mapped[str] = mapped_column(String(8), default="ok")  # ok/suspect/bad
    source: Mapped[str] = mapped_column(String(16), default="seed")


class Alert(Base):
    __tablename__ = "alert"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    station_id: Mapped[str] = mapped_column(ForeignKey("station.id"), index=True)
    level: Mapped[str] = mapped_column(String(8), index=True)  # blue/yellow/orange/red
    status: Mapped[str] = mapped_column(String(16), index=True, default="pending")
    title: Mapped[str] = mapped_column(String(200))
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    dedup_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    confirmed_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    close_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)


class Report(Base):
    __tablename__ = "report"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    alert_ids: Mapped[list] = mapped_column(JSON, default=list)
    content_md: Mapped[str] = mapped_column(Text)
    citations: Mapped[list] = mapped_column(JSON, default=list)
    model: Mapped[str] = mapped_column(String(64), default="template-v1")
    fallback: Mapped[bool] = mapped_column(Boolean, default=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime)


class Scenario(Base):
    __tablename__ = "scenario"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(300), default="")
    duration_min: Mapped[int] = mapped_column(Integer, default=180)
    seed: Mapped[int] = mapped_column(Integer, default=0)
    injections: Mapped[list] = mapped_column(JSON, default=list)
    expected: Mapped[dict] = mapped_column(JSON, default=dict)
