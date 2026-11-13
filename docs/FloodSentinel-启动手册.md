# FloodSentinel 项目启动手册

> 防汛监测预警多智能体平台 · 软件工程课程设计 · 4 人团队 · 14 周
> 版本 v1.0 · 本手册是团队的"宪法"，任何与手册冲突的个人偏好以手册为准；要改手册，走 PR 并全员知会。

---

## 0. 怎么用这份手册

| 角色 | 每周必读 | 每天要用 |
|---|---|---|
| 队长 | 第 7、8 章（分工 + 任务表） | 第 8 章当周五验收清单 |
| P1 | 第 2、3 章 + 第 9 章 | 第 9 章的周节奏 |
| P2 | 第 3、4、5 章 + 第 10 章 | 第 4 章接口契约 |
| P3 | 第 3 章 + 第 11 章 | 第 11 章工具清单 |
| P4 | 第 4 章 + 第 12 章 | 第 4 章接口契约 |
| 所有人 | 第 6、13 章 | 第 13 章 AI 协作规范 |

**三条不可违反的规则**

1. **契约先行**：接口和数据格式没定，不许写实现。改契约找队长，队长改完通知全员。
2. **每周五必须能跑**：任何人周五交不出能运行的东西，下周一只做补齐，不做新功能。
3. **AI 生成的代码，你必须能讲清每一行**。讲不清的，删掉重写。

---

## 1. 项目定义与范围

### 1.1 一句话

把「雨量 / 水位 / 积水数据 → 风险研判 → 分级预警 → 值班简报 → 群消息推送 → 大屏呈现」这条链，做成**可回放、可追责、可离线运行**的多智能体系统。

### 1.2 三个演示场景（所有功能都为这三个场景服务）

**S1 常规值班（30 秒）**
值班员在对话框问："现在全区雨情怎么样？" → 系统汇总 24 个站点的 1h/3h/24h 雨量、超警站点数、趋势 → 输出 200 字简报，附数据来源。

**S2 暴雨升级（90 秒，核心）**
回放脚本注入强降雨 → 1h 雨量 52mm → 规则引擎命中橙色 → 生成告警（pending）→ LLM 生成研判简报（含证据、预案引用）→ **等人工确认** → 值班员点确认 → 推送飞书群卡片 → 大屏站点变橙、告警列表刷新 → 雨停后自动降级/解除。

**S3 灾后复盘（60 秒）**
选择历史场景「2024-07-20 城西内涝」→ 系统按时间轴重演 → 显示"系统在第 47 分钟发出橙色预警，实际积水在第 71 分钟达到 40cm"→ 输出预警提前量、命中/误报统计。

### 1.3 明确不做（写进开题报告，是加分项）

- ❌ 不做 7 天洪水预报、不做水文模型率定（专业水文工作，我们做不了也不该做）
- ❌ 不做真实气象/水文数据源的生产级 SLA 承诺
- ❌ 不做多租户、不做移动 App、不做小程序
- ❌ 不做视频流 AI 识别（算力与标注成本不可控）
- ❌ 不做泵站/闸门的远程控制（安全责任不可承担，只做"建议"）

### 1.4 假设与前提

- 14 周（可按 16 周顺延，缓冲加在 W15-16）
- 4 人，每周人均投入 ≥ 12 小时
- 开发机可联网；演示环境**必须能离线**
- 无 GPU 也要能跑（LLM 走 API，本地 Ollama 作为降级）
- 阈值全部为**示例值**，代码里必须可配置，并在文档标注"需按当地防汛预案校准"

---

## 2. 领域模型（全组"宪法"，W0 定死）

### 2.1 站点类型

| type | 中文 | 主指标 | 单位 | 关键字段 |
|---|---|---|---|---|
| `rain` | 雨量站 | rainfall_1h / rainfall_3h / rainfall_24h | mm | — |
| `level` | 水位站 | water_level | m | warn_level, guarantee_level, history_max |
| `flow` | 流量站 | discharge | m³/s | — |
| `waterlog` | 积水点 | water_depth | cm | warn_depth=15, danger_depth=30 |
| `pipe` | 管网监测点 | fullness | % | — |
| `pump` | 泵站 | pump_status, pump_flow | 0/1, m³/s | — |
| `gate` | 闸门 | gate_opening | % | — |

### 2.2 预警等级与判据（示例值，必须可配置）

| 等级 | 代码 | 雨量判据 | 水位判据 | 积水判据 |
|---|---|---|---|---|
| 蓝色 IV | `blue` | 24h ≥ 50mm | H ≥ warn_level | 水深 ≥ 15cm |
| 黄色 III | `yellow` | 3h ≥ 50mm 或 1h ≥ 25mm | H ≥ warn+0.2m 且 1h 涨速 ≥ 0.1m/h | 水深 ≥ 30cm |
| 橙色 II | `orange` | 1h ≥ 50mm 或 3h ≥ 80mm | H ≥ guarantee_level | 水深 ≥ 50cm 或 积水面积 ≥ 500m² |
| 红色 I | `red` | 1h ≥ 80mm 或 3h ≥ 120mm | H ≥ history_max | 水深 ≥ 80cm 且仍在上涨 |

**合并规则**：同一站点多条规则命中时，**取最高等级**，生成**一条**告警，`evidence` 数组保留全部命中证据（这是"可追责"的关键，答辩必讲）。

### 2.3 告警状态机

```
                    ┌──────────┐
       规则命中 ───▶│ pending  │
                    └────┬─────┘
         ┌───────────────┼────────────────┬──────────────┐
         │ confirm       │ auto_expire    │ dedup_hit    │ cancel
         ▼               ▼                ▼              ▼
   ┌───────────┐   ┌──────────┐    ┌────────────┐  ┌───────────┐
   │ confirmed │   │ expired  │    │ suppressed │  │ cancelled │
   └─────┬─────┘   └──────────┘    └─────┬──────┘  └───────────┘
         │ dispatch                      │ 冷却结束
         ▼                               ▼
   ┌────────────┐                  ┌──────────┐
   │ dispatched │──── close ──────▶│  closed  │
   └─────┬──────┘                  └──────────┘
         │ escalate(升级)
         └──────▶ confirmed（level+1，parent_id 指向原告警）
```

**约束（写进代码，不许口头约定）**

