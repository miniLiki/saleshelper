# SalesHelper 🚀

SalesHelper 是一个面向企业内部资料的 AI 产品分析推荐系统，适用于产品分析、市场定位、竞品对比和销售辅助场景。

系统支持上传公司产品资料、竞品资料、行业资料和客户案例，通过文档解析、结构化抽取、知识库检索和大模型生成，帮助用户快速获得：

* 产品适合哪些客户
* 产品适合哪些行业和应用场景
* 产品有哪些核心卖点
* 与竞品相比有哪些差异
* 销售人员可以从哪些角度切入
* 资料依据是否充分，哪些结论需要补充证据

项目包含前端页面、后端 API、异步任务、文档解析、结构化抽取、向量检索、图谱索引、Evidence Pack、分析任务和辅助问答等能力。

---

## 1. 技术栈 🧱

后端使用 FastAPI、SQLAlchemy、Celery、LangGraph、Pydantic Settings 和 JWT，负责接口服务、权限控制、任务调度和分析流程编排。

前端使用 React、TypeScript、Vite 和 Ant Design，提供资料上传、产品识别、Evidence Pack、分析任务、辅助问答和管理后台等页面。

文档解析支持 PDF、Word、Excel、PPT、Markdown 和 TXT，主要使用 PyMuPDF、python-docx、openpyxl 和 python-pptx。

知识库与检索层使用 PostgreSQL、Milvus 和 Neo4j。PostgreSQL 用于保存业务数据和文档 chunk，Milvus 用于向量检索，Neo4j 用于产品、行业、竞品和客户案例之间的关系查询。

基础服务包括 PostgreSQL、Redis、MinIO、Milvus 和 Neo4j。

模型接口使用 OpenAI-compatible Chat / Embedding API，默认可接入 ModelScope。

---

## 2. 快速启动 🚀

### 2.1 准备环境变量

先复制环境变量模板：

```bash
cp .env.example .env
```

默认模型配置如下：

```env
OPENAI_BASE_URL=https://api-inference.modelscope.cn/v1/
OPENAI_API_KEY=替换为你的密钥
LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash
CHAT_MODEL=deepseek-ai/DeepSeek-V4-Flash
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
```

如果暂时没有模型 API Key，也可以先运行系统基础流程。系统会自动使用本地降级策略：

* 抽取：使用规则抽取
* embedding：使用确定性哈希向量
* 问答：使用基于证据的模板化回答

也就是说，没有配置模型密钥时，系统仍然可以上传资料、解析文档、生成 chunk、查看基础检索和问答结果。

如果需要使用真实远程 embedding，请确认当前网关支持配置的 `EMBEDDING_MODEL`。如果 ModelScope 网关拒绝当前 embedding 模型 ID，系统会自动回退到本地 512 维向量。

---

## 3. Docker 启动方式 🐳

推荐使用 Docker 启动完整环境。

### 3.1 启动基础服务

```bash
docker compose -f infra/docker-compose.yml up -d postgres redis minio etcd milvus neo4j
```

### 3.2 构建后端、Worker 和前端

```bash
docker compose -f infra/docker-compose.yml build backend worker frontend
```

### 3.3 启动应用服务

```bash
docker compose -f infra/docker-compose.yml up -d backend worker frontend
```

### 3.4 初始化数据库

```bash
docker compose -f infra/docker-compose.yml exec backend alembic upgrade head
docker compose -f infra/docker-compose.yml exec backend python -m app.db.init_db
```

---

## 4. 访问地址 🌐

启动完成后，可以访问以下地址：

| 服务            | 地址                         |
| ------------- | -------------------------- |
| 前端页面          | http://localhost:5173      |
| 后端 API        | http://localhost:8000      |
| API 文档        | http://localhost:8000/docs |
| PostgreSQL    | localhost:15432            |
| MinIO 控制台     | http://localhost:9001      |
| Neo4j Browser | http://localhost:7474      |

默认管理员账号：

```text
admin / admin123456
```

---

## 5. 本地开发启动方式 🛠️

如果不使用 Docker 运行应用，也可以分别启动后端、Worker 和前端。

