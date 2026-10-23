from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database import get_db

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    responses={503: {"description": "The database is unreachable."}},
    summary="Check that the API and its database are up.",
)
def health_check(response: Response, db: Session = Depends(get_db)):
    """Return 200 when the database answers a trivial query, otherwise 503.

    The docker-compose healthcheck treats any non-2xx status as unhealthy.
    """
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}
