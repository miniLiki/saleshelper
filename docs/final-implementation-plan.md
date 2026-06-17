# AI 产品分析推荐系统最终实施方案

## 1. 项目目标

本项目建设一个面向公司内部产品分析、市场定位、竞品情报和销售辅助的完整业务系统。系统以公司产品资料、销售资料、客户案例、行业资料和竞品资料为可信知识源，结合 PostgreSQL 结构化主数据、Milvus 向量检索、Neo4j 业务关系图谱和大模型分析生成能力，形成可持续运营的产品分析与销售推荐平台。

系统目标不是做一个“可信问答 MVP”，也不是只完成资料上传后回答问题。问答能力只是底层证据检索和解释能力的一种交互形式，项目主线应围绕完整业务闭环建设：

```text
产品输入 / 资料上传
-> 产品识别与分析任务创建
-> 产品知识库检索
-> 目标市场分析
-> 竞品对比分析
-> 竞品动态沉淀
-> 销售推荐策略
-> 结构化报告输出
-> 人工反馈与知识运营
```

系统完成后应支持以下核心业务能力：

- 用户输入产品名称、型号，或上传产品资料后，系统自动识别产品对象并创建分析任务。
- 系统从产品资料库、客户案例库、行业资料库和竞品资料库中检索证据，形成可追溯的 evidence pack。
- 系统分析产品适合的目标行业、目标客户、典型应用场景、客户痛点和市场进入策略。
- 系统完成我方产品与竞品的结构化对比，输出差异化卖点、风险提示和销售反驳话术。
- 系统将竞品新闻、官网资料、销售反馈和行业文章抽取为竞品事件，形成可持续沉淀的竞品动态库。
- 系统生成客户画像、客户适配度评分、销售切入点、拜访问题、推荐话术和推荐销售材料。
- 系统输出结构化产品分析报告，并支持引用来源展示、历史报告管理和导出。

所有事实性结论必须能够追溯到资料来源；没有证据支撑的内容必须标注为推测、建议或资料不足。

## 2. 建设原则

- 以业务分析流程为主线，不以自由聊天或单点问答作为项目终点。
- PostgreSQL 作为唯一业务事实源，Milvus 和 Neo4j 作为可重建索引。
- 产品、参数、客户案例、竞品、行业、销售建议和报告结论都必须绑定证据来源。
- 自动抽取结果作为候选知识，必须支持管理员审核、修正、确认和回滚。
- 分析流程必须拆解为多个可追踪节点，避免一个 Prompt 直接生成整份报告。
- 回答和报告必须区分事实、分析、推测、建议和资料缺口。
- 资料不足时必须输出缺口清单，不能编造参数、价格、客户案例、市场份额或竞品结论。
- 首个可交付版本必须打通“资料接入 -> 知识库 -> 市场分析 -> 竞品分析 -> 销售推荐 -> 报告输出”的完整闭环。
- 外部市场数据采集可分阶段建设，但数据结构、事件模型和扩展接口需在前期预留。

## 3. 总体架构

系统采用前后端分离、多存储协同和工作流编排架构。

```text
Frontend
  -> 产品输入
  -> 资料管理
  -> 分析任务
  -> 报告工作台
  -> 竞品动态
  -> 知识维护
  -> 管理后台

API Gateway / FastAPI
  -> Auth Service
  -> Document Service
  -> Product Service
  -> Knowledge Service
  -> Retrieval Service
  -> Workflow Service
  -> Analysis Service
  -> Report Service
  -> Feedback Service
  -> Celery Workers

Workflow Layer
  -> Product Identification Flow
  -> Evidence Pack Flow
  -> Market Analysis Flow
  -> Competitor Analysis Flow
  -> Competitor Event Flow
  -> Sales Strategy Flow
  -> Report Generation Flow

Storage
  -> PostgreSQL
  -> Redis
  -> MinIO
  -> Milvus
  -> Neo4j

Model Layer
  -> Chat Model
  -> Embedding Model
  -> Reranker Model
  -> Extraction Prompts
  -> Analysis Prompts
  -> Report Prompts
```

核心业务链路：