- `pending → confirmed` 需要角色 `operator` 或 `admin`（LLM 无权自动确认）
- 每次状态转移**必须**写 `audit_log`，且发一条 Redis 事件
- 同一 `dedup_key` 在 `cooldown`（默认 1800s）内只产生一条 pending
- 升级（escalate）不新建独立告警，通过 `parent_id` 串联成链

### 2.4 核心实体

| 表 | 关键字段 |
|---|---|
| `station` | id, code, name, type, lng, lat, basin_id, warn_level, guarantee_level, history_max, status |
| `observation` | station_id, ts, metric, value, unit, quality(ok/suspect/bad), source |
| `rule` | id, name, scope(jsonb), level, when(jsonb), cooldown_s, enabled, version |
| `alert` | id, station_id, rule_ids[], level, status, title, evidence(jsonb), dedup_key, parent_id, triggered_at, confirmed_by, confirmed_at, closed_at |
| `report` | id, alert_ids[], period, content_md, citations(jsonb), model, latency_ms, fallback(bool) |
| `audit_log` | id, actor, actor_role, action, target_type, target_id, before(jsonb), after(jsonb), ts |
| `scenario` | id, name, description, script(jsonb), expected(jsonb), created_by |
| `eval_run` | id, scenario_id, metrics(jsonb), passed, ts |

---

## 3. 数据契约

### 3.1 观测数据 `Observation`

```json
{
  "stationId": "R-001",
  "ts": "2026-07-20T14:05:00+08:00",
  "metric": "rainfall_1h",
  "value": 32.5,
  "unit": "mm",
  "quality": "ok",
  "source": "simulator"
}
```

约定：时间**必须带时区**（`+08:00`），后端统一存 UTC，出参转 Asia/Shanghai；数值保留 1 位小数。

### 3.2 告警 `Alert`

```json
{
  "alertId": "AL-20260720-0001",
  "stationId": "R-001",
  "stationName": "城西雨量站",
  "ruleIds": ["R-RAIN-1H-50"],
  "level": "orange",
  "status": "pending",
  "title": "城西雨量站 1 小时雨量 52.3mm，达橙色预警",
  "evidence": [
    {"metric": "rainfall_1h", "value": 52.3, "threshold": 50, "op": ">=", "window": "1h"},
    {"metric": "rainfall_3h", "value": 88.0, "threshold": 80, "op": ">=", "window": "3h"}
  ],
  "dedupKey": "R-001:orange",
  "triggeredAt": "2026-07-20T14:05:00+08:00",
  "needsConfirm": true,
  "parentId": null
}
```

### 3.3 值班简报 `Report`

```json
{
  "reportId": "RP-20260720-0001",
  "alertIds": ["AL-20260720-0001"],
  "contentMd": "## 研判结论\n城西片区 1h 雨量 52.3mm，已超橙色阈值…\n\n## 依据\n- 城西雨量站 1h 雨量 52.3mm（阈值 50mm）\n- 《XX市城市防洪应急预案》4.3 节：橙色响应…\n\n## 建议\n1. 通知城西街道办启动…\n",
  "citations": [
    {"docId": "plan-2024", "title": "XX市城市防洪应急预案", "section": "4.3", "page": 12, "quote": "当 1 小时降雨量达到 50 毫米以上时…"}
  ],
  "model": "qwen2.5-7b-instruct",
  "fallback": false,
  "latencyMs": 3120
}
```

**硬约束**：`citations` 里的 `quote` 必须能在检索结果中原样找到（相似度 > 0.9），否则该条引用被丢弃；一条不剩时 `fallback=true`，走模板生成。

### 3.4 场景脚本 `Scenario`

```json
{
  "id": "SC-2024-0720",
  "name": "2024-07-20 城西内涝",
  "durationMin": 180,
  "seed": 20240720,
  "injections": [
    {"at": "00:00", "type": "rainfall", "stationIds": ["R-001","R-002"], "intensity": 8},
    {"at": "00:30", "type": "rainfall", "stationIds": ["R-001"], "intensity": 42},
    {"at": "01:10", "type": "fault", "stationId": "L-003", "fault": "stuck"}
  ],
  "expected": {
    "firstAlertAt": "00:47",
    "maxLevel": "orange",
    "alertCount": 2,
    "mustNotAlert": ["R-004"]
  }
}
```

---

## 4. 接口契约（v0，W0 冻结）

**通用约定**

- Base：`/api/v1`，全部 JSON，字段 camelCase
- 时间：ISO8601 带时区
- 分页：`page`（从 1 起）、`pageSize`（默认 20，最大 100），返回 `{items, total, page, pageSize}`
- 错误：`{code, message, traceId, details}`；HTTP 用标准码（400/401/403/404/409/422/500）
- 鉴权：`Authorization: Bearer <JWT>`；角色 `viewer < operator < admin`
- 幂等：所有 POST 带 `Idempotency-Key` 头，重复 key 返回首次结果

| # | 方法 | 路径 | 说明 | 角色 | 负责 |
|---|---|---|---|---|---|
| 1 | GET | `/health` | 健康检查（含 DB/Redis/LLM 探活） | 匿名 | P2 |
| 2 | GET | `/stations` | 站点列表，支持 `basinId` `type` `bbox` | viewer | P2 |
| 3 | GET | `/stations/{id}` | 站点详情 + 阈值 | viewer | P2 |
| 4 | GET | `/stations/{id}/observations` | 时序查询 `from` `to` `metric` `interval` | viewer | P2 |
| 5 | GET | `/observations/latest` | 多站点最新值，`stationIds` 逗号分隔 | viewer | P2 |
| 6 | GET | `/alerts` | 告警列表 `status` `level` `from` `to` | viewer | P2 |
| 7 | GET | `/alerts/{id}` | 告警详情（含 evidence、关联 report） | viewer | P2 |
| 8 | POST | `/alerts/{id}/confirm` | 人工确认，body `{remark}` | operator | P2 |
| 9 | POST | `/alerts/{id}/close` | 关闭，body `{reason}` | operator | P2 |
| 10 | GET/PUT | `/rules` `/rules/{id}` | 规则查询与配置 | admin | P2 |
| 11 | POST | `/analysis/run` | 触发研判，body `{stationIds, windowMin, scenarioId?}` | operator | P3 |
| 12 | GET | `/reports/{id}` | 简报详情 | viewer | P3 |
| 13 | POST | `/chat` | 自然语言问答，SSE 流式返回 | viewer | P3 |
| 14 | GET | `/scenarios` | 场景列表 | viewer | P1 |
| 15 | POST | `/scenarios/{id}/replay` | 回放，body `{speed}` | operator | P1 |
| 16 | GET | `/metrics/summary` | 大屏聚合（站点数/超警数/告警分布） | viewer | P2 |
| 17 | WS | `/ws/alerts` | 告警实时推送 | viewer | P2 |

