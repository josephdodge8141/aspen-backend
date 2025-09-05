import os
from fastapi import FastAPI
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth import router as auth_router
from app.api.experts import router as experts_router
from app.api.workflows import router as workflows_router
from app.api.chat import router as chat_router
from app.api.services import router as services_router
from app.middleware.ratelimit import RateLimitMiddleware

# Initialize run registry (starts GC thread)
from app.services.runs.registry import REGISTRY

app = FastAPI(
    title="Aspen Backend",
    description="Multi-tenant AI workflow platform",
    version="0.1.0",
    openapi_tags=[
        {
            "name": "Auth",
            "description": "Authentication endpoints for internal users (JWT-based)",
        },
        {
            "name": "Experts",
            "description": "AI expert management - create, update, and manage chat personas",
        },
        {
            "name": "Workflows",
            "description": "Workflow orchestration - define and execute directed acyclic graphs",
        },
        {
            "name": "Services",
            "description": "External service integration - API key management and external user mapping",
        },
        {
            "name": "Chat",
            "description": "Chat execution - run experts and workflows with real-time logging",
        },
    ],
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React default
        "http://localhost:3001",  # Alternative React port
        "http://localhost:5173",  # Vite default
        "http://localhost:5174",  # Alternative Vite port
        "http://localhost:8080",  # Vue default
        "http://localhost:4200",  # Angular default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        # Add production origins as needed
        # "https://your-frontend-domain.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-API-Key",
        "X-Requested-With",
        "Cache-Control",
    ],
    expose_headers=[
        "Content-Length",
        "Content-Type",
        "X-Total-Count",
    ],
)

# Configure OpenAPI security schemes
from fastapi.openapi.utils import get_openapi


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token for internal users (members). Use the /auth/login endpoint to obtain a token.",
        },
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for external services. Generate and manage API keys through the Services endpoints.",
        },
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Register rate limiting middleware if enabled
if os.getenv("ENABLE_RATELIMIT", "false").lower() == "true":
    app.add_middleware(RateLimitMiddleware)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(experts_router)
app.include_router(workflows_router)
app.include_router(chat_router)
app.include_router(services_router)


@app.get("/")
async def root():
    return {"message": "Aspen Backend API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
