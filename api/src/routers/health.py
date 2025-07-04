from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from src.database import get_db
from src.schemas import HealthCheckResponse

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    return HealthCheckResponse(
        status="healthy",
        database=db_status,
        timestamp=datetime.utcnow()
    )