**`/chat` 的 SSE 事件格式**（P3 + P4 必须对齐）

```
event: token   data: {"delta":"当前"}
event: tool    data: {"name":"query_rainfall","args":{...},"status":"ok"}
event: done    data: {"answer":"...","citations":[...],"latencyMs":2100}
event: error   data: {"code":"LLM_TIMEOUT","message":"..."}
```

> 完整的 OpenAPI 见 `docs/api/openapi.yaml`。

---

## 5. 仓库结构与工程规范

```
floodsentinel/
├── AGENTS.md                 # AI 协作规范（所有 AI 工具先读这个）
├── README.md
├── docker-compose.yml
├── .env.example
├── Makefile                  # make dev / make test / make lint / make up
├── docs/
│   ├── FloodSentinel-启动手册.md
│   ├── api/openapi.yaml
│   ├── tasks/队长任务表.csv
│   ├── eval/评测报告.md
│   └── ai/                   # 每个模块一张「上下文卡片」，喂给 AI 用
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/v1/{stations,alerts,rules,reports,chat,scenarios,metrics}.py
│   │   ├── core/{config,security,logging,errors}.py
│   │   ├── models/           # SQLAlchemy
│   │   ├── schemas/          # Pydantic（= 数据契约的唯一实现）
│   │   ├── services/{alert_service,rule_engine,state_machine,report_service}.py
│   │   └── workers/{scheduler,consumer}.py
│   ├── alembic/
│   └── tests/
├── agent/
│   ├── orchestrator.py       # PLAN→ACT→OBSERVE→SYNTHESIZE→VALIDATE
│   ├── tools/                # 每个工具一个文件 + JSON Schema
│   ├── prompts/              # v1_briefing.md 等，带版本号
│   ├── rag/{ingest,retriever,eval}.py
│   └── tests/
├── data/
│   ├── simulator/            # 可复现模拟器（CLI）
│   ├── scenarios/            # SC-*.json
│   └── seeds/
├── algo/                     # 质检、异常检测、指标
├── frontend/
│   ├── src/pages/{Dashboard,Alerts,StationDetail,Rules,Scenarios,Chat}
│   ├── src/components/       # BasinMap(SVG), AlertCard, TimeSeriesChart
│   └── e2e/                  # Playwright
└── deploy/
```

**Git 规范**

- 分支：`main`（保护，禁直推）+ `feat/p1-simulator` 一类；合并走 PR，至少 1 人 review
- 提交：`feat(alert): 增加告警去重冷却` / `fix(agent): 修正工具超时未生效` / `docs:` / `test:` / `chore:`
- 每个 PR 必须包含：改了什么 / 怎么验证 / 截图或 curl 输出

**质量门（CI 必须过）**

- `ruff check` + `ruff format --check`
- `mypy backend agent`（允许 `# type: ignore` 但要写理由）
- `pytest`，核心 service 覆盖率 ≥ 70%，全仓 ≥ 50%
- 前端 `tsc --noEmit` + `eslint`
- `docker compose config` 校验

---

## 6. 技术选型决策记录（ADR 摘要）

| 选择 | 采用 | 不采用 | 理由 |
|---|---|---|---|
| 后端 | FastAPI + Pydantic v2 | Django / Spring | 异步、自动生成 OpenAPI、与 AI 生态同语言 |
| 数据库 | PostgreSQL 16 | MySQL | JSONB、窗口函数、pgvector 一库搞定 |
| 时序 | **先用普通表 + BRIN 索引** | TimescaleDB | Timescale 在 Windows/教学环境装起来费劲；数据量（百万级）普通表够用。**W6 压测后仍慢再上** |
| 缓存/事件 | Redis 7（pub/sub + Stream） | Kafka / RabbitMQ | 单人运维成本，别给自己找事 |
| 任务调度 | APScheduler + asyncio worker | Celery | 少一层 broker 心智负担 |
| Agent 编排 | **自研 ~300 行编排器** | LangGraph | 框架黑盒会让你答辩讲不清；自研可控、可测、可讲。思想借鉴 LangGraph（状态机 + 检查点） |
| 工具协议 | 自定义 JSON Schema 工具表 | 真 MCP Server | 概念借用，实现简化；W9 若有余力再包一层 MCP |
| LLM | 云 API（DeepSeek/通义）为主 + Ollama qwen2.5:7b 兜底 | 纯本地 | 演示断网必须有 Plan B |
| 向量库 | pgvector | Milvus / Chroma | 少一个组件 |
| 前端 | React 18 + TS + Vite + AntD + ECharts | Vue | 生态与组件量 |
| 地图 | **自绘 SVG 流域示意图为主**，Leaflet 为增强 | 只做 Leaflet | 在线瓦片在断网/内网必挂，SVG 永远能显示 |
| IM | 飞书群自定义机器人 Webhook（+ 交互卡片回调） | QQ/钉钉 | 接入最快、无需审核、卡片可带按钮 |
| 部署 | Docker Compose | K8s | 一台机器搞定，答辩现场就一台 |

---

## 7. 四人分工

### 7.1 为什么按"层"切而不是按"功能"切

按功能切（A 做预警、B 做简报）→ 两人都要碰数据、后端、前端，天天冲突。
按层切（数据 / 平台 / Agent / 前端）→ 每层有明确 owner，靠**契约**解耦，能真并行。

### 7.2 分工总览

