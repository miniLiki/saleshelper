import math
import time
from pathlib import Path
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document, DocumentChunk
from app.models.knowledge import (
    Competitor,
    CompetitorProduct,
    CustomerCase,
    Industry,
    KnowledgeRelation,
    PainPoint,
    Product,
    ProductParameter,
    SalesMaterial,
    Scenario,
    SellingPoint,
)
from app.services.ai_client import embed_text


def cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    dot = sum(left[index] * right[index] for index in range(size))
    left_norm = math.sqrt(sum(value * value for value in left[:size])) or 1.0
    right_norm = math.sqrt(sum(value * value for value in right[:size])) or 1.0
    return dot / (left_norm * right_norm)


def embed_chunks(db: Session, chunks: Iterable[DocumentChunk]) -> None:
    for chunk in chunks:
        chunk.embedding = embed_text(chunk.content)
        chunk.vector_status = "embedded"
    db.commit()


def rebuild_pg_embeddings(db: Session) -> int:
    chunks = db.scalars(select(DocumentChunk)).all()
    embed_chunks(db, chunks)
    return len(chunks)


def rebuild_milvus(db: Session) -> dict:
    if not settings.enable_milvus:
        return {"status": "disabled", "count": 0}
    last_error: Exception | None = None
    for _ in range(2):
        try:
            from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

            connections.connect(
                alias="default",
                host=settings.milvus_host,
                port=str(settings.milvus_port),
                timeout=2,
            )
            collection_name = "document_chunks"
            chunks = db.scalars(select(DocumentChunk).where(DocumentChunk.embedding.is_not(None))).all()
            dimension = len(chunks[0].embedding) if chunks and chunks[0].embedding else settings.embedding_dimension
            if utility.has_collection(collection_name):
                collection = Collection(collection_name)
                existing_dim = next(
                    field.params.get("dim")
                    for field in collection.schema.fields
                    if field.name == "embedding"
                )
                if int(existing_dim) != int(dimension):
                    utility.drop_collection(collection_name)
                    collection = None
                else:
                    collection = Collection(collection_name)
            else:
                collection = None
            if collection is None:
                fields = [
                    FieldSchema(name="chunk_id", dtype=DataType.INT64, is_primary=True),
                    FieldSchema(name="document_id", dtype=DataType.INT64),
                    FieldSchema(name="trust_level", dtype=DataType.INT64),
                    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2048),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension),
                ]
                collection = Collection(collection_name, CollectionSchema(fields))
                collection.create_index(
                    "embedding",
                    {"index_type": "AUTOINDEX", "metric_type": "COSINE", "params": {}},
                )
            if chunks:
                collection.upsert(
                    [
                        [chunk.id for chunk in chunks],
                        [chunk.document_id for chunk in chunks],
                        [int(chunk.metadata_json.get("trust_level", 3)) for chunk in chunks],
                        [chunk.content[:2048] for chunk in chunks],
                        [chunk.embedding for chunk in chunks],
                    ]
                )
                collection.flush()
                collection.load()
            return {"status": "ok", "count": len(chunks), "dimension": dimension}
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1)
    if settings.enable_milvus_lite_fallback:
        lite_result = rebuild_milvus_lite(db)
        if lite_result["status"] == "ok":
            return {**lite_result, "fallback_from": str(last_error)}
        return {"status": "degraded", "error": str(last_error), "fallback_error": lite_result.get("error"), "count": 0}
    return {"status": "degraded", "error": str(last_error), "count": 0}


def search_milvus(query_embedding: list[float], top_k: int = 10) -> dict:
    if not settings.enable_milvus:
        return {"status": "disabled", "items": []}
    try:
        from pymilvus import Collection, connections, utility

        connections.connect(
            alias="search",
            host=settings.milvus_host,
            port=str(settings.milvus_port),
            timeout=2,
        )
        collection_name = "document_chunks"
        if not utility.has_collection(collection_name, using="search"):
            connections.disconnect("search")
            return {"status": "missing", "items": []}
        collection = Collection(collection_name, using="search")
        collection.load()
        result = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {}},
            limit=top_k,
            output_fields=["chunk_id", "document_id", "trust_level", "content"],
        )
        items = []
        for hit in result[0] if result else []:
            entity = hit.entity
            items.append(
                {
                    "chunk_id": entity.get("chunk_id"),
                    "document_id": entity.get("document_id"),
                    "trust_level": entity.get("trust_level"),
                    "content": entity.get("content"),
                    "score": float(hit.score),
                }
            )
        connections.disconnect("search")
        return {"status": "ok", "items": items}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "error": str(exc), "items": []}


