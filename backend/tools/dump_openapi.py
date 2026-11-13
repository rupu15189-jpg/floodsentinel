"""从 FastAPI 自动导出 OpenAPI 契约到 docs/api/openapi.yaml。

好处：契约永远等于代码，不会出现"文档写完忘了改"。
用法：python backend/tools/dump_openapi.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import yaml  # noqa: E402

from app.main import app  # noqa: E402

OUT = BACKEND.parent / "docs" / "api" / "openapi.yaml"


def main() -> None:
    spec = app.openapi()
    spec["servers"] = [{"url": "http://127.0.0.1:8000", "description": "本地开发"}]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(spec, fh, allow_unicode=True, sort_keys=False, width=100)
    print(f"written: {OUT}")


if __name__ == "__main__":
    main()