### 5.1 启动后端

```bash
cd backend
python3 -m venv ../.venv
source ../.venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.db.init_db
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5.2 启动 Worker

```bash
cd backend
source ../.venv/bin/activate
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO
```

### 5.3 启动前端

```bash
cd frontend
npm install
npm run dev
```

---

## 6. 推荐使用流程 🧭

SalesHelper 的典型使用流程如下：

```text
登录系统
  ↓
上传产品资料 / 竞品资料 / 行业资料 / 客户案例
  ↓
系统解析文档并生成 chunk
  ↓
结构化抽取产品、卖点、参数、行业、竞品和客户案例信息
  ↓
生成 embedding，并写入检索索引
  ↓
用户输入产品名称或问题
  ↓
系统检索 Evidence Pack
  ↓
生成产品分析、竞品对比、销售建议或辅助问答结果
```

---

## 7. 主要功能 ✨

### 7.1 资料接入与解析 📄

前端入口：上传资料

支持上传以下类型的资料：

* PDF
* Word `.docx`
* Excel
* PPT `.pptx`
* Markdown
* TXT

上传资料后，系统会通过 Celery 异步执行解析、抽取和索引流程。

如果 Worker 没有启动，也可以进入资料详情页，手动点击“解析 / 抽取 / 索引”。

解析和处理结果会写入：

* `document_chunks`
* `extraction_candidates`
* 产品、参数、卖点、行业、竞品、客户案例、销售材料等知识表
* chunk embedding
* `knowledge_relations`

---

### 7.2 产品识别 🔎

前端入口：产品识别

接口：

```http
POST /api/products/identify
```

产品识别支持：

* 产品名称匹配
* 产品型号匹配
* 产品别名匹配
* 包含匹配
* 模糊匹配

如果没有命中已有产品，系统可以创建临时产品对象，方便后续继续执行分析任务。

---

### 7.3 Evidence Pack 🧩

前端入口：Evidence Pack

接口：

```http
POST /api/retrieval/evidence-pack
```

Evidence Pack 用于为分析任务和辅助问答准备证据材料。系统会综合多种检索信号，尽量让模型基于可靠资料回答。

检索来源包括：

* PostgreSQL chunk 检索
* 关键词匹配
* embedding 相似度
* Milvus 向量检索
* Neo4j 图谱关系
* 资料可信等级
* 产品、行业和竞品过滤条件

管理后台支持重建和验证 Milvus collection 与 Neo4j 图谱索引。

---

### 7.4 分析任务 📊

前端入口：分析任务

相关接口：

```http
POST /api/analysis-tasks
GET  /api/analysis-tasks
GET  /api/analysis-tasks/{id}
POST /api/analysis-tasks/{id}/run
POST /api/analysis-tasks/{id}/retry
```

分析任务用于把产品识别、证据检索、质量检查和报告生成串成一个完整流程。

当前工作流节点：

```text
product_identification
-> evidence_pack
-> quality_check
-> report_stub
```

每个节点都会保存：

* 执行状态
* 输入参数
* 输出结果
* 错误信息
* 耗时字段

任务执行引擎使用 LangGraph `StateGraph`。任务完成后，`result_json.engine` 会记录为 `langgraph`。

---

### 7.5 辅助问答 💬

前端入口：辅助问答

接口：

```http
POST /api/chat
```

辅助问答会基于 Evidence Pack 的召回结果进行回答，而不是直接让模型自由发挥。

系统会保存：

* conversation
* user message
* assistant message
* citations
* retrieval debug

回答内容会区分：

* 事实
* 分析
* 推测
* 建议
* 资料缺口

这样可以减少模型编造，让业务人员知道哪些结论有资料依据，哪些地方还需要补充材料。

---

### 7.6 管理后台 ⚙️

前端入口：管理后台

管理后台主要用于查看资料处理状态、审核抽取结果、重建索引和验证索引状态。

当前包含：

* ingestion jobs 查看
* extraction candidates 列表
* extraction candidates 确认
* extraction candidates 忽略
* Milvus / Neo4j 索引重建
* Milvus / Neo4j 索引验证

管理接口：

```http
GET  /api/admin/ingestion-jobs
GET  /api/admin/extraction-candidates
POST /api/admin/extraction-candidates/{id}/confirm
POST /api/admin/extraction-candidates/{id}/ignore
POST /api/admin/indexes/rebuild
GET  /api/admin/indexes/verify
```

---

## 8. 核心 API 清单 🔌

### 8.1 登录与健康检查

```http
POST /api/auth/login
GET  /api/me
GET  /api/health
```

### 8.2 资料管理

```http
POST /api/documents
GET  /api/documents
GET  /api/documents/{id}
POST /api/documents/{id}/parse
POST /api/documents/{id}/process
```

### 8.3 产品与识别

```http
GET  /api/products
POST /api/products/identify
```

### 8.4 检索与证据包

```http
POST /api/retrieval/evidence-pack
```

### 8.5 分析任务

```http
POST /api/analysis-tasks
GET  /api/analysis-tasks
GET  /api/analysis-tasks/{id}
POST /api/analysis-tasks/{id}/run
POST /api/analysis-tasks/{id}/retry
```

### 8.6 辅助问答

```http
POST /api/chat
```

### 8.7 管理后台

```http
GET  /api/admin/ingestion-jobs
GET  /api/admin/extraction-candidates
POST /api/admin/extraction-candidates/{id}/confirm
POST /api/admin/extraction-candidates/{id}/ignore
POST /api/admin/indexes/rebuild
GET  /api/admin/indexes/verify
```

---

## 9. 测试与构建 ✅

### 9.1 后端测试

```bash
cd backend
source ../.venv/bin/activate
pytest
```

### 9.2 前端构建

```bash
cd frontend
npm run build
npm audit
```

如果前端构建时提示主 bundle 超过 500 kB，说明后续可以继续做 code splitting 优化，不影响基础运行。

---

## 10. 功能边界与注意事项 💡

Milvus 和 Neo4j 是正式外部索引。当 `ENABLE_MILVUS=true` 或 `ENABLE_NEO4J=true` 时，如果索引重建失败，对应的 ingestion job 会失败。

`ENABLE_MILVUS_LITE_FALLBACK=false` 是默认配置。只有显式开启时，系统才会使用本地 Milvus Lite。

当前 Evidence Pack 暂未接入独立 reranker 模型，排序主要综合 embedding 相似度、关键词匹配、Milvus 命中、图谱关系、可信等级和过滤条件。

OCR 暂未实现。图片型 PDF 依赖 PyMuPDF 可提取文本的结果，如果 PDF 是纯扫描图片，可能需要先用外部 OCR 工具转成可复制文本。

Word 仅支持 `.docx`，PPT 仅支持 `.pptx`。

结构化抽取支持 LLM JSON 输出，同时保留规则抽取回退。复杂字段建议在管理后台进行人工审核。

当前分析任务已经支持产品识别、Evidence Pack、质量检查和报告草稿节点。完整的市场分析、竞品分析和销售策略正式报告可以继续在后续工作流节点中扩展。

---

## 11. 常见问题 ❓

### 没有配置模型 API Key，可以运行吗？

可以。系统会自动使用本地降级策略，保证基础流程可运行。

### 为什么问答结果比较模板化？

通常是因为没有配置可用的远程 LLM，或者模型接口调用失败。配置 `OPENAI_API_KEY` 和可用模型后，可以获得更完整的生成结果。

### 为什么 embedding 使用了本地向量？

可能是没有配置 `OPENAI_API_KEY`，也可能是当前网关不支持配置的 `EMBEDDING_MODEL`。可以将 `EMBEDDING_MODEL` 替换为网关实际支持的 embedding 模型。

### 上传资料后没有自动解析怎么办？

先确认 Worker 是否启动。如果 Worker 没有启动，可以进入资料详情页手动执行“解析 / 抽取 / 索引”。

### Milvus 或 Neo4j 索引异常怎么办？

可以进入管理后台，使用索引重建和索引验证功能检查状态。