```text
用户输入产品名称 / 型号 / 上传资料
-> 产品识别、别名匹配和任务参数解析
-> 文档解析、切分、抽取、向量化和图谱写入
-> 产品事实包检索
-> 行业资料、客户案例和市场资料检索
-> Reader / Analyst / Strategist / Formatter 市场分析
-> Researcher / Analyst / Writer 竞品分析
-> 竞品事件抽取、去重、入库和时间线生成
-> 客户画像、适配度评分和销售策略生成
-> 中间结果事实校验
-> 结构化 JSON 报告生成
-> 前端报告渲染、引用展示和导出
-> 用户反馈回流知识库和评估集
```

问答链路仍然保留，但定位为“证据检索、追问解释和报告辅助入口”，不是最终项目边界。

## 4. 技术栈

| 层级 | 推荐技术 | 说明 |
| --- | --- | --- |
| 前端 | React + TypeScript + Vite + Ant Design | 实现资料管理、分析任务、报告展示、竞品动态和知识维护 |
| 后端 | FastAPI + Python | 提供 API、鉴权、RAG 编排、工作流调度和报告服务 |
| 工作流编排 | LangGraph 或等价有状态工作流 | 拆解产品识别、市场分析、竞品分析、销售策略和报告生成节点 |
| 异步任务 | Celery + Redis | 处理文档解析、抽取、向量化、图谱写入、报告生成和导出 |
| 结构化数据库 | PostgreSQL | 保存用户、资料、产品、案例、竞品、事件、任务、报告和反馈 |
| 向量数据库 | Milvus | 保存 chunk embedding，支持语义检索和 evidence pack 召回 |
| 图数据库 | Neo4j | 保存产品、行业、场景、痛点、竞品和销售卖点关系 |
| 文件存储 | MinIO | 保存原始资料、解析中间产物和导出报告 |
| 模型接口 | OpenAI-compatible API | 统一接入 chat、embedding、reranker 模型 |
| 部署 | Docker Compose | 首期内部部署，后续可迁移 Kubernetes |

## 5. 推荐项目结构

```text
saleshelper/
  backend/
    app/
      api/
      core/
      db/
      graph/
      models/
      prompts/
        extraction/
        analysis/
        report/
      rag/
      schemas/
      services/
        analysis/
        documents/
        knowledge/
        products/
        reports/
        retrieval/
        sales/
      storage/
      vector/
      workflows/
      workers/
      tests/
    pyproject.toml
    Dockerfile

  frontend/
    src/
      components/
      pages/
        documents/
        products/
        tasks/
        reports/
        competitors/
        knowledge/
        admin/
      services/
      stores/
      types/
    package.json
    Dockerfile

  infra/
    docker-compose.yml
    postgres/
    milvus/
    neo4j/
    minio/
    nginx/

  docs/
    final-implementation-plan.md
    task-cycles.md
    architecture.md
    data-model.md
    api.md
    rag-design.md
    workflow-design.md
    report-design.md
    deployment.md
    evaluation.md

  samples/
    documents/
    reports/
    questions/
```

## 6. 核心数据模型

### 6.1 PostgreSQL

PostgreSQL 是系统唯一业务事实源，负责保存可审计、可修正、可回溯的数据。Milvus、Neo4j 和报告索引都必须能够从 PostgreSQL 重建。

核心表建议：

```text
users
roles
permissions

documents
document_versions
document_chunks

products
product_aliases
product_models
product_parameters
product_features
selling_points

industries
scenarios
pain_points
customer_cases
sales_materials

competitors
competitor_products
competitor_parameters
competitor_events

knowledge_relations
extraction_candidates
ingestion_jobs

analysis_tasks
analysis_task_steps
evidence_items
analysis_reports
report_sections
report_exports

conversations
messages
citations
feedback
quality_checks
```

关键表设计方向：

