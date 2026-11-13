# FloodSentinel · 常用命令
# Windows 没装 make 也没关系，直接照抄下面的命令即可。

PY ?= python
PORT ?= 8000

.PHONY: help install run test openapi schema examples clean

help:
	@echo "make install   安装依赖"
	@echo "make run       启动后端 (默认 8000 端口)"
	@echo "make test      跑冒烟测试"
	@echo "make openapi   从代码导出接口契约到 docs/api/openapi.yaml"
	@echo "make schema    从模型导出建表 SQL 到 data/schema.sql"
	@echo "make examples  导出前端 mock 数据到 docs/examples/"
	@echo "make clean     删除数据库与缓存"

install:
	$(PY) -m pip install -r requirements.txt

run:
	cd backend && $(PY) -m uvicorn app.main:app --reload --port $(PORT)

test:
	$(PY) backend/tests/test_api.py

openapi:
	$(PY) backend/tools/dump_openapi.py

schema:
	$(PY) backend/tools/dump_schema.py

examples:
	$(PY) backend/tools/dump_examples.py

clean:
	rm -f data/floodsentinel.db
	find . -name "__pycache__" -type d -exec rm -rf {} +
