from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.api.v1.auth.oauth import router as oauth_router
from app.api.v1.auth.routes import router as auth_router
from app.api.v1.employees.routes import router as employees_router
from app.api.v1.recruitment.routes import router as recruitment_router
from app.api.v1.users.routes import router as users_router
from app.config.settings import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.core.rate_limit import limiter

configure_logging(settings.debug)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs",       # Swagger UI
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
register_exception_handlers(app)

app.add_middleware(RequestLoggingMiddleware)

# Dev-friendly CORS; tighten to explicit origins before Phase 6 (deployment/security).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(oauth_router, prefix=settings.api_v1_prefix)
app.include_router(users_router, prefix=settings.api_v1_prefix)
app.include_router(recruitment_router, prefix=settings.api_v1_prefix)
app.include_router(employees_router, prefix=settings.api_v1_prefix)


@app.get("/api/v1/health", tags=["health"])
def health_check():
    return {"status": "ok", "environment": settings.environment}