```text
documents:
  id
  title
  file_name
  file_type
  business_type
  source_type
  product_id
  competitor_id
  industry_id
  trust_level
  version
  storage_path
  status
  uploaded_by
  created_at
  updated_at

document_chunks:
  id
  document_id
  version_id
  chunk_index
  title_path
  content
  page_number
  sheet_name
  token_count
  metadata
  vector_status
  created_at

products:
  id
  name
  model
  category
  description
  status
  confidence_level
  created_at
  updated_at

product_parameters:
  id
  product_id
  parameter_name
  parameter_value
  unit
  source_chunk_id
  confidence
  verified_by_user
  created_at
  updated_at

customer_cases:
  id
  customer_name
  customer_industry_id
  customer_size
  product_id
  scenario_id
  pain_point_id
  solution_summary
  implementation_result
  source_chunk_id
  trust_level
  created_at
  updated_at

competitor_events:
  id
  competitor_id
  competitor_product_id
  event_type
  event_title
  event_summary
  event_time
  source_document_id
  source_chunk_id
  impact_level
  trust_level
  dedupe_key
  status
  created_at
  updated_at

analysis_tasks:
  id
  task_type
  product_id
  product_name_input
  product_model_input
  target_industry_id
  competitor_ids
  user_question
  output_format
  status
  current_step
  created_by
  created_at
  updated_at

analysis_task_steps:
  id
  task_id
  step_name
  status
  input_json
  output_json
  error_message
  started_at
  finished_at

evidence_items:
  id
  task_id
  source_type
  document_id
  chunk_id
  product_id
  competitor_id
  industry_id
  content
  quote
  score
  trust_level
  metadata
  created_at

analysis_reports:
  id
  task_id
  product_id
  report_type
  title
  report_json
  report_markdown
  quality_status
  version
  created_by
  created_at
  updated_at
```

设计要求：

- 自动抽取字段必须保留 `source_chunk_id`，并记录置信度和抽取版本。
- 人工确认字段优先级高于自动抽取字段，自动任务不能覆盖人工确认内容。
- 文档和 chunk 必须有版本信息，便于重建索引和追溯来源。
- 分析任务必须保存每个工作流节点的输入、输出、状态和错误信息。
- 报告必须保存结构化 JSON、Markdown 渲染文本、引用来源和质量检查结果。
- 会话回答必须保存当时使用的 citation，便于后续复盘。

### 6.2 Milvus

Milvus 用于保存文本片段 embedding，支持语义检索和 evidence pack 召回。

建议 collection：

```text
collection: document_chunks

fields:
  chunk_id
  document_id
  product_id
  competitor_id
  industry_id
  source_type
  business_type
  trust_level
  updated_at
  embedding
  content
```

设计要求：

- Milvus 中的 `chunk_id` 必须能回到 PostgreSQL 的 `document_chunks.id`。
- 支持按产品、竞品、行业、资料类型、业务类型、可信等级和更新时间过滤。
- 向量索引可通过 PostgreSQL 数据重建。
- 检索结果必须回写为 evidence item，供分析任务、报告和质量检查复盘。

### 6.3 Neo4j

Neo4j 用于保存业务关系，支撑产品推荐、行业匹配、痛点匹配、竞品关系和销售切入点查询。

节点类型：

```text
Product
ProductModel
Competitor
CompetitorProduct
Industry
Scenario
PainPoint
SellingPoint
CustomerCase
SalesMaterial
Document
Chunk
```

关系类型：

```text
(Product)-[:APPLIES_TO]->(Industry)
(Product)-[:USED_IN]->(Scenario)
(Product)-[:SOLVES]->(PainPoint)
(Product)-[:HAS_SELLING_POINT]->(SellingPoint)
(Product)-[:HAS_CASE]->(CustomerCase)
(Product)-[:COMPETES_WITH]->(CompetitorProduct)
(Competitor)-[:OWNS]->(CompetitorProduct)
(CustomerCase)-[:PROVES]->(SellingPoint)
(SalesMaterial)-[:SUPPORTS]->(Scenario)
(Document)-[:MENTIONS]->(Product)
(Document)-[:MENTIONS]->(Competitor)
(Chunk)-[:SUPPORTS]->(SellingPoint)
```

设计要求：

- 图谱首期只做可解释关系查询，不做复杂自动推理。
- 每条关系必须尽量绑定来源 chunk 或文档。
- 关系写入保留来源、置信度、创建方式和更新时间。
- Neo4j 可从 PostgreSQL 的结构化关系重建。

## 7. 文档接入与处理路径

文档处理采用异步任务，避免上传接口阻塞。

