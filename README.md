# SalesHelper

SalesHelper 是一个内部 AI 产品分析推荐系统。当前发行版覆盖 `docs/task-cycles.md` 中的周期 0-6：

- 周期 0-1：项目骨架、基础设施、登录鉴权、角色权限、资料上传和资料管理。
- 周期 2-4：文档解析、chunk 切分、结构化抽取、embedding、检索索引和 Neo4j/Milvus 重建入口。
- 周期 5-6：产品识别、Evidence Pack、分析任务工作流和辅助问答。

周期 2-6 的详细系统设计见 [docs/cycles-2-6-system-design.md](docs/cycles-2-6-system-design.md)。

## 1. 技术栈

- 后端：FastAPI、SQLAlchemy、Celery、LangGraph、Pydantic Settings、JWT
- 文档解析：PyMuPDF、python-docx、openpyxl、python-pptx
- 模型接口：OpenAI-compatible Chat/Embedding API
- 检索与图谱：PostgreSQL 主存储、Milvus 向量索引、Neo4j 图谱索引
- 前端：React、TypeScript、Vite、Ant Design
- 基础服务：PostgreSQL、Redis、MinIO、Milvus、Neo4j

## 2. 环境变量

```bash
cp .env.example .env
```

模型默认按 ModelScope OpenAI-compatible API 配置：

```env
OPENAI_BASE_URL=https://api-inference.modelscope.cn/v1/
OPENAI_API_KEY=替换为你的密钥
LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash
CHAT_MODEL=deepseek-ai/DeepSeek-V4-Flash
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
```

如果没有配置 `OPENAI_API_KEY`，系统会使用本地降级策略：

- 抽取：规则抽取。
- embedding：确定性哈希向量。
- 问答：基于证据的模板化回答。

代码按 OpenAI-compatible 协议调用 ModelScope 的 `chat/completions` 与 `embeddings` 端点。若外部模型接口不可用、未配置密钥，或 embedding 网关拒绝当前模型 ID，系统会自动降级到本地 512 维确定性向量与模板化回答；如需真实远程 embedding，请将 `EMBEDDING_MODEL` 替换为该网关实际支持的模型名。

## 3. Docker 启动

```bash
docker compose -f infra/docker-compose.yml up -d postgres redis minio etcd milvus neo4j
docker compose -f infra/docker-compose.yml build backend worker frontend
docker compose -f infra/docker-compose.yml up -d backend worker frontend
docker compose -f infra/docker-compose.yml exec backend alembic upgrade head
docker compose -f infra/docker-compose.yml exec backend python -m app.db.init_db
```

访问地址：

- 前端：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs
- PostgreSQL：localhost:15432
- MinIO 控制台：http://localhost:9001
- Neo4j Browser：http://localhost:7474

默认管理员：

```text
admin / admin123456
```

## 4. 本地开发启动

后端：

```bash
cd backend
python3 -m venv ../.venv
source ../.venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.db.init_db
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Worker：

```bash
cd backend
source ../.venv/bin/activate
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## 5. 主要功能

### 资料接入与解析

1. 在前端登录。
2. 进入“上传资料”，上传 PDF、Word、Excel、PPT、Markdown 或 TXT。
3. 上传后系统会尝试通过 Celery 异步执行解析、抽取和索引。
4. 如果 Worker 未运行，可进入资料详情页点击“解析/抽取/索引”手动执行。

解析结果会写入：

- `document_chunks`
- `extraction_candidates`
- 产品、参数、卖点、行业、竞品、客户案例、销售材料等知识表
- chunk embedding
- `knowledge_relations`

### 产品识别

前端入口：“产品识别”。

API：

```http
POST /api/products/identify
```

支持产品名称、型号、别名/包含匹配、模糊匹配。未命中时可创建临时产品对象。

### Evidence Pack

前端入口：“Evidence Pack”。

API：

```http
POST /api/retrieval/evidence-pack
```

检索会合并：

- PostgreSQL chunk 检索
- 关键词匹配
- embedding 相似度
- Milvus search 命中
- 图谱关系信号
- 可信等级权重
- 产品/行业/竞品过滤

可通过管理后台重建并验证 Milvus collection 与 Neo4j 图谱。

### 分析任务

前端入口：“分析任务”。

API：

