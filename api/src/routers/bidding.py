from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime

from src.database import get_db
from src.repositories import BiddingCaseRepository
from src.schemas import (
    BiddingCaseCreate,
    BiddingCaseUpdate,
    BiddingCaseResponse,
    BiddingCaseFrontendResponse,
    BiddingCaseListResponse,
    BiddingStatsResponse
)

router = APIRouter()


def map_to_frontend_response(case) -> BiddingCaseFrontendResponse:
    """Map database model to frontend response format"""
    return BiddingCaseFrontendResponse(
        id=str(case.id),
        case_id=str(case.case_id),
        case_name=case.case_name,
        organization=case.org_name or "",
        department=None,  # Not in our data model
        location=case.org_location,
        prefecture=case.org_prefecture,
        announcement_date=case.announcement_date.isoformat() if case.announcement_date else None,
        deadline=case.document_submission_date.isoformat() if case.document_submission_date else None,
        industry_type=case.business_types_raw,
        business_type=case.business_type if case.business_type else (case.business_types_raw.split('\n') if case.business_types_raw else None),
        business_type_code=case.business_type_code if case.business_type_code else case.business_types_normalized,
        qualification_requirements=case.qualifications_raw,
        qualification_details=case.qualifications_parsed,
        qualification_summary=case.qualifications_summary,
        planned_price=case.planned_price_normalized,
        winning_price=case.award_price_normalized,
        winner_name=case.winning_company,
        winner_location=case.winning_company_address,
        contract_date=case.award_date.isoformat() if case.award_date else None,
        description=case.overview,
        notes=case.remarks,
        status="active" if case.document_submission_date and case.document_submission_date >= datetime.now().date() else "completed",
        is_eligible_to_bid=case.is_eligible_to_bid,
        eligibility_reason=case.eligibility_reason,
        eligibility_details=case.eligibility_details,
        created_at=case.created_at.isoformat(),
        updated_at=case.updated_at.isoformat(),
        # Additional fields
        search_condition=case.search_condition,
        bidding_format=case.bidding_format,
        case_url=case.case_url,
        delivery_location=case.delivery_location,
        bidding_date=case.bidding_date.isoformat() if case.bidding_date else None,
        briefing_date=case.briefing_date.isoformat() if case.briefing_date else None,
        award_announcement_date=case.award_announcement_date.isoformat() if case.award_announcement_date else None,
        business_types_normalized=case.business_types_normalized,
        planned_price_raw=case.planned_price_raw,
        planned_unit_price=case.planned_unit_price,
        award_price_raw=case.award_price_raw,
        award_unit_price=case.award_unit_price,
        main_price=case.main_price,
        winning_reason=case.winning_reason,
        winning_score=case.winning_score,
        award_remarks=case.award_remarks,
        bid_result_details=case.bid_result_details,
        unsuccessful_bid=case.unsuccessful_bid,
        processed_at=case.processed_at.isoformat() if case.processed_at else None,
        qualification_confidence=case.qualification_confidence
    )


@router.post("/cases", response_model=BiddingCaseResponse)
async def create_bidding_case(
    case: BiddingCaseCreate,
    db: Session = Depends(get_db)
):
    repo = BiddingCaseRepository(db)
    existing = repo.get_by_case_id(case.case_id)
    if existing:
        raise HTTPException(status_code=400, detail="Case ID already exists")

    db_case = repo.create(case)
    return BiddingCaseResponse(
        **db_case.__dict__,
        has_embedding=bool(db_case.embedding)
    )


@router.get("/cases", response_model=BiddingCaseListResponse)
async def list_bidding_cases(
    page: int = Query(1, ge=1, alias="page"),
    limit: int = Query(20, ge=1, le=100, alias="limit"),
    eligible_only: bool = Query(False, description="Filter for eligible cases only"),
    db: Session = Depends(get_db)
):
    repo = BiddingCaseRepository(db)
    skip = (page - 1) * limit

    cases = repo.get_all(skip=skip, limit=limit, eligible_only=eligible_only)
    total = repo.count(eligible_only=eligible_only)

    return BiddingCaseListResponse(
        cases=[map_to_frontend_response(case) for case in cases],
        total=total,
        page=page,
        pages=(total + limit - 1) // limit if limit > 0 else 0
    )


@router.get("/cases/{case_id}", response_model=BiddingCaseResponse)
async def get_bidding_case(
    case_id: UUID,
    db: Session = Depends(get_db)
):
    repo = BiddingCaseRepository(db)
    case = repo.get_by_id(case_id)

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    return BiddingCaseResponse(
        **case.__dict__,
        has_embedding=bool(case.embedding)
    )


@router.get("/cases/by-case-id/{case_id}", response_model=BiddingCaseResponse)
async def get_bidding_case_by_case_id(
    case_id: str,
    db: Session = Depends(get_db)
):
    repo = BiddingCaseRepository(db)
    case = repo.get_by_case_id(case_id)

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    return BiddingCaseResponse(
        **case.__dict__,
        has_embedding=bool(case.embedding)
    )


@router.patch("/cases/{case_id}", response_model=BiddingCaseResponse)
async def update_bidding_case(
    case_id: UUID,
    case_update: BiddingCaseUpdate,
    db: Session = Depends(get_db)
):
    repo = BiddingCaseRepository(db)
    case = repo.update(case_id, case_update)

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    return BiddingCaseResponse(
        **case.__dict__,
        has_embedding=bool(case.embedding)
    )


@router.delete("/cases/{case_id}")
async def delete_bidding_case(
    case_id: UUID,
    db: Session = Depends(get_db)
):
    repo = BiddingCaseRepository(db)
    if not repo.delete(case_id):
        raise HTTPException(status_code=404, detail="Case not found")

    return {"message": "Case deleted successfully"}


@router.get("/stats", response_model=BiddingStatsResponse)
async def get_bidding_stats(
    db: Session = Depends(get_db)
):
    repo = BiddingCaseRepository(db)
    
    total_cases = repo.count()
    active_cases = repo.count_active()
    completed_cases = total_cases - active_cases
    eligible_cases = repo.count_eligible()
    ineligible_cases = repo.count_ineligible()
    eligibility_percentage = (eligible_cases / total_cases * 100) if total_cases > 0 else 0.0
    
    total_value = repo.get_total_value() or 0.0
    average_value = repo.get_average_value() or 0.0
    
    prefecture_distribution = repo.get_prefecture_distribution()
    business_type_distribution = repo.get_business_type_distribution()
    recent_trends = repo.get_recent_trends(days=30)
    
    return BiddingStatsResponse(
        total_cases=total_cases,
        total_value=total_value,
        active_cases=active_cases,
        completed_cases=completed_cases,
        average_winning_price=average_value,
        eligible_cases=eligible_cases,
        ineligible_cases=ineligible_cases,
        eligibility_percentage=eligibility_percentage,
        cases_by_prefecture=prefecture_distribution,
        cases_by_industry=business_type_distribution,
        recent_trends=recent_trends
    )