```text
管理员上传文件
-> FastAPI 校验文件和元数据
-> 原始文件保存到 MinIO
-> PostgreSQL 创建 document、document_version、ingestion_job
-> Celery Worker 拉取任务
-> 按文件类型解析
-> 文本清洗和表格提取
-> 语义切分 chunk
-> chunk 写入 PostgreSQL
-> 调用 LLM 抽取结构化字段和候选关系
-> 写入 PostgreSQL 候选知识
-> 调用 embedding 模型
-> 写入 Milvus
-> 写入 Neo4j 关系
-> 更新任务状态
```

文件格式支持：

| 文件类型 | 推荐工具 | 首期要求 |
| --- | --- | --- |
| PDF | PyMuPDF / pdfplumber / Docling | 提取正文、页码、表格 |
| Word | python-docx / Docling | 提取标题、段落、表格 |
| Excel | openpyxl / pandas | 提取参数表、竞品表、价格表、客户案例表 |
| PPT | python-pptx | 提取页面文字、备注、基础结构 |
| Markdown | Python 原生读取 | 按标题结构切分 |
| TXT | Python 原生读取 | 按段落切分 |
| 网页快照 | trafilatura / readability | 后续用于竞品动态和市场资料 |

OCR 不是首期必需能力。图片型 PDF 可先标记为“需要 OCR”，后续接入 PaddleOCR 或云 OCR。

切分策略：

- 优先按标题、章节、页码、表格和业务段落切分。
- 每个 chunk 建议 500-1000 中文字。
- 表格内容保留表头、行列上下文和来源 sheet。
- chunk metadata 必须包含文件、页码、sheet、标题路径、资料类型、可信等级、产品、竞品、行业。
- 客户案例、竞品参数、价格、交付周期等高风险事实必须保留更细粒度来源。

## 8. 结构化抽取路径

结构化抽取采用“LLM 抽取 + Schema 校验 + 人工修正 + 正式入库”。

```text
chunk 文本
-> 根据资料类型选择抽取 prompt
-> LLM 输出 JSON
-> Pydantic 校验
-> 规则补充和置信度评分
-> 写入 extraction_candidates
-> 管理员审核、修正或忽略
-> 写入正式知识表
-> 同步 Milvus metadata 和 Neo4j 关系
```

抽取内容：

- 产品名称、型号、分类、核心功能和关键参数。
- 产品特点、核心卖点、限制条件和适用边界。
- 适用行业、典型应用场景、目标客户和采购场景。
- 客户案例中的行业、痛点、应用场景、解决方案和实施效果。
- 竞品公司、竞品产品、竞品参数、优势、劣势和销售反馈。
- 竞品事件，包括产品发布、参数变化、价格变化、客户案例、合作伙伴、市场活动、负面舆情和招聘扩张。
- 行业趋势、采购关注点、政策影响和典型应用。

实现要求：

- LLM 输出必须是可校验 JSON。
- 每个字段必须绑定来源 chunk。
- 低置信度字段标记为待确认。
- 参数类字段优先来自 Excel、规格书和正式产品手册。
- 自动抽取不能覆盖人工确认字段。
- 竞品事件需要去重、可信度判断和影响等级评估。

## 9. 产品识别与 Evidence Pack

产品识别是所有业务分析任务的入口。

```text
用户输入产品名称 / 型号 / 自然语言问题 / 上传资料
-> 解析任务目标和输出格式
-> 产品精确匹配、别名匹配、模糊匹配和向量相似匹配
-> 如为新产品资料，创建临时产品对象
-> 补全产品、行业、竞品和客户上下文
-> 创建 analysis_task
```

Evidence pack 是后续市场分析、竞品分析、销售推荐和报告输出的统一证据输入。

```text
任务参数
-> 查询改写和多路 query 生成
-> PostgreSQL 结构化查询
-> 关键词精确查询
-> Milvus 向量检索
-> Neo4j 关系查询
-> 候选证据合并、去重、过滤
-> reranker 重排序
-> 证据分组和引用编号
-> 写入 evidence_items
```

检索策略：