| | P1 数据与算法 | P2 平台与后端（**队长**） | P3 Agent 与知识 | P4 前端与集成 |
|---|---|---|---|---|
| **一句话** | 造数据、算异常、定评测 | 造骨架、定契约、保可靠 | 造大脑、接知识、防幻觉 | 造界面、接渠道、保演示 |
| **主目录** | `data/` `algo/` `docs/eval/` | `backend/` `deploy/` | `agent/` `docs/ai/` | `frontend/` `e2e/` |
| **核心交付** | 模拟器、50 个场景、异常检测、评测报告 | 17 个接口、规则引擎、状态机、CI、一键部署 | 工具层、编排器、RAG、简报、对话 | 大屏、告警台、回放、飞书卡片、演示视频 |
| **技术栈** | Python, pandas, numpy, scipy, statsmodels, scikit-learn | FastAPI, SQLAlchemy, Alembic, Redis, Docker, pytest | Python, Pydantic, pgvector, httpx, prompt 工程 | React, TS, ECharts, AntD, Playwright |
| **兼任** | 评测负责人 | PM + 契约仲裁 + 集成守门 | 答辩主讲 + 技术文档 | QA + 演示导演 |
| **日均投入** | 2h | 2.5h | 2h | 2h |

**RACI**

| 事项 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| 数据契约（schema） | A | R | C | C |
| 接口契约（OpenAPI） | C | **A/R** | C | C |
| 预警阈值与规则语义 | **A/R** | R | C | I |
| 状态机实现 | C | **A/R** | I | I |
| 简报内容质量 | C | I | **A/R** | C |
| 大屏视觉与交互 | I | C | I | **A/R** |
| 每周集成 | C | **A/R** | C | C |
| 答辩材料 | C | R | **A** | R |

> A=最终负责，R=执行，C=需咨询，I=需知会

### 7.3 队长的额外职责（这 5 条比写代码重要）

1. **契约唯一仲裁人**：`openapi.yaml` 和 `schemas/` 只有你能合并；改完必须群发变更说明（含示例 JSON）
2. **周五集成守门**：拉全量、跑全链路、打 tag `w{N}`；坏了当场定人修，不许过夜
3. **范围砍刀**：每周五对比计划与实际，落后就砍功能，**永远保 S2 垂直切片**
4. **风险台账**：维护第 15 章那张表，每周更新状态
5. **对外接口人**：老师/助教/答辩安排全部由你对接，别让四个人各自去问

> 队长默认兼 P2。如果你更擅长 Agent，可与 P3 对调，但**接口仲裁权和集成守门必须跟着 P2 走**。

---

## 8. 队长任务表（W0–W14）

> 可导入版本见 `docs/tasks/队长任务表.csv`

| 周 | 阶段 | P1 数据算法 | P2 平台后端 | P3 Agent 知识 | P4 前端集成 | 周五验收（队长） |
|---|---|---|---|---|---|---|
| W0 | 立项 | 领域模型表 v1、阈值表 | 跑通 AstrBot、技术选型、建仓 | 调研 3 个 Agent 框架、定编排方案 | 定设计规范、画 3 张页面草图 | 边界文档签字、OpenAPI v0 冻结、架构图 v0 |
| W1 | 骨架 | 模拟器 v0（单站、纯降雨） | FastAPI 骨架 + 接口 1/2/4/5 + DB 迁移 | 工具层 v0（2 个工具）+ 单轮调用 | 大屏静态页 + SVG 流域图 + 拉接口 2 | 四人各自 demo 30 秒；`make up` 能起 |
| W2 | **垂直切片** | 模拟器 v1（30 天 1min，可复现） | 接口 6/7 + 规则引擎 v0（3 条规则）+ 事件 | 编排器 v0（单步）+ 简报 prompt v1 | 告警列表 + 详情页 + WS 订阅 | **M1：S2 全链路能录屏**（数据→告警→简报→屏幕） |
| W3 | 闭环 | 质检 L0-L2（范围/跳变/卡死/z-score） | 状态机 v1 + 接口 8/9 + audit_log | 工具扩到 5 个 + 结构化输出校验 | 告警确认交互 + 状态流转 UI | 确认/关闭走通，audit 有记录 |
| W4 | 知识 | 多站点空间相关 + 故障注入 | 接口 10/16 + 权限 RBAC | RAG v1（预案入库、top-k、引用） | 规则配置页 + 站点详情（阈值线） | 简报能带 1 条真实引用 |
| W5 | 渠道 | 场景脚本格式定稿 + 5 个场景 | 任务调度 + 冷却/去重/抑制 | 简报完整版（结论/依据/建议三段） | 飞书卡片 + 确认按钮回调 | 群里收到卡片，点按钮能回写状态 |
| W6 | **M2** | 20 场景 + 指标 v1（命中/误报/提前量） | 压测（10 万条 P95<200ms）+ 幂等 | 降级路径（超时→模板）+ 成本统计 | 回放页 v1（时间轴） | **M2 验收：20 场景跑批出报告** |
| W7 | 深化 | STL + IsolationForest，误报归因 | 接口 11/12 联调、限流 | RAG hybrid（BM25+向量）+ rerank | 图表联动、空态/错误态 | 误报率有对比数据 |
| W8 | 交互 | 场景 35 个 + 异常注入矩阵 | 接口 13 `/chat` SSE 打通 | 多轮对话 + 工具选择策略 | 对话页 + 流式渲染 | 能问"哪个站最危险"并答对 |
| W9 | 加固 | 50 场景 + 边界数据 | 审计报表 + 健康检查 + 备份脚本 | MCP 风格工具描述、工具白名单 | 大屏动效 + 演示模式（一键播放） | 断网演练通过 |
| W10 | **M3** | 评测报告初稿、指标口径复核 | 性能优化、日志埋点 | 幻觉抽样审计（30 条人工核） | E2E 用例 10 条 | **M3 验收：功能冻结** |
| W11 | 文档 | 评测报告终稿 + 图表 | 部署文档 + README | 技术文档（架构/算法/工具） | 使用手册 + 截图 | 文档齐全度检查 |
| W12 | 回归 | 支持复现问题 | 全量回归 + 修 bug | 支持 prompt 调优 | 全流程录制素材 | 零 P0 bug |
| W13 | 交付 | 答辩数据支撑 | 部署演练（干净机器） | 答辩技术部分讲稿 | 演示视频剪辑 | 视频 v1 + PPT v1 |
| W14 | 答辩 | 陪练 | 现场部署兜底 | 主讲彩排 | 现场操作演练 | 彩排 3 次，掐表 8 分钟 |

---

## 9. P1 执行手册（数据与算法）

### 9.1 你的核心产出

