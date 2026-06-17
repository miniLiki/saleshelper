# 周期 2-6 系统设计

本文档描述 SalesHelper 周期 2-6 的发行版设计，覆盖文档解析、结构化抽取、向量索引、图谱关系、产品识别、Evidence Pack、分析工作流和辅助问答。

## 1. 设计目标

- PostgreSQL 保存全部业务事实、审核状态和任务状态，是唯一事实源。
- Milvus 和 Neo4j 是可从 PostgreSQL 重建的外部索引，不作为业务事实源。
- 文档解析、结构化抽取、embedding、Milvus 重建和 Neo4j 重建必须进入同一条可追踪 ingestion 链路。
- 分析任务使用 LangGraph 编排，节点输入、输出、状态、错误和耗时全部落库。
- Evidence Pack 必须合并 PostgreSQL、关键词、embedding、Milvus 和图谱信号，并保留检索 debug。
- 如果配置启用外部 Milvus/Neo4j，索引重建失败时 ingestion job 失败，不再静默降级。

## 2. 数据层

PostgreSQL 表分为五组：

- 资料层：`documents`、`document_versions`、`document_chunks`、`ingestion_jobs`
- 知识层：`products`、`product_aliases`、`product_models`、`product_parameters`、`selling_points`、`industries`、`scenarios`、`pain_points`、`customer_cases`、`sales_materials`、`competitors`、`competitor_products`、`competitor_parameters`
- 抽取审核层：`extraction_candidates`
- 关系层：`knowledge_relations`
- 分析层：`analysis_tasks`、`analysis_task_steps`、`evidence_items`、`conversations`、`messages`、`citations`

Alembic 迁移：

- `0001_initial.py`：周期 0-1 基础用户、权限、资料表
- `0002_cycles_2_6.py`：周期 2-6 知识库、证据、任务和会话表

## 3. 文档处理链路

入口：

- `POST /api/documents/{id}/parse`
- `POST /api/documents/{id}/process`
- Celery worker 可异步调用同一服务逻辑

处理顺序：

```text
原始文件
-> parse_document_bytes
-> split_into_chunks
-> document_chunks
-> extract_document_chunks
-> extraction_candidates
-> 自动应用高置信候选到正式知识表
-> embed_chunks
-> rebuild_knowledge_relations
-> rebuild_milvus
-> rebuild_neo4j
```

解析格式：

- PDF：PyMuPDF
- Word：python-docx，支持 `.docx`
- Excel：openpyxl，保留 sheet 和表格上下文
- PPT：python-pptx，支持 `.pptx`，提取页面文字和备注
- Markdown/TXT：按标题、段落切分

失败策略：

- 解析、抽取、索引各自写入 `ingestion_jobs`
- 任一阶段异常会记录 `error_message`
- 当 `ENABLE_MILVUS=true` 或 `ENABLE_NEO4J=true` 时，对应外部索引重建失败会使索引阶段失败

## 4. 结构化抽取

抽取服务会优先调用 OpenAI-compatible LLM JSON 输出，并通过规则抽取作为无模型环境的后备路径。

候选类型：

- `product`
- `product_parameter`
- `selling_point`
- `industry`
- `competitor`
- `competitor_product`
- `customer_case`
- `sales_material`

每个候选保存：

- `candidate_type`
- `payload_json`
- `source_chunk_id`
- `document_id`
- `confidence`
- `extraction_version`
- `status`
- `reviewed_by`

管理员可通过后台确认或忽略候选。确认后写入正式知识表；正式知识表中人工确认字段优先，不被自动抽取覆盖。

## 5. Milvus 向量索引

Milvus collection：

```text
document_chunks
```

字段：

- `chunk_id`：主键
- `document_id`
- `trust_level`
- `content`
- `embedding`

重建入口：

- `POST /api/admin/indexes/rebuild`

验证入口：

- `GET /api/admin/indexes/verify`

验证内容：

- collection 是否存在
- 实体数量
- 使用真实 chunk embedding 执行一次 search
- 返回 search 状态和命中数量

`ENABLE_MILVUS_LITE_FALLBACK=false` 是发行默认值。只有显式打开该开关时，外部 Milvus 不可用才会写入本地 Milvus Lite。

## 6. Neo4j 图谱索引

节点：

- `Product`
- `ProductParameter`
- `Competitor`
- `CompetitorProduct`
- `Industry`
- `Scenario`
- `PainPoint`
- `SellingPoint`
- `CustomerCase`
- `SalesMaterial`
- `Document`
- `Chunk`

关系：

- `HAS_CHUNK`
- `MENTIONS`
- `APPLIES_TO`
- `USED_IN`
- `SOLVES`
- `HAS_PARAMETER`
- `HAS_SELLING_POINT`
- `HAS_CASE`
- `HAS_PRODUCT`
- `COMPETES_WITH`

Neo4j 可从 PostgreSQL 全量重建。管理后台验证接口会返回节点数和关系数。

## 7. Evidence Pack

入口：

- `POST /api/retrieval/evidence-pack`

召回和排序信号：

- PostgreSQL chunk 范围筛选
- 关键词命中
- PostgreSQL 保存的 embedding 相似度
- Milvus search 命中分
- PostgreSQL 图谱关系 chunk hint
- 资料可信等级
- 产品、行业、竞品过滤加权

输出分组：

- `product_facts`
- `industry_materials`
- `customer_cases`
- `competitor_materials`
- `sales_materials`
- `general`

每条证据包含：

- 引用编号
- 来源资料
- 来源 chunk
- 页码或 sheet
- 可信等级
- 排序分
- 检索 debug

## 8. LangGraph 分析工作流

分析任务入口：

- `POST /api/analysis-tasks`
- `POST /api/analysis-tasks/{id}/run`
- `POST /api/analysis-tasks/{id}/retry`

工作流引擎：

```text
LangGraph StateGraph
```

节点：

```text
product_identification
-> evidence_pack
-> quality_check
-> report_stub
```

每个节点写入 `analysis_task_steps`：

- `input_json`
- `output_json`
- `status`
- `error_message`
- `started_at`
- `finished_at`

任务完成后 `analysis_tasks.result_json.engine = "langgraph"`。

## 9. 辅助问答

入口：

- `POST /api/chat`

问答基于 Evidence Pack 召回结果生成回答，并保存：

- 会话
- 用户消息
- 助手消息
- 引用证据
- 检索 debug

回答结构区分：

- 事实
- 分析
- 推测
- 建议
- 资料缺口

## 10. 运维验证

基础健康：

- `GET /api/health`

索引重建：

- `POST /api/admin/indexes/rebuild`

索引验证：

- `GET /api/admin/indexes/verify`

推荐验收顺序：

```text
docker compose up 基础服务
-> alembic upgrade head
-> python -m app.db.init_db
-> 上传样例资料
-> /api/documents/{id}/process
-> /api/admin/indexes/verify
-> /api/retrieval/evidence-pack
-> /api/analysis-tasks/{id}/run
-> /api/chat
```
