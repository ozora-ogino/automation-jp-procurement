from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from uuid import UUID
from datetime import datetime, timedelta
import logging

from src.models import BiddingCase, CaseEmbedding
from src.schemas import BiddingCaseCreate, BiddingCaseUpdate

logger = logging.getLogger(__name__)


class BiddingCaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, case_data: BiddingCaseCreate) -> BiddingCase:
        db_case = BiddingCase(**case_data.model_dump())
        self.db.add(db_case)
        self.db.commit()
        self.db.refresh(db_case)
        return db_case

    def get_by_id(self, case_id: UUID) -> Optional[BiddingCase]:
        return self.db.query(BiddingCase).filter(BiddingCase.id == case_id).first()

    def get_by_case_id(self, case_id: str) -> Optional[BiddingCase]:
        return self.db.query(BiddingCase).filter(BiddingCase.case_id == case_id).first()

    def get_all(self, skip: int = 0, limit: int = 100, eligible_only: bool = False, eligibility_filter: str = None) -> List[BiddingCase]:
        query = self.db.query(BiddingCase)
        
        # Handle backward compatibility
        if eligible_only and eligibility_filter is None:
            eligibility_filter = "eligible"
            
        if eligibility_filter == "eligible":
            query = query.filter(BiddingCase.is_eligible_to_bid == True)
        elif eligibility_filter == "ineligible":
            query = query.filter(BiddingCase.is_eligible_to_bid == False)
            
        return query.offset(skip).limit(limit).all()

    def count(self, eligible_only: bool = False, eligibility_filter: str = None) -> int:
        query = self.db.query(func.count(BiddingCase.id))
        
        # Handle backward compatibility
        if eligible_only and eligibility_filter is None:
            eligibility_filter = "eligible"
            
        if eligibility_filter == "eligible":
            query = query.filter(BiddingCase.is_eligible_to_bid == True)
        elif eligibility_filter == "ineligible":
            query = query.filter(BiddingCase.is_eligible_to_bid == False)
            
        return query.scalar()

    def update(self, case_id: UUID, case_update: BiddingCaseUpdate) -> Optional[BiddingCase]:
        db_case = self.get_by_id(case_id)
        if not db_case:
            return None

        update_data = case_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_case, field, value)

        self.db.commit()
        self.db.refresh(db_case)
        return db_case

    def delete(self, case_id: UUID) -> bool:
        db_case = self.get_by_id(case_id)
        if not db_case:
            return False

        self.db.delete(db_case)
        self.db.commit()
        return True

    def search_by_vector(self, embedding: List[float], limit: int = 10, min_similarity: float = 0.7) -> List[tuple]:
        query = text("""
            SELECT bc.*, ce.embedding <=> :embedding as similarity
            FROM bidding_cases bc
            JOIN case_embeddings ce ON bc.case_id = ce.case_id
            WHERE ce.embedding <=> :embedding < :threshold
            ORDER BY similarity
            LIMIT :limit
        """)

        threshold = 1 - min_similarity
        results = self.db.execute(
            query,
            {"embedding": str(embedding), "threshold": threshold, "limit": limit}
        ).fetchall()

        return [(BiddingCase(**dict(row._mapping)), row.similarity) for row in results]

    def full_text_search(self, query: str, limit: int = 10) -> List[BiddingCase]:
        search_query = text("""
            SELECT * FROM bidding_cases
            WHERE search_vector @@ plainto_tsquery('japanese', :query)
            ORDER BY ts_rank(search_vector, plainto_tsquery('japanese', :query)) DESC
            LIMIT :limit
        """)

        results = self.db.execute(search_query, {"query": query, "limit": limit}).fetchall()
        return [BiddingCase(**dict(row._mapping)) for row in results]
    
    def count_active(self) -> int:
        """Count cases where submission deadline hasn't passed"""
        return self.db.query(func.count(BiddingCase.id)).filter(
            BiddingCase.document_submission_date >= datetime.now()
        ).scalar() or 0
    
    def count_eligible(self) -> int:
        """Count cases that are eligible to bid"""
        return self.db.query(func.count(BiddingCase.id)).filter(
            BiddingCase.is_eligible_to_bid == True
        ).scalar() or 0
    
    def count_ineligible(self) -> int:
        """Count cases that are not eligible to bid"""
        return self.db.query(func.count(BiddingCase.id)).filter(
            BiddingCase.is_eligible_to_bid == False
        ).scalar() or 0
    
    def count_recent(self, days: int = 30) -> int:
        """Count cases announced in the last N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        return self.db.query(func.count(BiddingCase.id)).filter(
            BiddingCase.announcement_date >= cutoff_date
        ).scalar() or 0
    
    def get_total_value(self) -> Optional[float]:
        """Get sum of all winning prices"""
        total = self.db.query(func.sum(BiddingCase.award_price_normalized)).scalar()
        return float(total) if total else None
    
    def get_average_value(self) -> Optional[float]:
        """Get average winning price"""
        avg = self.db.query(func.avg(BiddingCase.award_price_normalized)).scalar()
        return float(avg) if avg else None
    
    def get_prefecture_distribution(self) -> Dict[str, int]:
        """Get count of cases by prefecture"""
        results = self.db.query(
            BiddingCase.org_prefecture,
            func.count(BiddingCase.id).label('count')
        ).filter(
            BiddingCase.org_prefecture.isnot(None)
        ).group_by(
            BiddingCase.org_prefecture
        ).all()
        
        return {row.org_prefecture: row.count for row in results}
    
    def get_business_type_distribution(self) -> Dict[str, int]:
        """Get count of cases by business type"""
        results = self.db.query(
            BiddingCase.business_types_raw,
            func.count(BiddingCase.id).label('count')
        ).filter(
            BiddingCase.business_types_raw.isnot(None)
        ).group_by(
            BiddingCase.business_types_raw
        ).all()
        
        return {row.business_types_raw: row.count for row in results}
    
    def get_recent_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily case counts and values for the last N days"""
        query = text("""
            SELECT 
                DATE(announcement_date) as date,
                COUNT(*) as count,
                COALESCE(SUM(award_price_normalized), 0) as value
            FROM bidding_cases
            WHERE announcement_date >= CURRENT_DATE - :days * INTERVAL '1 day'
            GROUP BY DATE(announcement_date)
            ORDER BY date ASC
        """)
        
        results = self.db.execute(query, {"days": days}).fetchall()
        
        return [
            {
                "date": row.date.strftime("%Y-%m-%d") if row.date else None,
                "count": row.count,
                "value": float(row.value) if row.value else 0.0
            }
            for row in results
        ]


class CaseEmbeddingRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_or_update(self, case_id: str, embedding: List[float], model: str = "text-embedding-3-large") -> CaseEmbedding:
        existing = self.db.query(CaseEmbedding).filter(CaseEmbedding.case_id == case_id).first()

        if existing:
            existing.embedding = embedding
            existing.embedding_model = model
        else:
            existing = CaseEmbedding(
                case_id=case_id,
                embedding=embedding,
                embedding_model=model
            )
            self.db.add(existing)

        self.db.commit()
        self.db.refresh(existing)
        return existing

    def get_by_case_id(self, case_id: str) -> Optional[CaseEmbedding]:
        return self.db.query(CaseEmbedding).filter(CaseEmbedding.case_id == case_id).first()