1. `data/simulator/` —— 一条命令生成任意流域、任意时长的可复现数据
2. `data/scenarios/` —— ≥50 个场景脚本（JSON），覆盖正常/暴雨/故障/边界
3. `algo/` —— 数据质检 + 异常检测 + 指标计算，全部可单测
4. `docs/eval/评测报告.md` —— 有图表、有基线对比、有结论

### 9.2 模拟器怎么做（三层建模）

**第一层：降雨（气象）**
- 天气状态用一阶马尔可夫链：`P(雨|晴)=0.15`，`P(雨|雨)=0.65`
- 雨强用 Gamma 分布（形状 k≈0.8，尺度 θ≈3），按 5 分钟步长生成
- 暴雨事件注入：以概率 `p_storm` 触发，持续 20–90 分钟，强度 20–80 mm/h
- 空间相关：一个"雨团中心"随机游走，站点雨强按距离衰减 `exp(-d/λ)`，λ≈3km

**第二层：产汇流（简化水文，够用即可）**
- 产流用 SCS-CN 曲线数法：`S = 25400/CN - 254`，`Q = (P-0.2S)²/(P+0.8S)`（P 为累计降雨，Q 为净雨，mm）；城市区 CN 取 85–95
- 汇流用线性水库：`dS/dt = I - Q`，`Q = S/K`，K 为滞时（10–60 分钟）
- 流量转水位用水位-流量关系曲线：`H = a·Q^b`（b 取 0.4–0.6，a 按站点标定）

**第三层：观测（含缺陷，这层最重要）**
- 噪声：高斯 σ=0.02×量程
- 故障注入（默认 2%）：`stuck`（连续 N 点相同）、`drift`（线性漂移）、`spike`（单点跳变）、`missing`（丢包）
- **不注入故障，你的异常检测就没有存在意义**——这点答辩会被问

**CLI**

```bash
python -m simulator --basin demo --days 30 --interval 60 --seed 42 \
  --fault-rate 0.02 --storm-prob 0.02 --out data/seeds/demo_30d.parquet
```

**可复现要求**：同 `seed` 必须产出完全一致的数据（用 `numpy.random.default_rng(seed)`，不要用全局 `np.random`）。

### 9.3 异常检测怎么做（分级，别一上来深度学习）

| 层 | 方法 | 输出 | 周次 |
|---|---|---|---|
| L0 质检 | 量程检查、跳变检测（\|Δ\|>3σ）、卡死（连续 6 点相同）、缺失率 | `quality: ok/suspect/bad` | W3 |
| L1 阈值 | 直接比较 | `hit: bool` | W3 |
| L2 统计 | 滑动 z-score（窗口 12）、EWMA、变化率 | `score: 0-1` | W3 |
| L3 季节分解 | STL 残差 + 3σ | `score` + 残差图 | W7 |
| L4 多站联合 | IsolationForest（特征：值、变化率、邻站差、小时） | `score` + top 特征 | W7 |

**关键**：每个异常必须输出**人类可读的解释**（"L0 卡死：L-003 连续 8 个点水位不变"），这个解释会作为 evidence 传给 Agent，是"可追责"的落点。

### 9.4 场景与评测怎么做

- 场景 = 剧本（injections）+ 期望（expected）。W5 定稿格式，之后只加内容不改结构
- 覆盖矩阵（50 个的分配）：正常 10 / 单站暴雨 10 / 多站流域暴雨 10 / 传感器故障 8 / 阈值边界 7 / 历史复盘 5
- 跑批：`pytest tests/eval -k scenario --alluredir` 或 `python -m algo.eval --all`
- 指标（必须写进报告，且给出计算公式）：
  - 命中率 = 应报且报了 / 应报总数
  - 误报率 = 不应报但报了 / 不应报总数
  - 漏报率、平均提前量（分钟）、告警条数（衡量告警风暴）、端到端 P95 时延

### 9.5 AI 怎么帮你（具体用法）

| 场景 | 提示词要点 |
|---|---|
| 写模拟器 | "实现 SCS-CN 产流函数，输入 P(mm)、CN、初损率 0.2，返回 Q(mm)；给出 3 个 pytest 用例含 P=0 和 P 极大值" |
| 造场景 | 给它规则表 + 场景 JSON schema，"生成 10 个场景，要求覆盖 1h/3h/24h 三档阈值上下浮动 5% 的边界，输出纯 JSON 数组" |
| 写测试 | 给函数签名和契约，"生成 pytest 参数化用例，覆盖 None/空数组/超量程/时区缺失" |
| 查算法 | "STL 分解对 5 分钟粒度雨量序列合理吗？参数 period 怎么选？" |

**AI 使用禁忌**：SCS-CN、皮尔逊 III 型、rating curve 这类公式，**必须自己对照教材核对**，AI 经常把系数写错（0.2S vs 0.3S、25400 vs 2540）。

### 9.6 验收标准（可测）

- [ ] 30 天 1min 数据生成 < 5s，同 seed 两次输出 MD5 相同
- [ ] 50 个场景全部可跑，跑批 < 10 分钟
- [ ] 异常检测在注入故障上的召回 ≥ 85%，误报 ≤ 10%（写进报告）
- [ ] 评测报告含 5 张图 + 1 张基线对比表

### 9.7 常见坑

- ❌ 数据太"干净"→ 异常检测全是 0，演示没东西可看
- ❌ 混合时区/单位（mm vs m，cm vs m）→ 后期到处换算出错
- ❌ 一上来上 LSTM → 训练慢、调不动、答辩讲不清，收益还不如 STL
- ❌ 场景写死在代码里 → 改成 JSON，P2/P3 才能复用

---

## 10. P2 执行手册（平台与后端 · 队长）

### 10.1 你的核心产出

1. `backend/` 17 个接口全绿 + OpenAPI 自动生成
2. 规则引擎（YAML DSL → 安全求值）、告警状态机（表驱动）、审计日志
3. `docker-compose.yml`：`make up` 一条命令起全栈
4. CI 全绿 + 部署文档

### 10.2 规则引擎怎么做

规则用 YAML 存，**编译成 AST 后安全求值，绝不用 `eval`**：

```yaml
- id: R-RAIN-1H-50
  name: 1小时雨量达50mm
  scope: { stationType: rain }
  level: orange
  cooldown: 1800
  when:
    all:
      - { metric: rainfall_1h, op: ">=", value: 50, window: 1h }
  actions: [ create_alert ]
```

