from fastapi import APIRouter, Depends
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.storage.minio_client import ObjectStorage

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    checks: dict[str, bool | str] = {"api": True}

    try:
        db.execute(text("select 1"))
        checks["database"] = True
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"

    try:
        Redis.from_url(settings.redis_url, socket_connect_timeout=0.5).ping()
        checks["redis"] = True
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc}"

    try:
        checks["minio"] = ObjectStorage().health()
    except Exception as exc:  # noqa: BLE001
        checks["minio"] = f"error: {exc}"

    if not settings.enable_milvus:
        checks["milvus"] = "disabled"
    else:
        try:
            from pymilvus import connections, utility

            connections.connect(
                alias="health",
                host=settings.milvus_host,
                port=str(settings.milvus_port),
                timeout=2,
            )
            utility.list_collections(using="health")
            connections.disconnect("health")
            checks["milvus"] = True
        except Exception as exc:  # noqa: BLE001
            checks["milvus"] = f"error: {exc}"

    if not settings.enable_neo4j:
        checks["neo4j"] = "disabled"
    else:
        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                connection_timeout=2,
            )
            try:
                driver.verify_connectivity()
            finally:
                driver.close()
            checks["neo4j"] = True
        except Exception as exc:  # noqa: BLE001
            checks["neo4j"] = f"error: {exc}"

    ok = all(value is True or value == "disabled" for value in checks.values())
    return {"status": "ok" if ok else "degraded", "checks": checks}
