"""生成接口示例 JSON，供前端（胡子妍）在没有后端时做 mock 用。

用法：python backend/tools/dump_examples.py
输出：docs/examples/*.json
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import os  # noqa: E402

_TMP = Path(tempfile.mkdtemp(prefix="floodsentinel-examples-"))
os.environ["FLOOD_DB_PATH"] = str(_TMP / "examples.db")

from contextlib import ExitStack  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

OUT = BACKEND.parent / "docs" / "examples"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        client = stack.enter_context(TestClient(app))

        stations = client.get("/api/stations").json()
        alerts = client.get("/api/alerts").json()
        obs = client.get(
            "/api/stations/R-001/observations",
            params={"from": "2026-07-20T04:00:00+08:00", "to": "2026-07-20T08:00:00+08:00"},
        ).json()
        report = client.post(
            "/api/reports/generate", json={"alert_id": "AL-20260720-0001"}
        ).json()

        payloads = {
            "stations.json": stations,
            "alerts.json": alerts,
            "observations.json": obs,
            "report.json": report,
        }
        for name, data in payloads.items():
            path = OUT / name
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"written: {path}")


if __name__ == "__main__":
    main()
