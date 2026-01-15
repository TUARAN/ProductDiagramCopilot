# 产品智绘官（Product Diagram Copilot）

**产品智绘官** 是一款面向产品科室与业务支撑团队的 AI 产品方案可视化工具，聚焦解决产品方案输出、系统对接说明及结算类业务分析过程中 **流程图、状态图、示意图高度依赖人工绘制、规范难统一、修改成本高** 等问题。

项目基于  **大模型能力（支持 API 调用与本地模型运行）** ，结合业务规则与模板体系，实现从 **文字描述、接口文档与业务数据** 中，自动生成规范化的流程图、时序图、状态图及接入方案，并支持结算类业务数据的周期性可视化展示，辅助产品人员高效完成方案编制与分析工作。

---

## 🎯 项目目标

* 将产品方案中的“画图能力”从人工技能转化为 **可复用、可标准化的系统能力**
* 统一产品方案、系统对接说明中的图形表达规范
* 显著降低产品人员在方案输出、沟通与反复修改中的时间成本

---

## 🧠 AI 能力说明（核心）

产品智绘官内置  **大模型驱动的生成引擎** ，支持以下两种运行模式：

### 模式一：模型 API 调用（默认）

* 可对接：
  * OpenAI / Azure OpenAI
  * DeepSeek / 通义 / 其他企业模型平台
* 适合内网可访问外部 API 或已有模型服务场景
* 优势：部署轻、效果稳定、快速迭代

### 模式二：本地模型运行

* 支持运行  **轻量级指令模型** （如 7B / 8B 级别）
* 典型方案：
  * Ollama / vLLM / LM Studio
  * Qwen / LLaMA / DeepSeek 系列小模型
* 适合内网隔离、数据敏感或算力可控场景

> 无论采用哪种模式，模型统一输出  **结构化中间表示（Diagram Spec JSON）** ，确保生成结果可校验、可编辑、可复用。

---

## 🚀 核心能力

### 1. 文本到产品示意图自动生成

* 支持基于自然语言描述，自动生成：
  * 流程图（Flow）
  * 时序图（Sequence）
  * 状态图（State）
* 覆盖不少于 **3 类产品与系统对接场景**
* 输出结果符合产品方案规范，可直接用于文档与汇报材料

### 2. 接入方案自动生成

* 基于业务流程描述与接口文档（Swagger / 文本）：
  * 自动生成系统接入方案说明
  * 包含角色划分、系统调用链、关键接口说明
* 方案可用率目标 ≥ **80%**

### 3. 结算类业务数据可视化

* 支持结算类业务数据的 **月度周期性图形化展示**
* 覆盖不少于 **5 项核心业务指标**
* 图表生成与数据映射准确率目标 ≥ **95%**

---

## 🏗️ 技术架构

```
[ Web 前端 ]
   │
   ▼
[ FastAPI 后端（编排与权限） ]
   │
   ├─ LLM 编排服务（API / 本地模型）
   ├─ 图规范生成（Diagram Spec）
   ├─ 数据处理与指标计算
   │
   ▼
[ 渲染与任务系统 ]
   ├─ Mermaid / BPMN 渲染
   ├─ Celery 异步任务
   ├─ Redis 队列
   │
   ▼
[ 数据与存储 ]
   ├─ PostgreSQL（业务数据 / 元数据）
   ├─ MinIO（文件与产物）
   └─ pgvector（可选，文档向量检索）
```

---

## 🧰 技术栈

### 前端

* Vue 3 + Vite + TypeScript
* Element Plus / Naive UI
* Mermaid（流程图 / 时序图 / 状态图）
* ECharts（结算数据可视化）

### 后端

* Python FastAPI
* Celery + Redis（异步任务）
* SQLAlchemy / Alembic

### 数据与存储

* PostgreSQL（主数据库）
* Redis（缓存 / 队列）
* MinIO（对象存储）
* pgvector（可选，语义检索）

### 模型运行

* API 模式：HTTP 调用模型服务
* 本地模式：Ollama / vLLM / LM Studio

---

## 📂 项目结构

```
product-diagram-copilot/
├── frontend/                # 前端工作台
├── backend/
│   ├── api/                 # FastAPI 接口
│   ├── llm/                 # 模型调用与 Prompt 编排
│   ├── generator/           # 图与方案生成逻辑
│   ├── renderer/            # Mermaid / BPMN 渲染
│   ├── data_pipeline/       # 结算数据处理
│   ├── jobs/                # Celery 任务
│   └── models/              # ORM 模型
├── templates/               # 业务模板与规范
├── examples/                # 示例输入与输出
├── docker-compose.yml
└── README.md

---

## ✅ 快速开始（本地可运行骨架）

> 说明：当前版本以 **Mock LLM** 默认可跑通端到端（无需 Key）。后续接入真实模型时，只要改 `LLM_MODE` 与相关环境变量。

### 1) 启动依赖（可选，但推荐）

启动 PostgreSQL / Redis / MinIO：

`docker compose up -d`

> 注意：为了避免与本机已有 Postgres 冲突，项目默认将 **宿主机 5433** 映射到容器内 **5432**。
>
> - 默认连接串：`postgresql+psycopg://pdc:pdc@localhost:5433/pdc`
> - 如需改回宿主机 5432：`PDC_PG_PORT=5432 docker compose up -d postgres`，并同步修改 `.env` 中的 `DATABASE_URL`

