"""接口冒烟测试：不依赖 pytest 也能跑。

    python backend/tests/test_api.py

装了 pytest 的话：
    cd backend && pytest tests -q
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# 必须在导入 app 之前指定临时库，避免污染开发数据
_TMP = Path(tempfile.mkdtemp(prefix="floodsentinel-test-"))
import os  # noqa: E402

os.environ["FLOOD_DB_PATH"] = str(_TMP / "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

# 用 ExitStack 进入上下文，确保 lifespan（建表 + 灌数据）被执行
from contextlib import ExitStack  # noqa: E402

_stack = ExitStack()
client = _stack.enter_context(TestClient(app))


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["stations"] == 8


def test_list_stations():
    r = client.get("/api/stations")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 8
    assert {"id", "code", "name", "type", "lng", "lat"} <= set(data[0])


def test_filter_stations_by_type():
    r = client.get("/api/stations", params={"type": "rain"})
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_station_observations():
    r = client.get(
        "/api/stations/R-001/observations",
        params={"from": "2026-07-19T00:00:00+08:00", "to": "2026-07-21T00:00:00+08:00"},
    )
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 576
    assert rows[0]["ts"].startswith("2026-07-19T00:00:00+08:00")
    assert rows[0]["unit"] == "mm"


def test_station_observations_not_found():
    r = client.get(
        "/api/stations/X-999/observations",
        params={"from": "2026-07-19T00:00:00+08:00", "to": "2026-07-21T00:00:00+08:00"},
    )
    assert r.status_code == 404
    assert r.json()["code"] == "STATION_NOT_FOUND"


def test_station_observations_bad_range():
    r = client.get(
        "/api/stations/R-001/observations",
        params={"from": "2026-07-21T00:00:00+08:00", "to": "2026-07-19T00:00:00+08:00"},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "INVALID_TIME_RANGE"


def test_latest_observations():
    r = client.get("/api/observations/latest", params={"station_ids": "R-001,L-001,W-001"})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 3
    assert {x["station_id"] for x in rows} == {"R-001", "L-001", "W-001"}


def test_list_alerts():
    r = client.get("/api/alerts")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["items"][0]["level"] in {"blue", "yellow", "orange", "red"}


def test_alert_state_machine():
    # 1) 待确认的告警可以确认
    r = client.post(
        "/api/alerts/AL-20260720-0001/confirm",
        json={"operator": "值班员-张三", "remark": "已通知街道"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "confirmed"
    assert r.json()["confirmed_by"] == "值班员-张三"

    # 2) 重复确认幂等
    r2 = client.post("/api/alerts/AL-20260720-0001/confirm", json={"operator": "值班员-李四"})
    assert r2.status_code == 200
    assert r2.json()["confirmed_by"] == "值班员-张三"

    # 3) 关闭
    r3 = client.post(
        "/api/alerts/AL-20260720-0001/close",
        json={"operator": "值班员-张三", "reason": "降雨结束，水位回落"},
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "closed"

    # 4) 已关闭的告警不能再确认
    r4 = client.post("/api/alerts/AL-20260720-0001/confirm", json={"operator": "值班员-王五"})
    assert r4.status_code == 409
    assert r4.json()["code"] == "ALERT_STATE_CONFLICT"


def test_generate_report():
    r = client.post("/api/reports/generate", json={"alert_id": "AL-20260720-0002"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "研判结论" in body["content_md"]
    assert "数据来源" in body["content_md"]
    assert body["fallback"] is True
    assert body["citations"] == []


def test_generate_report_alert_not_found():
    r = client.post("/api/reports/generate", json={"alert_id": "AL-NOPE"})
    assert r.status_code == 404


def test_scenarios():
    r = client.get("/api/scenarios")
    assert r.status_code == 200
    assert len(r.json()) == 2

    r2 = client.post("/api/scenarios/SC-2026-0720/replay", json={"speed": 60})
    assert r2.status_code == 200
    assert r2.json()["scenario_id"] == "SC-2026-0720"

    r3 = client.post("/api/scenarios/SC-NOPE/replay", json={"speed": 60})
    assert r3.status_code == 404


def _run_all() -> int:
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {name}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"ERROR {name}: {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
