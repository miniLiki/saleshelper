from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, analysis, auth, documents, health, products, retrieval, users
from app.core.config import settings
from app.core.errors import register_exception_handlers


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(users.router, prefix="/api", tags=["users"])
    app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
    app.include_router(products.router, prefix="/api/products", tags=["products"])
    app.include_router(retrieval.router, prefix="/api/retrieval", tags=["retrieval"])
    app.include_router(analysis.router, prefix="/api", tags=["analysis"])
    app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
    return app


app = create_app()
