import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import document, user  # noqa: F401
from app.models.user import Role, User
from app.services.bootstrap import seed_defaults
from app.core.security import hash_password


@pytest.fixture(autouse=True)
def disable_external_indexes():
    from app.core.config import settings

    old_milvus = settings.enable_milvus
    old_neo4j = settings.enable_neo4j
    settings.enable_milvus = False
    settings.enable_neo4j = False
    yield
    settings.enable_milvus = old_milvus
    settings.enable_neo4j = old_neo4j


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        seed_defaults(db)
        business_role = db.query(Role).filter(Role.name == "business_user").one()
        db.add(
            User(
                username="sales",
                password_hash=hash_password("sales123456"),
                display_name="业务用户",
                roles=[business_role],
            )
        )
        db.commit()
    with TestingSessionLocal() as db:
        yield db
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session, monkeypatch):
    app = create_app()

    def override_get_db():
        yield db_session

    class FakeStorage:
        def put_bytes(self, object_name, data, content_type=None):
            self.object_name = object_name
            self.data = data
            self.content_type = content_type

        def health(self):
            return True

    monkeypatch.setattr("app.services.documents.ObjectStorage", lambda: FakeStorage())
    monkeypatch.setattr("app.api.routes.health.ObjectStorage", lambda: FakeStorage())
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture()
def admin_token(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture()
def business_token(client):
    response = client.post("/api/auth/login", json={"username": "sales", "password": "sales123456"})
    assert response.status_code == 200
    return response.json()["access_token"]