实现要点：
- `when` 支持 `all` / `any` 嵌套，操作符白名单 `>= > <= < == between`
- 求值时从 `observations` 拉窗口内数据，**缺数据视为不满足**（不要默认 0）
- 命中后调 `alert_service.create()`，由它做去重/冷却/等级合并
- 规则热加载：管理端改了 `rule` 表 → 发 Redis 事件 → 引擎重载缓存

### 10.3 状态机怎么做（本项目最能体现工程水平的地方）

**表驱动**，一张转移表 + 一个执行器：

```python
TRANSITIONS = {
    ("pending", "confirm"):    ({"operator", "admin"}, "confirmed"),
    ("pending", "expire"):     ({"system"},             "expired"),
    ("pending", "suppress"):   ({"system"},             "suppressed"),
    ("confirmed", "dispatch"): ({"operator", "admin"}, "dispatched"),
    ("dispatched", "close"):   ({"operator", "admin"}, "closed"),
    ("dispatched", "escalate"):({"admin"},              "confirmed"),
    ("*", "cancel"):           ({"admin"},              "cancelled"),
}
```

执行器要求：
- 先校验角色，再校验当前状态，非法转移抛 `409 Conflict`
- 事务内：更新 `alert` + 写 `audit_log` + 发 Redis 事件，**三者原子**
- 幂等：重复 confirm 返回当前状态，不报错

### 10.4 幂等与可靠性

- 所有 POST 支持 `Idempotency-Key`，Redis 存 24h
- 外部调用（LLM/Webhook）统一走 `httpx.AsyncClient`，超时 10s，重试 2 次（指数退避），熔断 3 次
- 后台任务用 `asyncio.Queue` + 单 worker，任务失败进死信表，管理端可重放
- 日志：结构化 JSON，字段 `traceId, actor, action, latencyMs, result`

### 10.5 数据库要点

- 迁移用 Alembic，**每次改表必须有迁移文件**，禁止手改库
- `observation` 表按月分区（可选），至少建 `(station_id, ts DESC)` 复合索引 + `ts` BRIN
- 时间统一 `TIMESTAMPTZ` 存 UTC
- 大字段（evidence/citations）用 `JSONB`，并建 GIN 索引

### 10.6 AI 怎么帮你

| 场景 | 提示词要点 |
|---|---|
| 生成 CRUD | 贴 `openapi.yaml` 的某段 + "按契约实现 router/service/schema，用 SQLAlchemy 2.0 async 写法，返回分页结构" |
| 写迁移 | "为 alert 表加 parent_id 自引用外键，生成 Alembic 迁移，包含 downgrade" |
| 写测试 | "给 state_machine 生成 pytest，覆盖全部合法转移 + 5 个非法转移 + 角色越权" |
| 查坑 | "FastAPI 里 BackgroundTasks 和 APScheduler 同时用会不会重复执行？" |

**AI 高发幻觉区（必须自己验）**：SQLAlchemy 1.x/2.0 写法混用、Pydantic v1/v2 的 `Config` vs `model_config`、Alembic 的 `batch_alter_table`、async session 的生命周期。**每段 AI 代码必须真跑一次**。

### 10.7 验收标准

- [ ] 17 个接口在 Swagger 里可点通，错误码符合约定
- [ ] 状态机单测覆盖全部转移路径，覆盖率 ≥ 90%
- [ ] `make up` 在干净机器上 3 分钟内起全栈
- [ ] 10 万条观测查询 P95 < 200ms
- [ ] CI 全绿，PR 必须过 review

---

## 11. P3 执行手册（Agent 与知识）

### 11.1 你的核心产出

1. `agent/tools/` —— 7 个工具的注册表（含 JSON Schema、超时、是否副作用）
2. `agent/orchestrator.py` —— 编排器（状态机 + 重试 + 超时 + 检查点）
3. `agent/rag/` —— 预案入库、混合检索、引用校验
4. 简报生成（结构化输出 + 校验 + 降级）、`/chat` 对话
5. Prompt 版本库 + 幻觉抽样审计记录

### 11.2 工具清单（先定这 7 个，别贪多）

| 工具 | 作用 | 副作用 | 超时 |
|---|---|---|---|
| `query_stations` | 按流域/类型/bbox 查站点 | 否 | 3s |
| `query_observations` | 查时序/最新值 | 否 | 5s |
| `query_alerts` | 查告警列表/详情 | 否 | 3s |
| `eval_rules` | 对指定站点跑规则（只读，不落库） | 否 | 5s |
| `search_plan` | 检索预案/规范，返回带页码的片段 | 否 | 5s |
| `generate_report` | 生成简报（内部调 LLM） | 否 | 20s |
| `notify_group` | 推送飞书群 | **是** | 10s |

**铁律**：`side_effect=true` 的工具**只能由人工确认后触发**，编排器在自动流程里必须拒绝调用（返回 `NEED_HUMAN_CONFIRM`）。

### 11.3 编排器怎么做

```
PLAN → 选择工具 → 参数校验 → 执行(超时/重试) → OBSERVE → 是否足够?
   ↑                                                      │否，且步数<5
   └──────────────────────────────────────────────────────┘
                        │是
                        ▼
              SYNTHESIZE（LLM 生成）→ VALIDATE（Pydantic）
                        │失败重试≤2
                        ▼
                   DONE / FALLBACK（模板）
```

要求：
- 状态可序列化（存 Redis），**中断可续**（借鉴 LangGraph 的检查点思想）
- 每步写 `trace`：`{step, tool, args, latencyMs, resultSummary}`，前端可展示"AI 的思考过程"（答辩演示很加分）
- 总预算：最多 5 步、总时长 30s，超了直接降级
- 上下文裁剪：只把最近 3 步的完整结果 + 更早的摘要塞进 prompt

### 11.4 简报生成怎么防幻觉（三件套）

1. **工具白名单**：模型只能从注册表里选工具，参数走 JSON Schema 校验
2. **结构化输出**：`BriefingOutput` Pydantic 模型（`conclusion`, `evidence[]`, `suggestions[]`, `citations[]`），校验失败重试 2 次，再失败走模板
3. **引用溯源**：`citations[].quote` 必须能在 `search_plan` 返回的片段里匹配到（相似度 > 0.9），否则删除该引用；引用为空则 `fallback=true`