- 产品参数、型号、价格、规格优先查 PostgreSQL。
- 产品说明、应用案例、行业资料、销售 FAQ 优先查 Milvus。
- 型号、竞品名称、参数名必须做关键词精确匹配。
- 产品、行业、场景、痛点、竞品和销售材料关系查 Neo4j。
- 多路结果进入统一 evidence pool，再去重、过滤、重排序。

排序权重建议：

```text
最终分数 =
  语义相关性 * 0.40
+ 关键词匹配 * 0.20
+ 可信等级 * 0.15
+ 资料类型权重 * 0.10
+ 业务节点匹配度 * 0.10
+ 更新时间 * 0.05
```

资料优先级：

```text
内部正式产品资料
> 公司销售资料
> 客户案例
> 人工维护标签
> 竞品官网资料
> 行业报告
> 普通外部资料
```

## 10. 分析工作流设计

分析层不是单一大模型调用，而是由多个工作流节点组成。每个节点必须有明确输入、输出、引用来源和质量检查规则。

### 10.1 目标市场分析

目标市场分析回答“这个产品适合哪些行业、哪些客户、哪些应用场景，以及为什么适合”。

采用 Reader -> Analyst -> Strategist -> Formatter 流程：

```text
Reader:
  读取产品事实包，检索行业资料、客户案例和市场资料。

Analyst:
  从产品功能、客户痛点、行业需求、已有案例、采购场景和进入难度分析匹配关系。

Strategist:
  给出优先进入行业、适合客户类型、主打应用场景、价值主张和进入策略。

Formatter:
  输出目标行业排序、客户类型、行业痛点、产品匹配依据、案例支撑和风险提示。
```

输出内容：

- 目标行业排序。
- 目标客户画像。
- 典型应用场景。
- 客户痛点与产品能力匹配。
- 市场机会和进入策略。
- 资料缺口和待验证假设。

### 10.2 竞品对比分析

竞品对比分析回答“我方产品和竞品相比差异在哪里，销售时应该怎么讲”。

采用 Researcher -> Analyst -> Writer 流程：

```text
Researcher:
  检索我方产品资料和竞品资料；未指定竞品时推荐候选竞品。

Analyst:
  按功能能力、技术参数、适用场景、价格区间、部署成本、维护成本、
  稳定性、交付周期、售后服务、典型客户、认证资质和市场定位进行对比。

Writer:
  输出我方优势、我方劣势、差异化卖点、竞品风险提示、反驳话术和销售注意事项。
```

实现要求：

- 竞品对比必须表格化。
- 每个对比项必须有来源或标注资料不足。
- 不得编造竞品价格、参数、客户案例和市场份额。
- 销售话术必须对应产品卖点、客户痛点或竞品差异。

### 10.3 竞品动态沉淀

竞品动态沉淀负责将竞品资料持续转化为结构化情报。

```text
竞品资料 / 新闻 / 官网页面 / 销售反馈
-> 文档解析和正文抽取
-> 事件抽取 JSON
-> 事件去重
-> 可信度和影响等级判断
-> PostgreSQL 入库
-> 竞品动态时间线
-> 供竞品分析和报告调用
```

事件类型：

```text
product_release
parameter_change
price_change
customer_case
partnership
financing_or_acquisition
market_campaign
hiring_expansion
new_industry_entry
negative_news
sales_feedback
```

### 10.4 销售推荐策略

销售推荐策略将产品分析、市场分析和竞品分析结果转化为销售可执行建议。

```text
产品事实包
-> 目标行业和客户画像
-> 客户痛点和案例匹配
-> 竞品差异和替代机会
-> 客户适配度评分
-> 销售切入点
-> 拜访问题
-> 推荐话术
-> 推荐材料
```

客户适配度评分维度：

- 行业匹配度。
- 痛点匹配度。
- 案例匹配度。
- 竞品替代机会。
- 采购可能性。
- 销售进入难度。

销售推荐输出：

- 首次触达话术。
- 需求挖掘问题。
- 产品推荐逻辑。
- 竞品异议回应。
- 成交推进建议。
- 推荐销售材料列表。

### 10.5 结构化报告输出

报告不应由一个 Prompt 一次性生成，而应采用“中间结果汇总 -> 事实校验 -> 结构化 JSON -> 报告渲染”的方式。

报告内容：