def rebuild_milvus_lite(db: Session) -> dict:
    try:
        from pymilvus import MilvusClient

        chunks = db.scalars(select(DocumentChunk).where(DocumentChunk.embedding.is_not(None))).all()
        dimension = len(chunks[0].embedding) if chunks and chunks[0].embedding else settings.embedding_dimension
        path = Path(settings.milvus_lite_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[3] / path
        path.parent.mkdir(parents=True, exist_ok=True)
        client = MilvusClient(str(path))
        collection_name = "document_chunks"
        if client.has_collection(collection_name):
            try:
                existing = client.describe_collection(collection_name)
                existing_dim = existing.get("dimension") or existing.get("schema", {}).get("dimension")
            except Exception:
                existing_dim = None
            if existing_dim and int(existing_dim) != int(dimension):
                client.drop_collection(collection_name)
        if not client.has_collection(collection_name):
            index_params = client.prepare_index_params()
            index_params.add_index(
                field_name="embedding",
                metric_type="COSINE",
                index_type="AUTOINDEX",
            )
            client.create_collection(
                collection_name=collection_name,
                dimension=dimension,
                primary_field_name="chunk_id",
                vector_field_name="embedding",
                metric_type="COSINE",
                index_params=index_params,
                auto_id=False,
            )
        if chunks:
            client.upsert(
                collection_name,
                [
                    {
                        "chunk_id": chunk.id,
                        "embedding": chunk.embedding,
                        "document_id": chunk.document_id,
                        "trust_level": int(chunk.metadata_json.get("trust_level", 3)),
                        "content": chunk.content[:2048],
                    }
                    for chunk in chunks
                ],
            )
        return {"status": "ok", "backend": "milvus_lite", "path": str(path), "count": len(chunks), "dimension": dimension}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "backend": "milvus_lite", "error": str(exc), "count": 0}


def search_milvus_lite(query_embedding: list[float], top_k: int = 10) -> dict:
    try:
        from pymilvus import MilvusClient

        path = Path(settings.milvus_lite_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[3] / path
        client = MilvusClient(str(path))
        collection_name = "document_chunks"
        if not client.has_collection(collection_name):
            return {"status": "missing", "items": []}
        result = client.search(
            collection_name=collection_name,
            data=[query_embedding],
            limit=top_k,
            output_fields=["document_id", "trust_level", "content"],
        )
        return {"status": "ok", "items": result[0] if result else []}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "error": str(exc), "items": []}


def verify_external_indexes(db: Session) -> dict:
    chunks = db.scalars(select(DocumentChunk).where(DocumentChunk.embedding.is_not(None))).all()
    result: dict = {
        "postgres": {"embedded_chunks": len(chunks)},
        "milvus": {"status": "disabled"} if not settings.enable_milvus else {},
        "neo4j": {"status": "disabled"} if not settings.enable_neo4j else {},
    }
    if settings.enable_milvus:
        try:
            from pymilvus import Collection, connections, utility

            connections.connect(
                alias="verify",
                host=settings.milvus_host,
                port=str(settings.milvus_port),
                timeout=2,
            )
            collection_name = "document_chunks"
            if not utility.has_collection(collection_name, using="verify"):
                result["milvus"] = {"status": "missing", "collection": collection_name}
            else:
                collection = Collection(collection_name, using="verify")
                collection.load()
                search_status = "not_tested"
                hits = 0
                if chunks and chunks[0].embedding:
                    search = collection.search(
                        data=[chunks[0].embedding],
                        anns_field="embedding",
                        param={"metric_type": "COSINE", "params": {}},
                        limit=1,
                        output_fields=["chunk_id", "document_id"],
                    )
                    hits = len(search[0]) if search else 0
                    search_status = "ok" if hits else "empty"
                result["milvus"] = {
                    "status": "ok",
                    "collection": collection_name,
                    "entities": collection.num_entities,
                    "search_status": search_status,
                    "search_hits": hits,
                }
            connections.disconnect("verify")
        except Exception as exc:  # noqa: BLE001
            result["milvus"] = {"status": "error", "error": str(exc)}

    if settings.enable_neo4j:
        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                connection_timeout=2,
            )
            try:
                driver.verify_connectivity()
                with driver.session() as session:
                    record = session.run(
                        """
                        MATCH (n)
                        WITH count(n) AS nodes
                        OPTIONAL MATCH ()-[r]->()
                        RETURN nodes, count(r) AS relationships
                        """
                    ).single()
                    result["neo4j"] = {
                        "status": "ok",
                        "nodes": record["nodes"] if record else 0,
                        "relationships": record["relationships"] if record else 0,
                    }
            finally:
                driver.close()
        except Exception as exc:  # noqa: BLE001
            result["neo4j"] = {"status": "error", "error": str(exc)}
    result["status"] = "ok" if all(
        value.get("status") in {"ok", "disabled"}
        for key, value in result.items()
        if key in {"milvus", "neo4j"}
    ) else "degraded"
    return result