**Prompt v1 骨架**

```
你是防汛值班研判助手。你的唯一信息来源是下面提供的工具结果与预案片段。
禁止编造：任何不在工具结果中的数值、站点名、阈值，一律不得出现在输出中。
输出必须是合法 JSON，符合 BriefingOutput schema。

【任务】根据以下告警与证据，生成值班简报。
【告警】{alert_json}
【证据】{evidence_json}
【预案片段】{rag_chunks_with_page}
【输出要求】conclusion 不超过 120 字；suggestions 3-5 条，每条以动词开头；citations 只能引用上面给出的片段。
```

### 11.5 RAG 怎么做

- 素材：当地防汛应急预案、排水防涝技术规范、历史灾情通报（PDF/Word）
- 切分：按标题层级切，每块 400–600 字，overlap 80，保留 `docId/title/section/page`
- 向量：`bge-small-zh-v1.5`（轻量够用）或 `bge-m3`；存 pgvector
- 检索：BM25（`rank_bm25`）+ 向量，RRF 融合，取 top 20 → 重排（可用 bge-reranker 或简单规则）→ top 5
- 评测：自建 30 条问答对，算 Recall@5、MRR，写进文档（这条能显著加分）

### 11.6 AI 怎么帮你

| 场景 | 提示词要点 |
|---|---|
| 写工具 | "按这个 JSON Schema 实现工具函数，纯 async，不抛异常只返回 `{ok, data, error}`，超时用 asyncio.wait_for" |
| 调 prompt | "以下是 5 条失败案例，分析失败模式并给出 prompt 修改建议，输出 diff 形式" |
| 造评测集 | "从这份预案生成 30 条问答对，答案必须能在原文定位到页码" |
| 审计幻觉 | 把 30 条输出逐条人工核对，记录"编造数值/张冠李戴/过度推断"三类比例 |

### 11.7 验收标准

- [ ] 20 条固定输入，简报生成成功率 100%（允许 fallback），**零编造数值**
- [ ] 工具调用参数非法时能正确拒绝并重试，不崩
- [ ] 端到端 P95 < 8s（含 1 次工具调用 + 1 次生成）
- [ ] RAG Recall@5 ≥ 0.8
- [ ] 断网时自动切 Ollama，或降级模板，界面有明确提示

---

## 12. P4 执行手册（前端与集成）

### 12.1 你的核心产出

1. 大屏 `/dashboard`（1920×1080，自适应缩放，断网可展示）
2. 告警台 `/alerts`（列表 + 筛选 + 确认/关闭 + 详情抽屉）
3. 站点详情 `/stations/:id`（时序图 + 阈值线 + 异常标注）
4. 规则配置 `/rules`、场景回放 `/scenarios`、对话 `/chat`
5. 飞书卡片推送 + 按钮回调、Playwright E2E 10 条、演示视频

### 12.2 大屏怎么做（这是评分第一眼）

布局（1920×1080）：

```
┌──────────────────────────────────────────────────────────┐
│ 标题栏：FloodSentinel 防汛监测预警   时间  在线状态        │
├───────────────┬──────────────────────────┬───────────────┤
│ 左侧 KPI 卡    │  中部：流域示意图(SVG)     │ 右侧：告警流    │
│ 站点数/超警数  │  站点按等级着色 + 脉冲动画  │ 实时滚动       │
│ 今日告警数     │  点击站点 → 右侧详情        │ 等级色条       │
│ 平均响应时长   │                          │               │
├───────────────┴──────────────────────────┴───────────────┤
│ 底部：24h 雨量柱状图 + 水位折线（双轴）+ 预警等级时间带     │
└──────────────────────────────────────────────────────────┘
```

要点：
- **SVG 流域图自己画**：河道用 path，站点用 circle，不用真实地图也能讲清空间关系，且断网永远能显示
- 颜色规范：蓝 `#1890ff` / 黄 `#faad14` / 橙 `#fa8c16` / 红 `#f5222d`
- 实时：WS 订阅 + 断线重连（指数退避）+ 重连后拉一次 `/metrics/summary` 补状态
- **演示模式**：一个隐藏按钮，一键按 S2 剧本播放（纯前端定时器驱动），现场不怕后端抽风

### 12.3 接口对接要点

- 用 OpenAPI 生成 TS 类型（`openapi-typescript`），**不要手写 interface**
- 统一请求层：超时 10s、错误 toast、401 跳登录、loading 骨架屏
- 所有列表必须有：空态、错误态、加载态（老师会故意点空数据）

### 12.4 飞书卡片

- 群机器人 Webhook 发 `interactive` 卡片：标题 + 等级色 + 3 个字段（站点/指标/时点）+ 两个按钮（确认/忽略）
- 按钮回调走飞书事件订阅 → 打到后端 `/alerts/{id}/confirm`
- 卡片必须含"数据来源：模拟数据"字样（合规）

### 12.5 AI 怎么帮你

| 场景 | 提示词要点 |
|---|---|
| 生成页面 | "用 AntD + ECharts 实现告警列表页，字段按这个 TS 类型，含筛选/分页/详情抽屉，状态用 Tag 着色" |
| 画 SVG | "生成一个 800×500 的流域示意 SVG，3 条支流汇入主河道，8 个站点 circle 带 id，配色克制" |
| 写 E2E | "用 Playwright 写用例：打开大屏 → 断言 KPI 数字存在 → 点第一个告警 → 断言抽屉出现确认按钮" |
| 调样式 | 贴截图 + "这个布局在小屏下溢出，给出修复方案" |

**AI 高发幻觉区**：ECharts 5 的 option 结构（尤其 `dataset`、`markLine`）、AntD 5 的 `Table` 泛型、Leaflet 的 SSR 问题。**跑起来看效果再信**。

### 12.6 验收标准

- [ ] 大屏 1920/1440/1366 三档不溢出，首屏 < 2s
- [ ] 告警产生到屏幕出现 < 3s
- [ ] 断网后大屏仍显示（静态快照兜底）
- [ ] E2E 10 条全绿，演示视频 5 分钟内讲完 3 个场景

---

## 13. AI 协作规范（全组必读）