- 产品概述。
- 产品核心能力和参数。
- 用户画像。
- 目标行业和应用场景。
- 客户痛点与产品匹配。
- 客户案例支撑。
- 竞品对比表。
- 竞品动态时间线。
- 销售切入点。
- 销售话术和拜访问题。
- 推荐材料。
- 资料缺口。
- 引用来源。

报告输出格式：

```json
{
  "product_summary": {},
  "target_market": {},
  "customer_profile": {},
  "scenarios": [],
  "pain_point_mapping": [],
  "competitor_comparison": [],
  "competitor_events": [],
  "sales_strategy": {},
  "recommended_materials": [],
  "missing_information": [],
  "citations": []
}
```

## 11. 生成约束与质量治理

生成层必须将大模型限制在证据范围内。

通用输出结构：

```json
{
  "facts": [],
  "analysis": [],
  "assumptions": [],
  "recommendations": [],
  "missing_information": [],
  "citations": []
}
```

生成规则：

- 只能基于给定证据回答或生成报告。
- 产品参数、竞品对比、客户案例、价格、交付周期和市场结论必须引用来源。
- 无证据内容必须标注为“推测”或“建议”。
- 资料不足时必须输出“暂无资料支持”或“需要补充资料”。
- 竞品对比必须表格化。
- 市场推荐必须说明推荐依据、风险和待验证假设。
- 销售建议必须对应客户痛点、产品卖点、案例证据或竞品差异。

Prompt 基础约束：

```text
你是公司内部产品分析、市场定位和销售辅助系统中的分析节点。
你只能基于给定证据输出。
不能编造参数、价格、客户案例、竞品信息和市场份额。
请区分事实、分析、推测和建议。
关键结论必须引用证据编号。
如果证据不足，请明确指出缺失资料。
```

质量检查流程：

```text
节点输出 / 报告初稿
-> 检查关键事实是否有引用
-> 检查参数和竞品信息是否来自证据
-> 检查销售建议是否能回溯到痛点、卖点或案例
-> 检查是否存在无证据确定性结论
-> 检查输出结构是否合规
-> 不合规则重新生成、降级为资料不足或进入人工复核
```

## 12. API 设计

核心接口：

```text
POST /api/auth/login
GET  /api/me

POST /api/documents
GET  /api/documents
GET  /api/documents/{id}
POST /api/documents/{id}/reindex
PATCH /api/documents/{id}/metadata

GET  /api/products
POST /api/products/identify
GET  /api/products/{id}
PATCH /api/products/{id}

GET  /api/competitors
GET  /api/competitors/{id}/events
POST /api/competitor-events/extract

GET  /api/industries
GET  /api/scenarios
GET  /api/pain-points

POST /api/analysis-tasks
GET  /api/analysis-tasks
GET  /api/analysis-tasks/{id}
POST /api/analysis-tasks/{id}/run
POST /api/analysis-tasks/{id}/retry

POST /api/retrieval/evidence-pack
POST /api/chat

GET  /api/reports
GET  /api/reports/{id}
POST /api/reports/{id}/export

POST /api/feedback
GET  /api/admin/ingestion-jobs
GET  /api/admin/quality-checks
```

`POST /api/analysis-tasks` 请求示例：

```json
{
  "task_type": "full_product_analysis",
  "product_name": "XX-100",
  "product_model": "optional",
  "target_industry_id": "optional",
  "competitor_ids": ["optional"],
  "analysis_goals": [
    "market_analysis",
    "competitor_comparison",
    "sales_strategy",
    "report"
  ],
  "output_format": "structured_report"
}
```

`GET /api/analysis-tasks/{id}` 响应示例：

```json
{
  "task_id": "",
  "status": "running",
  "current_step": "market_analysis",
  "steps": [
    {
      "name": "product_identification",
      "status": "completed"
    },
    {
      "name": "evidence_pack",
      "status": "completed"
    },
    {
      "name": "market_analysis",
      "status": "running"
    }
  ],
  "report_id": null
}
```

`POST /api/chat` 保留为辅助接口：

```json
{
  "conversation_id": "optional",
  "question": "XX-100 适合哪些客户？",
  "filters": {
    "product_id": "optional",
    "industry_id": "optional",
    "trust_level_min": 3
  }
}
```