def rebuild_neo4j(db: Session) -> dict:
    if not settings.enable_neo4j:
        return {"status": "disabled", "count": 0}
    last_error: Exception | None = None
    for _ in range(2):
        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                connection_timeout=2,
            )
            try:
                driver.verify_connectivity()
                documents = db.scalars(select(Document)).all()
                chunks = db.scalars(select(DocumentChunk)).all()
                products = db.scalars(select(Product)).all()
                parameters = db.scalars(select(ProductParameter)).all()
                industries = db.scalars(select(Industry)).all()
                scenarios = db.scalars(select(Scenario)).all()
                pain_points = db.scalars(select(PainPoint)).all()
                competitors = db.scalars(select(Competitor)).all()
                competitor_products = db.scalars(select(CompetitorProduct)).all()
                points = db.scalars(select(SellingPoint)).all()
                cases = db.scalars(select(CustomerCase)).all()
                materials = db.scalars(select(SalesMaterial)).all()
                relations = db.scalars(select(KnowledgeRelation)).all()
                with driver.session() as session:
                    for document in documents:
                        session.run(
                            """
                            MERGE (d:Document {id:$id})
                            SET d.title=$title, d.file_name=$file_name, d.business_type=$business_type,
                                d.trust_level=$trust_level, d.status=$status
                            """,
                            id=document.id,
                            title=document.title,
                            file_name=document.file_name,
                            business_type=document.business_type,
                            trust_level=document.trust_level,
                            status=document.status,
                        )
                    for chunk in chunks:
                        session.run(
                            """
                            MATCH (d:Document {id:$document_id})
                            MERGE (c:Chunk {id:$id})
                            SET c.chunk_index=$chunk_index, c.title_path=$title_path,
                                c.page_number=$page_number, c.sheet_name=$sheet_name
                            MERGE (d)-[:HAS_CHUNK]->(c)
                            """,
                            document_id=chunk.document_id,
                            id=chunk.id,
                            chunk_index=chunk.chunk_index,
                            title_path=chunk.title_path,
                            page_number=chunk.page_number,
                            sheet_name=chunk.sheet_name,
                        )
                    for product in products:
                        session.run(
                            "MERGE (p:Product {id:$id}) SET p.name=$name, p.model=$model",
                            id=product.id,
                            name=product.name,
                            model=product.model,
                        )
                    for parameter in parameters:
                        session.run(
                            """
                            MERGE (pp:ProductParameter {id:$id})
                            SET pp.name=$name, pp.value=$value, pp.unit=$unit
                            WITH pp
                            OPTIONAL MATCH (p:Product {id:$product_id})
                            FOREACH (_ IN CASE WHEN p IS NULL THEN [] ELSE [1] END |
                                MERGE (p)-[:HAS_PARAMETER]->(pp)
                            )
                            """,
                            id=parameter.id,
                            name=parameter.parameter_name,
                            value=parameter.parameter_value,
                            unit=parameter.unit,
                            product_id=parameter.product_id,
                        )
                    for industry in industries:
                        session.run(
                            "MERGE (i:Industry {id:$id}) SET i.name=$name",
                            id=industry.id,
                            name=industry.name,
                        )
                    for scenario in scenarios:
                        session.run(
                            """
                            MERGE (s:Scenario {id:$id}) SET s.name=$name, s.description=$description
                            WITH s
                            OPTIONAL MATCH (i:Industry {id:$industry_id})
                            FOREACH (_ IN CASE WHEN i IS NULL THEN [] ELSE [1] END |
                                MERGE (s)-[:USED_IN]->(i)
                            )
                            """,
                            id=scenario.id,
                            name=scenario.name,
                            description=scenario.description,
                            industry_id=scenario.industry_id,
                        )
                    for pain_point in pain_points:
                        session.run(
                            """
                            MERGE (pp:PainPoint {id:$id}) SET pp.name=$name, pp.description=$description
                            WITH pp
                            OPTIONAL MATCH (i:Industry {id:$industry_id})
                            FOREACH (_ IN CASE WHEN i IS NULL THEN [] ELSE [1] END |
                                MERGE (pp)-[:USED_IN]->(i)
                            )
                            """,
                            id=pain_point.id,
                            name=pain_point.name,
                            description=pain_point.description,
                            industry_id=pain_point.industry_id,
                        )
                    for competitor in competitors:
                        session.run(
                            "MERGE (c:Competitor {id:$id}) SET c.name=$name",
                            id=competitor.id,
                            name=competitor.name,
                        )
                    for competitor_product in competitor_products:
                        session.run(
                            """
                            MERGE (cp:CompetitorProduct {id:$id})
                            SET cp.name=$name, cp.model=$model, cp.strengths=$strengths, cp.weaknesses=$weaknesses
                            WITH cp
                            OPTIONAL MATCH (c:Competitor {id:$competitor_id})
                            FOREACH (_ IN CASE WHEN c IS NULL THEN [] ELSE [1] END |
                                MERGE (c)-[:HAS_PRODUCT]->(cp)
                            )
                            """,
                            id=competitor_product.id,
                            name=competitor_product.name,
                            model=competitor_product.model,
                            strengths=competitor_product.strengths,
                            weaknesses=competitor_product.weaknesses,
                            competitor_id=competitor_product.competitor_id,
                        )
                    for point in points:
                        session.run(
                            """
                            MERGE (s:SellingPoint {id:$id}) SET s.title=$title, s.description=$description
                            WITH s
                            OPTIONAL MATCH (p:Product {id:$product_id})
                            FOREACH (_ IN CASE WHEN p IS NULL THEN [] ELSE [1] END |
                                MERGE (p)-[:HAS_SELLING_POINT]->(s)
                            )
                            """,
                            id=point.id,
                            title=point.title,
                            description=point.description,
                            product_id=point.product_id,
                        )
                    for case in cases:
                        session.run(
                            """
                            MERGE (cc:CustomerCase {id:$id})
                            SET cc.customer_name=$customer_name, cc.solution_summary=$solution_summary,
                                cc.implementation_result=$implementation_result
                            WITH cc
                            OPTIONAL MATCH (p:Product {id:$product_id})
                            OPTIONAL MATCH (i:Industry {id:$industry_id})
                            OPTIONAL MATCH (s:Scenario {id:$scenario_id})
                            OPTIONAL MATCH (pp:PainPoint {id:$pain_point_id})
                            FOREACH (_ IN CASE WHEN p IS NULL THEN [] ELSE [1] END | MERGE (p)-[:HAS_CASE]->(cc))
                            FOREACH (_ IN CASE WHEN i IS NULL THEN [] ELSE [1] END | MERGE (cc)-[:USED_IN]->(i))
                            FOREACH (_ IN CASE WHEN s IS NULL THEN [] ELSE [1] END | MERGE (cc)-[:USED_IN]->(s))
                            FOREACH (_ IN CASE WHEN pp IS NULL THEN [] ELSE [1] END | MERGE (cc)-[:SOLVES]->(pp))
                            """,
                            id=case.id,
                            customer_name=case.customer_name,
                            solution_summary=case.solution_summary,
                            implementation_result=case.implementation_result,
                            product_id=case.product_id,
                            industry_id=case.customer_industry_id,
                            scenario_id=case.scenario_id,
                            pain_point_id=case.pain_point_id,
                        )
                    for material in materials:
                        session.run(
                            """
                            MERGE (sm:SalesMaterial {id:$id})
                            SET sm.title=$title, sm.material_type=$material_type,
                                sm.content_summary=$content_summary
                            """,
                            id=material.id,
                            title=material.title,
                            material_type=material.material_type,
                            content_summary=material.content_summary,
                        )
                    for relation in relations:
                        if relation.source_type == "Product" and relation.target_type == "Industry":
                            session.run(
                                """
                                MATCH (p:Product {id:$source_id})
                                MATCH (i:Industry {id:$target_id})
                                MERGE (p)-[r:APPLIES_TO]->(i)
                                SET r.confidence=$confidence, r.source_chunk_id=$source_chunk_id
                                """,
                                source_id=relation.source_id,
                                target_id=relation.target_id,
                                confidence=relation.confidence,
                                source_chunk_id=relation.source_chunk_id,
                            )
                        elif relation.source_type == "Product" and relation.target_type == "SellingPoint":
                            session.run(
                                """
                                MATCH (p:Product {id:$source_id})
                                MATCH (s:SellingPoint {id:$target_id})
                                MERGE (p)-[r:HAS_SELLING_POINT]->(s)
                                SET r.confidence=$confidence, r.source_chunk_id=$source_chunk_id
                                """,
                                source_id=relation.source_id,
                                target_id=relation.target_id,
                                confidence=relation.confidence,
                                source_chunk_id=relation.source_chunk_id,
                            )
                    for model in competitor_products:
                        for product in products:
                            if model.source_chunk_id and product.source_chunk_id == model.source_chunk_id:
                                session.run(
                                    """
                                    MATCH (p:Product {id:$product_id})
                                    MATCH (cp:CompetitorProduct {id:$competitor_product_id})
                                    MERGE (p)-[:COMPETES_WITH]->(cp)
                                    """,
                                    product_id=product.id,
                                    competitor_product_id=model.id,
                                )
                    for source_chunk_id, label, entity_id in [
                        *[(product.source_chunk_id, "Product", product.id) for product in products],
                        *[(point.source_chunk_id, "SellingPoint", point.id) for point in points],
                        *[(case.source_chunk_id, "CustomerCase", case.id) for case in cases],
                        *[(material.source_chunk_id, "SalesMaterial", material.id) for material in materials],
                        *[(competitor.source_chunk_id, "Competitor", competitor.id) for competitor in competitors],
                        *[(competitor_product.source_chunk_id, "CompetitorProduct", competitor_product.id) for competitor_product in competitor_products],
                    ]:
                        if source_chunk_id:
                            session.run(
                                f"""
                                MATCH (c:Chunk {{id:$chunk_id}})
                                MATCH (e:{label} {{id:$entity_id}})
                                MERGE (e)-[:MENTIONS]->(c)
                                """,
                                chunk_id=source_chunk_id,
                                entity_id=entity_id,
                            )
                count = (
                    len(documents)
                    + len(chunks)
                    + len(products)
                    + len(parameters)
                    + len(industries)
                    + len(scenarios)
                    + len(pain_points)
                    + len(competitors)
                    + len(competitor_products)
                    + len(points)
                    + len(cases)
                    + len(materials)
                    + len(relations)
                )
            finally:
                driver.close()
            return {"status": "ok", "count": count}
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1)
    return {"status": "degraded", "error": str(last_error), "count": 0}


def rebuild_knowledge_relations(db: Session) -> int:
    db.query(KnowledgeRelation).filter(KnowledgeRelation.created_by == "auto").delete()
    count = 0
    products = db.scalars(select(Product)).all()
    industries = db.scalars(select(Industry)).all()
    points = db.scalars(select(SellingPoint)).all()
    for product in products:
        for point in points:
            if point.product_id == product.id or (point.source_chunk_id and product.source_chunk_id == point.source_chunk_id):
                db.add(
                    KnowledgeRelation(
                        source_type="Product",
                        source_id=product.id,
                        relation_type="HAS_SELLING_POINT",
                        target_type="SellingPoint",
                        target_id=point.id,
                        source_chunk_id=point.source_chunk_id,
                        confidence=point.confidence,
                    )
                )
                count += 1
        for industry in industries:
            if product.source_chunk_id:
                db.add(
                    KnowledgeRelation(
                        source_type="Product",
                        source_id=product.id,
                        relation_type="APPLIES_TO",
                        target_type="Industry",
                        target_id=industry.id,
                        source_chunk_id=product.source_chunk_id,
                        confidence=0.4,
                    )
                )
                count += 1
    db.commit()
    return count
