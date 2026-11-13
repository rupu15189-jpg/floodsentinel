# AGENTS.md — FloodSentinel 项目 AI 协作规范

> 所有 AI 编码工具（Cursor / Copilot / Claude Code / ChatGPT / 通义灵码）在本仓库工作前，必须先读完本文件。
> 与 `docs/FloodSentinel-启动手册.md` 冲突时，以启动手册为准。

## 1. 项目是什么

FloodSentinel 是一个防汛监测预警多智能体平台：接入雨量/水位/积水观测数据 → 规则引擎研判 → 分级告警（蓝黄橙红）→ 人工确认 → LLM 生成值班简报 → 推送飞书群 → 大屏呈现。支持场景回放与离线演示。

**演示优先级最高的一条链路**：模拟数据 → 异常检测 → 规则命中 → 橙色告警 → LLM 简报 → 人工确认 → 大屏刷新。

## 2. 技术栈（不许擅自替换）

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic |
| 数据库 | PostgreSQL 16（**不用 TimescaleDB**）, pgvector |
| 缓存/事件 | Redis 7（pub/sub + Stream） |
| 调度 | APScheduler + asyncio worker（**不用 Celery**） |
| Agent | 自研编排器（**不用 LangGraph**），工具走 JSON Schema 注册表 |
| 前端 | React 18 + TypeScript + Vite + Ant Design 5 + ECharts 5 |
| 地图 | 自绘 SVG 为主，Leaflet 为可选增强 |
| 测试 | pytest / pytest-asyncio / Playwright |
| 部署 | Docker Compose |

## 3. 目录约定

```
backend/app/{api,core,models,schemas,services,workers}
agent/{orchestrator.py,tools,prompts,rag}
data/{simulator,scenarios,seeds}
frontend/src/{pages,components,services}
docs/
```

## 4. 常用命令

```bash
make up          # docker compose 起全栈
make dev         # 本地起后端（热重载）
make test        # pytest
make lint        # ruff check + ruff format --check
make type        # mypy backend agent
make fe-dev      # 前端开发服务器
make e2e         # Playwright
make migrate m="msg"   # 生成迁移
```

## 5. 契约（最重要的规则）

- **接口契约**：`docs/api/openapi.yaml`。改接口 = 先改这个文件 + 通知队长，禁止先写实现再补文档。
- **数据契约**：`backend/app/schemas/` 里的 Pydantic 模型。字段 camelCase，时间带时区。
- **规则格式**：`data/rules/*.yaml`，结构见启动手册 10.2。
- **场景格式**：`data/scenarios/*.json`，结构见启动手册 3.4。

AI 写实现前，**必须把相关 schema / openapi 片段贴进上下文**，否则它一定会发明字段。

## 6. 编码规范

- 代码注释与 docstring 用中文，提交信息用英文 type + 中文描述（`feat(alert): 增加冷却窗口`）
- 所有 I/O 必须 async；外部调用统一 `httpx.AsyncClient`，超时 10s
- 错误统一抛 `AppError(code, message, http_status)`，由全局 handler 转成 `{code,message,traceId}`
- 时间只用带时区的 `datetime`，DB 存 UTC，出参转 `Asia/Shanghai`
- 日志用结构化 JSON：`traceId, actor, action, latencyMs, result`
- **禁止 `eval` / `exec`**（规则引擎必须走 AST 安全求值）
- **禁止硬编码阈值**：所有阈值从 `config/` 或 `rule` 表读取
- 新增依赖必须在 PR 描述里写理由，并锁版本

## 7. AI 生成代码的验收要求

1. 必须能本地跑通（贴运行输出）
2. 必须有对应测试，核心 service 覆盖率 ≥ 70%
3. 必须能解释每一行；讲不清的删掉重写
4. PR 描述标注 `AI-assisted: <百分比>`
5. 涉及数据库迁移的，必须人工逐行核对 `upgrade` 和 `downgrade`

## 8. AI 高发幻觉区（每次生成后必查）

| 区域 | 典型错误 |
|---|---|
| SQLAlchemy | 1.x `session.query()` 与 2.0 `select()` 混用 |
| Pydantic | v1 `class Config` 与 v2 `model_config` 混用 |
| Alembic | 忘记 `downgrade`；SQLite/PG 类型不兼容 |
| ECharts | `dataset` / `markLine` 结构写错；5.x 与 4.x 混淆 |
| AntD | `Table` 泛型、`Form` 受控写法 |
| 水文公式 | SCS-CN 系数（0.2S / 25400）、rating curve 指数 |
| FastAPI | `BackgroundTasks` 与 APScheduler 重复执行 |
| 时区 | naive datetime 直接入库 |

## 9. 禁止事项

- ❌ 直推 `main`
- ❌ 把 API Key / 密钥写进代码或提交历史
- ❌ 修改 `docs/api/openapi.yaml` 不通知队长
- ❌ 引入新的重型框架（K8s、Kafka、Milvus、LangChain 全家桶）
- ❌ 为了让 demo 好看而写死数据（可以 mock，但必须走 mock 开关）
- ❌ 删除或跳过失败的测试来让 CI 变绿
