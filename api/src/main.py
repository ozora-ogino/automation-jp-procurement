from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from src.routers import bidding, health, search
from src.database import engine, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up API...")
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("Shutting down API...")


app = FastAPI(
    title="Japanese Procurement Data API",
    description="API for accessing and searching Japanese government procurement/bidding data",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(bidding.router, prefix="/api/v1/bidding", tags=["bidding"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])


@app.get("/")
async def root():
    return {
        "message": "Japanese Procurement Data API",
        "docs": "/docs",
        "redoc": "/redoc"
    }