## 13. 前端页面

首期应建设完整业务工作台，而不是只有问答页。

- 登录页：账号密码登录。
- 产品输入页：输入产品名称、型号，或上传新产品资料创建分析任务。
- 资料管理页：上传文件、填写元数据、查看解析状态。
- 资料详情页：查看原文件、解析文本、chunk、抽取结果和来源关系。
- 产品知识页：维护产品、型号、参数、行业、场景、卖点、限制条件。
- 分析任务页：查看任务状态、当前节点、失败原因和重试入口。
- 报告工作台：查看结构化报告、引用来源、资料缺口和导出结果。
- 目标市场页：查看行业排序、客户画像、应用场景和市场进入建议。
- 竞品分析页：查看竞品对比表、差异化卖点和反驳话术。
- 竞品动态页：查看竞品事件时间线、事件来源和影响等级。
- 销售策略页：查看适配度评分、销售切入点、拜访问题和推荐材料。
- 问答页：用于追问、解释报告结论和检索引用来源。
- 管理后台页：任务状态、失败重试、索引重建、质量检查和用户权限。

报告工作台交互要求：

- 左侧展示报告目录和章节。
- 中间展示结构化报告正文、表格、评分和推荐内容。
- 右侧展示引用来源、证据片段、可信等级和资料缺口。
- 点击引用可查看原文片段、文件名、页码、sheet 和可信等级。
- 报告中的事实、分析、推测和建议应有清晰区分。

## 14. 部署方案

第一阶段使用 Docker Compose 部署。

服务清单：

```text
frontend
backend
worker
postgres
redis
milvus
neo4j
minio
nginx
```

环境变量：

```text
DATABASE_URL
REDIS_URL
MILVUS_HOST
NEO4J_URI
MINIO_ENDPOINT
OPENAI_BASE_URL
OPENAI_API_KEY
CHAT_MODEL
EMBEDDING_MODEL
RERANKER_MODEL
JWT_SECRET
```

部署流程：

```text
初始化数据库
-> 启动基础服务
-> 启动 backend 和 worker
-> 创建管理员账号
-> 上传样例资料
-> 等待解析、抽取、向量化和图谱写入完成
-> 创建样例产品分析任务
-> 生成标准报告
-> 运行质量检查和评估集
-> 开放给业务试用
```

## 15. 评估指标

系统上线前必须建立评估集，不能只靠主观体验判断。

首批建议准备 30-80 条评估任务，覆盖：

- 输入产品名称后是否能识别正确产品和型号。
- 某产品目标行业、客户画像和应用场景是否合理。
- 某产品和竞品差异是否有资料依据。
- 某行业或客户痛点能否推荐合适产品。
- 客户案例能否正确支撑销售建议。
- 竞品事件能否正确抽取、去重和入库。
- 报告关键结论是否有引用来源。
- 资料不足时系统是否能拒绝编造。

评估指标：

```text
产品识别准确率
检索命中率
事实准确率
引用正确率
市场分析可用率
竞品对比可用率
销售建议可执行率
资料缺口识别率
报告结构完整率
人工修改率
平均任务完成时间
```

完整业务验收标准：

- 上传首批产品资料、客户案例、行业资料和竞品资料后，系统能完成解析、抽取、索引和知识维护。
- 用户输入产品名称、型号或上传资料后，系统能创建并执行完整分析任务。
- 系统能生成包含产品概述、目标市场、客户画像、应用场景、竞品对比、销售策略和引用来源的结构化报告。
- 产品参数类事实准确率达到 90% 以上。
- 报告关键事实引用覆盖率达到 90% 以上。
- 竞品资料不足场景不能编造参数、价格、客户案例或市场份额。
- 管理员可以修正抽取错误，并且修正结果进入后续分析。
- 业务用户可以查看报告、追问报告结论、导出报告并提交反馈。

## 16. 实施路线图

完整项目建议分为六个阶段，总周期约 16-20 周。每个阶段都应产出可验证交付物，避免系统停留在单点问答能力。

### 阶段一：需求梳理与数据准备

周期建议：第 1-2 周。

目标是明确系统边界、资料范围、用户角色、报告模板和评估标准。

交付内容：

