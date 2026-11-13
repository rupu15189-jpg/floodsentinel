"""把 ORM 模型导出成 data/schema.sql，供报告和答辩使用。

用法：python backend/tools/dump_schema.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app import models  # noqa: E402,F401

OUT = BACKEND.parent / "data" / "schema.sql"


def main() -> None:
    chunks = [
        "-- 由 backend/tools/dump_schema.py 自动生成，请勿手改",
        "-- 与 backend/app/models.py 一一对应",
        "",
    ]
    for table in Base.metadata.sorted_tables:
        chunks.append(str(CreateTable(table).compile(engine)).strip() + ";")
        for index in table.indexes:
            chunks.append(str(CreateIndex(index).compile(engine)).strip() + ";")
        chunks.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(chunks), encoding="utf-8")
    print(f"written: {OUT}")


if __name__ == "__main__":
    main()
