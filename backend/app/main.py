from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

import backend.app.models  # noqa: F401  (registers tables on Base.metadata)
from backend.app.database import Base, engine, migrate_legacy_schema
from backend.app.limiter import limiter
from backend.app.routers import auth, games, health, questions, sessions, users
from backend.app.utils.exceptions import AppException


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    migrate_legacy_schema()
    yield


app = FastAPI(title="RuleKeepr API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(games.router)
app.include_router(sessions.router)
app.include_router(questions.router)