- 需求说明文档。
- 系统功能清单。
- 资料分类规范。
- 元数据字段规范。
- 产品分析报告模板。
- 竞品分析维度。
- 销售策略输出格式。
- 数据库初步设计。

### 阶段二：数据底座与知识库建设

周期建议：第 3-6 周。

目标是完成资料接入、文档解析、结构化字段抽取、向量化入库和基础知识库管理能力。

交付内容：

- 资料上传和管理后台。
- 文档解析链路。
- chunk 切分和来源追溯。
- 产品、竞品、行业、案例基础表。
- Milvus 向量索引。
- Neo4j 基础关系写入。
- 管理员审核和修正候选知识能力。

### 阶段三：产品识别、Evidence Pack 与辅助问答

周期建议：第 7-9 周。

目标是为后续分析模块提供可靠证据输入，而不是把问答作为项目终点。

交付内容：

- 产品识别接口。
- 查询改写和多路检索。
- PostgreSQL、关键词、Milvus、Neo4j 混合检索。
- evidence pack 生成服务。
- 引用来源和资料缺口识别。
- 辅助问答接口和引用侧栏。

### 阶段四：市场分析与竞品分析

周期建议：第 10-13 周。

目标是使系统从知识库能力升级为业务分析工具。

交付内容：

- 市场分析工作流。
- 目标行业推荐。
- 客户画像生成。
- 应用场景和客户痛点分析。
- 竞品候选推荐。
- 竞品对比工作流。
- 竞品对比表、差异化卖点和反驳话术。

### 阶段五：竞品动态沉淀与销售推荐

周期建议：第 14-17 周。

目标是建设竞品事件库和销售策略模块，使系统具备持续情报沉淀和服务销售动作的能力。

交付内容：

- 竞品事件抽取服务。
- 竞品事件去重和可信度判断。
- 竞品动态时间线。
- 客户适配度评分。
- 销售切入点生成。
- 需求挖掘问题。
- 异议处理话术。
- 推荐销售材料列表。

### 阶段六：报告输出、质量治理与上线

周期建议：第 18-20 周。

目标是完成结构化报告输出、质量评估、权限控制、系统测试和正式上线准备。

交付内容：

- 结构化报告工作台。
- 报告导出为 Markdown、Word 或 PDF。
- 引用来源展示。
- 质量检查规则。
- 用户权限和资料权限。
- 操作日志和任务失败重试。
- 评估集和测试报告。
- 上线部署文档。

## 17. 建设重点与风险控制

- 资料质量决定系统上限。项目早期必须重视资料整理、资料分类、元数据规范和样例资料准备。
- 检索质量决定分析是否有依据。系统不能只依赖向量检索，需要结合关键词检索、结构化过滤、图谱查询和 reranker。
- 分析流程必须拆解。产品分析、市场分析、竞品分析、销售策略和报告生成必须分节点执行、分节点存储、分节点校验。
- 竞品信息必须谨慎处理。竞品价格、参数、客户案例和市场份额如果没有明确资料来源，必须标注资料不足。
- 销售建议必须贴近业务。报告不能只输出“适合某行业”，还要给出客户痛点、切入场景、推荐话术、异议处理和可引用材料。
- 外部数据采集应渐进建设。首期可先支持人工上传竞品资料和网页快照，后续再扩展定时抓取、网页监控和搜索 API。
- 权限和审计要前置设计。产品资料、客户案例和竞品情报可能涉及敏感信息，不同角色必须受资料权限控制。

## 18. 默认假设

- 项目采用完整业务闭环作为首期目标：资料接入、知识库、市场分析、竞品分析、销售推荐、报告输出和反馈回流。
- 技术架构采用 PostgreSQL + Milvus + Neo4j + MinIO + Redis。
- 模型接口采用 OpenAI-compatible API。
- 工作流编排采用 LangGraph 或等价实现。
- 首期资料格式支持 PDF、Word、Excel、PPT、Markdown、TXT。
- 首期外部市场数据以人工上传和网页快照为主，不强依赖自动爬虫。
- 首版权限至少包含管理员、知识维护人员、业务用户和只读用户。
- 默认项目先做内部部署；如果使用公网模型，需要单独确认数据合规策略。