```http
POST /api/analysis-tasks
GET  /api/analysis-tasks
GET  /api/analysis-tasks/{id}
POST /api/analysis-tasks/{id}/run
POST /api/analysis-tasks/{id}/retry
```

当前工作流节点：

```text
product_identification
-> evidence_pack
-> quality_check
-> report_stub
```

每个节点都会保存状态、输入、输出、错误和耗时字段。
任务执行引擎为 LangGraph `StateGraph`，完成后 `result_json.engine` 会记录为 `langgraph`。

### 辅助问答

前端入口：“辅助问答”。

API：

```http
POST /api/chat
```

问答会基于 Evidence Pack 召回结果回答，并保存：

- conversation
- user/assistant message
- citations
- retrieval debug

输出要求区分事实、分析、推测、建议和资料缺口。

### 管理后台

前端入口：“管理后台”。

当前包含：

- ingestion jobs 查看
- 后端 API 提供 extraction candidates 列表、确认、忽略接口
- 后端 API 提供索引重建和验证接口

管理 API：

```http
GET  /api/admin/ingestion-jobs
GET  /api/admin/extraction-candidates
POST /api/admin/extraction-candidates/{id}/confirm
POST /api/admin/extraction-candidates/{id}/ignore
POST /api/admin/indexes/rebuild
GET  /api/admin/indexes/verify
```

## 6. 核心 API 清单

```http
POST /api/auth/login
GET  /api/me
GET  /api/health

POST /api/documents
GET  /api/documents
GET  /api/documents/{id}
POST /api/documents/{id}/parse
POST /api/documents/{id}/process

GET  /api/products
POST /api/products/identify

POST /api/retrieval/evidence-pack

POST /api/analysis-tasks
GET  /api/analysis-tasks
GET  /api/analysis-tasks/{id}
POST /api/analysis-tasks/{id}/run
POST /api/analysis-tasks/{id}/retry

POST /api/chat

GET  /api/admin/ingestion-jobs
GET  /api/admin/extraction-candidates
POST /api/admin/extraction-candidates/{id}/confirm
POST /api/admin/extraction-candidates/{id}/ignore
POST /api/admin/indexes/rebuild
GET  /api/admin/indexes/verify
```

## 7. 测试与构建

后端：

```bash
cd backend
source ../.venv/bin/activate
pytest
```

前端：

```bash
cd frontend
npm run build
npm audit
```

当前验证结果：

- 后端测试：`7 passed`
- Alembic 空库升级：通过，覆盖周期 0-6 表结构
- 前端构建：通过
- 前端构建提示：主 bundle 超过 500 kB，属于后续 code splitting 优化项
- 前端依赖审计：`0 vulnerabilities`

## 8. 外部服务与后续工作

- 分析任务已接入 LangGraph `StateGraph`，任务结果中会记录 `engine=langgraph`。
- Milvus 和 Neo4j 是正式外部索引；当 `ENABLE_MILVUS=true` 或 `ENABLE_NEO4J=true` 时，索引重建失败会使 ingestion job 失败。
- 管理后台提供索引重建和索引验证；验证接口会检查 Milvus collection/search 与 Neo4j 节点/关系计数。
- 当前执行环境的 Docker daemon 在 `docker info` 的 Server 阶段超时，无法在本机完成容器级 Milvus/Neo4j 端到端验证；代码路径和验证接口已具备，部署环境恢复 Docker 后可按系统设计文档验收。
- `ENABLE_MILVUS_LITE_FALLBACK=false` 是默认发行配置；只有显式打开时才会使用本地 Milvus Lite。
- reranker 未接入独立模型；Evidence Pack 使用 embedding 相似度、关键词、Milvus 命中、图谱关系、可信等级和过滤条件综合排序。
- 若 ModelScope embedding 网关拒绝 `BAAI/bge-small-zh-v1.5`，系统会使用本地回退 embedding。
- OCR 未实现；图片型 PDF 会依赖 PyMuPDF 可提取文本的结果。
- Word 仅支持 `.docx`，PPT 仅支持 `.pptx`。
- 结构化抽取支持真实 LLM JSON 输出，同时保留规则抽取回退；复杂字段仍需要管理员审核。
- 分析任务已实现产品识别、Evidence Pack、质量检查和 `report_stub`，尚未生成周期 7-12 所需的完整市场、竞品、销售策略正式报告。
