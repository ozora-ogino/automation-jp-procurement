from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import openai
import os
import logging

from src.database import get_db
from src.repositories import BiddingCaseRepository, CaseEmbeddingRepository
from src.schemas import (
    VectorSearchRequest,
    VectorSearchResult,
    FullTextSearchRequest,
    BiddingCaseResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

openai.api_key = os.getenv("OPENAI_API_KEY")


async def get_embedding(text: str) -> List[float]:
    try:
        response = openai.embeddings.create(
            input=text,
            model="text-embedding-3-large"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate embedding")


@router.post("/vector", response_model=List[VectorSearchResult])
async def vector_search(
    request: VectorSearchRequest,
    db: Session = Depends(get_db)
):
    if not openai.api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    embedding = await get_embedding(request.query)
    repo = BiddingCaseRepository(db)
    
    results = repo.search_by_vector(
        embedding=embedding,
        limit=request.limit,
        min_similarity=request.min_similarity
    )
    
    return [
        VectorSearchResult(
            case=BiddingCaseResponse(
                **case.__dict__,
                has_embedding=bool(case.embedding)
            ),
            similarity=1 - similarity
        )
        for case, similarity in results
    ]


@router.post("/fulltext", response_model=List[BiddingCaseResponse])
async def full_text_search(
    request: FullTextSearchRequest,
    db: Session = Depends(get_db)
):
    repo = BiddingCaseRepository(db)
    cases = repo.full_text_search(request.query, request.limit)
    
    return [
        BiddingCaseResponse(
            **case.__dict__,
            has_embedding=bool(case.embedding)
        )
        for case in cases
    ]


@router.post("/cases/{case_id}/embed")
async def create_case_embedding(
    case_id: str,
    db: Session = Depends(get_db)
):
    if not openai.api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    case_repo = BiddingCaseRepository(db)
    case = case_repo.get_by_case_id(case_id)
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    text_for_embedding = f"{case.name} {case.organization or ''} {case.qualification or ''} {case.industry or ''}"
    embedding = await get_embedding(text_for_embedding)
    
    embedding_repo = CaseEmbeddingRepository(db)
    embedding_repo.create_or_update(case_id, embedding)
    
    return {"message": "Embedding created successfully", "case_id": case_id}