> 目前接口不强依赖数据库；但后续落地“产物存储/任务队列/元数据”时会用到。

### 2) 启动后端（FastAPI）

推荐（最省心）：

`make backend-pg`

说明：会自动启动 Docker Postgres + 等待就绪 + 迁移 + 启动后端（reload）。

仅启动后端（不管数据库）：

`make backend`

等价命令（不通过 Makefile）：

`python pdc.py api --reload`

健康检查：

`curl http://127.0.0.1:8000/health`

### 3) 启动前端（Vue3 工作台）

`cd frontend`

`npm i`

`npm run dev`

打开：`http://localhost:5173`

或使用脚本：

`./scripts/dev-frontend.sh`

也可以用 Makefile：

`make frontend`

---

## 🖥️ 桌面版（Tauri）

说明：桌面版复用当前前端界面；后端仍以本地 FastAPI 方式运行（默认 `http://localhost:8000`）。

1) 启动后端（任选一种）：

`make backend-pg`

或：

`make backend`

2) 启动桌面端（开发模式）：

`cd frontend`

`npm run tauri:dev`

3) 打包桌面端：

`cd frontend`

`npm run tauri:build`

> 首次打包需要本机安装 Rust 工具链（`rustup`）以及对应平台的构建依赖（Tauri 会在报错信息里提示）。

### 4) 三个核心接口（已实现骨架）

- `POST /api/diagram/generate`：生成 Diagram Spec + Mermaid
- `POST /api/integration/generate`：生成接入方案 Markdown
- `POST /api/settlement/metrics`：计算结算指标（示例口径）

另外提供：

- `POST /api/tasks/diagram`：异步生成图（返回 task_id）
- `POST /api/tasks/integration`：异步生成方案（返回 task_id）
- `GET /api/tasks/{task_id}`：查询任务状态与结果
- `GET /api/artifacts/`：列出已落库产物（需要数据库可用）
- `GET /api/artifacts/{artifact_id}`：查询单个产物

示例输入见 `examples/`。

---

## 🔧 模型切换

后端默认 `LLM_MODE=mock`。

- OpenAI 兼容网关：设置 `LLM_MODE=openai_compat`，并配置 `OPENAI_COMPAT_BASE_URL/OPENAI_COMPAT_API_KEY/OPENAI_COMPAT_MODEL`
  - `OPENAI_COMPAT_BASE_URL` 支持两种形式：`https://xxx` 或 `https://xxx/v1`
  - 例如：`OPENAI_COMPAT_BASE_URL=https://api.gptsapi.net`
  - 如果你的网关使用 `/v1/responses`（例如 gptsapi），设置 `OPENAI_COMPAT_API_STYLE=responses`
  - 建议把环境变量放到 `.env`（项目根目录）或 `backend/.env`（二选一），参考 `backend/.env.example`
- Ollama：设置 `LLM_MODE=ollama`，并配置 `OLLAMA_BASE_URL/OLLAMA_MODEL`

---

## 🧵 异步任务（Celery）

> 需要 Redis 可用（推荐用 docker-compose 启动），并将 `TASK_MODE=celery`。

启动 worker：

`make worker`

等价命令：

`python pdc.py worker`

## 🗄️ 数据库迁移（Alembic）

`make migrate`

等价命令：

`python pdc.py migrate`

---

## 🧯 降级策略（无 Docker 也能跑）

- 默认 `TASK_MODE=inproc`：`/api/tasks/*` 以 **进程内同步执行** 方式运行，并可用 `/api/tasks/{task_id}` 查询结果（仅当前进程内有效）。
- 设置 `TASK_MODE=celery` 且 Redis+worker 可用时：`/api/tasks/*` 使用 Celery 异步执行。
- 未启动 PostgreSQL 时：产物落库与 `/api/artifacts/*` 会返回 `503 database unavailable`（生成接口仍可用）。
- 未启动 MinIO 时：产物上传为 best-effort，失败不影响接口返回。
```

---

## 📈 预期成效指标

* 自动生成图在产品方案中的 **采纳率 ≥ 80%**
* 结算类数据图形化展示准确率 ≥ **95%**
* 产品材料准备效率相较人工方式 **提升 ≥ 30%**

---

## 👥 适用对象

* 产品经理 / 产品科室
* 系统对接与业务支撑人员
* 结算、计费、对账相关产品团队
* 高频输出产品方案与系统说明的内部团队

---

## 📌 项目定位说明

* 本项目不是设计工具替代品
* 而是 **“产品方案生成与表达的 AI 助手”**
* 强调 **规范化、可复用、可审计、可落地**