### 13.1 仓库根目录必须有 `AGENTS.md`

所有 AI 工具（Cursor / Copilot / Claude / ChatGPT）开工前先喂它。内容见仓库 `AGENTS.md`，核心是：技术栈、目录、命令、契约位置、禁止事项、测试要求。

### 13.2 五条 AI 使用纪律

1. **生成的代码必须自己跑通**，且能解释每一行；讲不清就删
2. **契约优先**：让 AI 写实现前，先把它要遵守的 schema/接口贴给它，否则它一定自己发明字段
3. **AI 不碰的三处**：密钥、`main` 分支、数据库迁移（迁移可以 AI 起草，必须人工核对）
4. **PR 里标注 AI 参与度**（`AI-assisted: 70%`），这是诚实也是加分项
5. **版本锁定**：AI 常给过时 API，一律以 `requirements.txt` 锁定的版本为准，不确定就查官方文档

### 13.3 四个万能提示词模板

**① 按契约实现**
```
角色：你是本项目后端工程师。严格遵守以下契约，不得新增/改名任何字段。
契约：<贴 openapi 片段 + Pydantic schema>
现状：<贴相关已有代码>
任务：实现 <函数/路由>，要求：async、错误走统一 error handler、写 docstring。
输出：完整文件内容 + 需要新增的测试用例。
```

**② 补测试**
```
为 <文件> 生成 pytest 用例。要求：
1) 覆盖正常路径 + 边界（0/空/超量程/None/时区缺失）+ 异常路径；
2) 用 pytest.mark.parametrize；
3) 外部依赖一律 mock，不许真连 DB/LLM；
4) 每个用例写一句中文 docstring 说明测什么。
```

**③ 代码审查**
```
审查以下 diff，按严重程度列出问题，只报真问题不要凑数：
[阻断] 会导致错误的；[重要] 安全隐患/性能/契约违背；[建议] 可读性。
每条给出：位置、问题、修复代码。
diff：<贴 diff>
```

**④ 造数据/场景**
```
按以下 schema 生成 N 个 <场景/测试数据>，要求覆盖 <矩阵>，输出纯 JSON 数组，不要解释。
schema：<贴>
约束：<贴阈值表/覆盖要求>
```

### 13.4 每周 AI 复盘（队长主持，15 分钟）

- 本周 AI 生成的代码里，有几处是错的？错在哪类（版本/公式/契约）？
- 把这些"AI 易错点"追加到 `docs/ai/pitfalls.md`，下周喂给 AI
- 这个文件越厚，你们后面越快

---

## 14. 里程碑验收标准

| 里程碑 | 时间 | 硬性标准（达不到就不算过） |
|---|---|---|
| **M0 立项** | W0 末 | 边界文档签字；OpenAPI v0 冻结；仓库能 `make up`；四人各有一个"能跑的东西" |
| **M1 垂直切片** | W2 末 | S2 全链路可录屏：模拟数据→异常→规则→告警→LLM 简报→大屏刷新（IM 可延后） |
| **M2 闭环** | W6 末 | 20 场景跑批出报告；确认/关闭/审计走通；飞书卡片能回写；压测达标 |
| **M3 功能冻结** | W10 末 | 50 场景；RAG 带引用；对话可用；E2E 10 条绿；断网演练通过 |
| **M4 交付** | W13 末 | 文档齐全；干净机器部署成功；演示视频 + PPT 完稿 |
| **答辩** | W14 | 8 分钟讲完 + 3 分钟演示 + 问答不卡壳 |

---

## 15. 风险台账（队长每周更新）

| # | 风险 | 概率 | 影响 | 触发信号 | 预案 | 负责人 |
|---|---|---|---|---|---|---|
| R1 | 数据太假被质疑 | 高 | 高 | 老师问"数据哪来的" | 报告里放模拟器方法论 + 分布校验图，主动说明是合成数据 | P1 |
| R2 | LLM 限额/断网 | 中 | 高 | 调用报 429 | Ollama 本地兜底 + 模板降级 + 预录视频 | P3 |
| R3 | 地图瓦片加载不出 | 中 | 中 | 演示现场白屏 | SVG 兜底（默认方案，Leaflet 只是增强） | P4 |
| R4 | 进度落后 2 周 | 中 | 高 | W4 还没打通链路 | 砍规则配置页、砍对话、砍 MCP，保 S2 | 队长 |
| R5 | 队员只做自己那层，联调崩 | 高 | 中 | 周五集成失败 | 契约先行 + mock server + 周五强制集成 | 队长 |
| R6 | 时序库装不上 | 中 | 低 | docker pull 失败 | 直接用普通 PG + BRIN（已定为首选） | P2 |
| R7 | 告警风暴导致演示难看 | 中 | 中 | 一次回放刷 50 条 | 冷却 + 聚合 + 演示场景限流 | P2 |
| R8 | 队员投入不足 | 中 | 高 | 周产出为空 | 周任务拆到"半天粒度"，队长跟到人 | 队长 |

---

## 16. 第一周就绪清单（逐项打勾）

**第 0 天（半天）**
- [ ] 建群、建仓库、拉四人、开 issue 看板
- [ ] 边界文档定稿，四人回"确认"
- [ ] 分工签字（谁负责哪层，写进 README）

**第 1 天**
- [ ] 队长：`openapi.yaml` v0 写完（17 个接口的壳）
- [ ] P2：`make up` 能起 PG + Redis + FastAPI 空壳
- [ ] P1：模拟器跑出第一个 CSV（哪怕只有雨量）
- [ ] P3：列出 7 个工具的名字和签名（不实现）
- [ ] P4：画出大屏线框图（纸笔拍照即可）

**第 2 天**
- [ ] 全体：过一遍 `AGENTS.md`，各自用 AI 生成第一个模块并跑通
- [ ] 队长：架构图 v0 贴到群里，收集异议

**第 3 天**
- [ ] 四人各交一个"能运行的 30 秒 demo"（录屏或现场）
- [ ] 定下每周五 20:00 集成会（雷打不动）

---

## 附：本手册的修改规则

- 第 2、3、4 章（领域模型/数据契约/接口契约）= 宪法级，改动需**全员同意 + 队长合并**
- 第 8 章（任务表）= 队长每周五可调，调完群发
- 其余章节 = 谁提 PR 谁改，1 人 review 即可
