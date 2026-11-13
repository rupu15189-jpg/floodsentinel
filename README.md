# FloodSentinel · 防汛监测预警智能体平台

> 把「雨量水位数据 → 规则研判 → 分级预警 → 值班简报 → 消息推送 → 大屏展示」做成一条能跑通、能演示、能复盘的链路。

**当前状态：W1 骨架版** —— 后端 9 个接口全部可用，数据库 5 张表，种子数据 48 小时，18 条冒烟测试全绿。

---

## 1. 快速开始（3 分钟）

```bash
# 1) 装依赖（建议先建虚拟环境）
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

# 2) 启动（首次启动会自动建表并灌种子数据）
cd backend
uvicorn app.main:app --reload --port 8000
```

打开：

- 接口文档（可在线调试）：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/api/health>

看到 `{"status":"ok","stations":8}` 就说明环境通了。

> 没有 `make`、没有 conda 都不影响，上面三条命令就够了。

---

## 2. 目录结构

```
floodsentinel/
├── backend/
│   ├── app/
│   │   ├── main.py           # 入口：建表 → 灌数据 → 挂路由
│   │   ├── config.py         # 配置（只读环境变量，不硬编码）
│   │   ├── db.py             # 连接与会话
│   │   ├── models.py         # 5 张表
│   │   ├── schemas.py        # 接口出入参（= 对前端的契约）
│   │   ├── seed.py           # 种子数据（确定性）
│   │   ├── timeutil.py       # 时区唯一转换点
│   │   ├── errors.py         # 统一异常
│   │   └── routers/          # stations / alerts / reports / scenarios
│   ├── tools/                # 导出 openapi、schema、示例 JSON
│   └── tests/test_api.py     # 冒烟测试（不装 pytest 也能跑）
├── data/
│   ├── schema.sql            # 自动生成，勿手改
│   └── floodsentinel.db      # 运行时生成，已 gitignore
├── docs/
│   ├── api/openapi.yaml      # 自动生成的接口契约
│   ├── examples/*.json       # 前端 mock 用
│   ├── tasks/队长任务表.csv
│   └── 防汛监测预警智能体平台-项目说明与分工.docx
├── requirements.txt
└── Makefile
```

---

## 3. 接口清单（v1，第 1 周冻结）

| # | 方法 | 路径 | 说明 |
|---|---|---|---|
| 1 | GET | `/api/stations` | 站点列表，支持 `basin_id` / `type` 筛选 |
| 2 | GET | `/api/stations/{id}/observations` | 时序数据，参数 `from` / `to` / `metric` / `limit` |
| 3 | GET | `/api/observations/latest` | 多站点最新值，`station_ids=R-001,L-001` |
| 4 | GET | `/api/alerts` | 告警列表，`status` / `level` / 分页 |
| 5 | POST | `/api/alerts/{id}/confirm` | 人工确认（`pending → confirmed`） |
| 6 | POST | `/api/alerts/{id}/close` | 关闭告警（`pending/confirmed → closed`） |
| 7 | POST | `/api/reports/generate` | 生成值班简报（当前为模板版） |
| 8 | GET | `/api/scenarios` | 场景列表 |
| 9 | POST | `/api/scenarios/{id}/replay` | 触发场景回放 |
| — | GET | `/api/health` | 健康检查（非业务接口） |

契约由 `backend/tools/dump_openapi.py` 从代码自动导出，**文档永远等于代码**，不会出现"改了代码忘了改文档"。

---

## 4. 数据说明

种子数据是**确定性**的：固定随机种子 + 固定时间锚点 `2026-07-19 00:00`（东八区），48 小时、5 分钟粒度，共 4608 条观测。

- 一场约 2 小时的暴雨过程，雨量钟形分布，水位滞后 40 分钟响应
- 8 个站点：3 个雨量站、3 个水位站、2 个积水点
- 2 条告警：`AL-20260720-0001`（橙色，待确认）、`AL-20260720-0002`（黄色，已确认）
- 故意埋了脏数据：`L-003` 有 30 分钟卡死（`quality=suspect`），用来演示数据质检

想清空重来：删掉 `data/floodsentinel.db` 再启动即可。

> 真正的模拟器由黄锰猛在 W1 重写，这里只是让接口有数据可返回。

---

## 5. 三条硬约定（改代码前先看）

1. **字段一律 snake_case**，时间一律 ISO8601 带 `+08:00`。库里存 UTC，出参转东八区——转换只在 `app/timeutil.py` 一处做。
2. **错误统一长这样**：`{"code": "ALERT_STATE_CONFLICT", "message": "...", "trace_id": "..."}`。业务代码只抛 `AppError`。
3. **接口先改契约，再改实现**。改 `openapi.yaml` 由队长合并并通知全员。

---

## 6. 常用命令

```bash
cd backend

# 跑冒烟测试（不需要 pytest）
python tests/test_api.py

# 有 pytest 的话
pytest tests -q

# 重新导出契约 / 建表 SQL / 示例 JSON
python tools/dump_openapi.py
python tools/dump_schema.py
python tools/dump_examples.py
```

---

## 7. W1 完成度与下一步

| 事项 | 状态 |
|---|---|
| 仓库骨架、目录、依赖锁定 | ✅ |
| 5 张表 + 建表脚本 | ✅ |
| 9 个接口 + 统一错误格式 + CORS | ✅ |
| 确定性种子数据（8 站 / 48h / 2 告警 / 2 场景） | ✅ |
| 冒烟测试 12 项全绿 | ✅ |
| 前端 mock 数据（`docs/examples/`） | ✅ |
| 规则引擎（阈值研判自动生成告警） | ⬜ W2 |
| 真正的场景回放（按时间轴重演） | ⬜ W5 |
| LLM 简报（替换模板版） | ⬜ W3 |

**对接说明**

- 胡子妍：先吃 `docs/examples/*.json`，接口按第 3 节写，CORS 已放开 `localhost:5173`。
- 黄锰猛：`observation` 表结构与 `metric` 取值已定（`rainfall_1h` / `water_level` / `water_depth`），你的模拟器直接往这 3 个 metric 写。
- 李宇露：`POST /api/reports/generate` 的出入参已冻结，你把 `_render()` 换成 LLM 调用即可，前端不用改。
