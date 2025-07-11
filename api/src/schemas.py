from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID


class BiddingCaseBase(BaseModel):
    case_id: int = Field(..., description="Unique case identifier")
    case_name: str = Field(..., description="Case name/title")
    search_condition: Optional[str] = Field(None, description="Search condition")
    bidding_format: Optional[str] = Field(None, description="Bidding format")
    case_url: Optional[str] = Field(None, description="Case URL")
    
    # Organization info
    org_name: Optional[str] = Field(None, description="Organization name")
    org_location: Optional[str] = Field(None, description="Organization location")
    org_prefecture: Optional[str] = Field(None, description="Organization prefecture")
    delivery_location: Optional[str] = Field(None, description="Delivery location")
    
    # Schedule info
    announcement_date: Optional[datetime] = Field(None, description="Announcement date")
    bidding_date: Optional[datetime] = Field(None, description="Bidding date")
    document_submission_date: Optional[datetime] = Field(None, description="Document submission deadline")
    briefing_date: Optional[datetime] = Field(None, description="Briefing date")
    award_announcement_date: Optional[datetime] = Field(None, description="Award announcement date")
    award_date: Optional[datetime] = Field(None, description="Award date")
    
    # Qualification requirements
    qualifications_raw: Optional[str] = Field(None, description="Raw qualification text")
    qualifications_parsed: Optional[Any] = Field(None, description="Parsed qualifications")
    qualifications_summary: Optional[Any] = Field(None, description="Qualification summary")
    business_types_raw: Optional[str] = Field(None, description="Raw business types")
    business_types_normalized: Optional[List[str]] = Field(None, description="Normalized business type codes")
    business_type: Optional[List[str]] = Field(None, description="Business type names")
    business_type_code: Optional[List[str]] = Field(None, description="Business type codes")
    
    # Content
    overview: Optional[str] = Field(None, description="Overview")
    remarks: Optional[str] = Field(None, description="Remarks")
    
    # Price info
    planned_price_raw: Optional[str] = Field(None, description="Raw planned price")
    planned_price_normalized: Optional[float] = Field(None, description="Normalized planned price")
    planned_unit_price: Optional[float] = Field(None, description="Planned unit price")
    award_price_raw: Optional[str] = Field(None, description="Raw award price")
    award_price_normalized: Optional[float] = Field(None, description="Normalized award price")
    award_unit_price: Optional[float] = Field(None, description="Award unit price")
    main_price: Optional[float] = Field(None, description="Main price")
    
    # Award info
    winning_company: Optional[str] = Field(None, description="Winning company")
    winning_company_address: Optional[str] = Field(None, description="Winning company address")
    winning_reason: Optional[str] = Field(None, description="Winning reason")
    winning_score: Optional[float] = Field(None, description="Winning score")
    award_remarks: Optional[str] = Field(None, description="Award remarks")
    bid_result_details: Optional[Any] = Field(None, description="Bid result details")
    unsuccessful_bid: Optional[str] = Field(None, description="Unsuccessful bid info")
    
    # Processing info
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    qualification_confidence: Optional[float] = Field(None, description="Qualification parsing confidence score")
    
    # Eligibility info
    is_eligible_to_bid: Optional[bool] = Field(None, description="Whether eligible to bid")
    eligibility_details: Optional[Any] = Field(None, description="Detailed eligibility information")
    eligibility_reason: Optional[str] = Field(None, description="Reason for eligibility determination")
    
    # LLM extracted data
    llm_extracted_data: Optional[Any] = Field(None, description="LLM extracted information")
    llm_extraction_timestamp: Optional[datetime] = Field(None, description="LLM extraction timestamp")


class BiddingCaseCreate(BiddingCaseBase):
    pass


class BiddingCaseUpdate(BaseModel):
    case_name: Optional[str] = None
    search_condition: Optional[str] = None
    bidding_format: Optional[str] = None
    case_url: Optional[str] = None
    
    # Organization info
    org_name: Optional[str] = None
    org_location: Optional[str] = None
    org_prefecture: Optional[str] = None
    delivery_location: Optional[str] = None
    
    # Schedule info
    announcement_date: Optional[datetime] = None
    bidding_date: Optional[datetime] = None
    document_submission_date: Optional[datetime] = None
    briefing_date: Optional[datetime] = None
    award_announcement_date: Optional[datetime] = None
    award_date: Optional[datetime] = None
    
    # Qualification requirements
    qualifications_raw: Optional[str] = None
    qualifications_parsed: Optional[Any] = None
    qualifications_summary: Optional[Any] = None
    business_types_raw: Optional[str] = None
    business_types_normalized: Optional[List[str]] = None
    business_type: Optional[List[str]] = None
    business_type_code: Optional[List[str]] = None
    
    # Content
    overview: Optional[str] = None
    remarks: Optional[str] = None
    
    # Price info
    planned_price_raw: Optional[str] = None
    planned_price_normalized: Optional[float] = None
    planned_unit_price: Optional[float] = None
    award_price_raw: Optional[str] = None
    award_price_normalized: Optional[float] = None
    award_unit_price: Optional[float] = None
    main_price: Optional[float] = None
    
    # Award info
    winning_company: Optional[str] = None
    winning_company_address: Optional[str] = None
    winning_reason: Optional[str] = None
    winning_score: Optional[float] = None
    award_remarks: Optional[str] = None
    bid_result_details: Optional[Any] = None
    unsuccessful_bid: Optional[str] = None
    
    # Processing info
    processed_at: Optional[datetime] = None
    qualification_confidence: Optional[float] = None
    
    # Eligibility info
    is_eligible_to_bid: Optional[bool] = None
    eligibility_details: Optional[Any] = None
    eligibility_reason: Optional[str] = None
    
    # Document info
    document_directory: Optional[str] = None
    document_count: Optional[int] = None
    downloaded_count: Optional[int] = None
    documents: Optional[List[Any]] = None


class BiddingCaseResponse(BiddingCaseBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    has_embedding: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class BiddingCaseFrontendResponse(BaseModel):
    id: str
    case_id: str
    case_name: str
    organization: str
    department: Optional[str] = None
    location: Optional[str] = None
    prefecture: Optional[str] = None
    announcement_date: Optional[str] = None
    deadline: Optional[str] = None
    industry_type: Optional[str] = None
    business_type: Optional[List[str]] = None
    business_type_code: Optional[List[str]] = None
    qualification_requirements: Optional[str] = None
    qualification_details: Optional[Any] = None
    qualification_summary: Optional[Any] = None
    planned_price: Optional[float] = None
    winning_price: Optional[float] = None
    winner_name: Optional[str] = None
    winner_location: Optional[str] = None
    contract_date: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    is_eligible_to_bid: Optional[bool] = None
    eligibility_reason: Optional[str] = None
    eligibility_details: Optional[Any] = None
    created_at: str
    updated_at: str
    
    # Additional fields
    search_condition: Optional[str] = None
    bidding_format: Optional[str] = None
    case_url: Optional[str] = None
    delivery_location: Optional[str] = None
    bidding_date: Optional[str] = None
    briefing_date: Optional[str] = None
    award_announcement_date: Optional[str] = None
    business_types_normalized: Optional[List[str]] = None
    planned_price_raw: Optional[str] = None
    planned_unit_price: Optional[float] = None
    award_price_raw: Optional[str] = None
    award_unit_price: Optional[float] = None
    main_price: Optional[float] = None
    winning_reason: Optional[str] = None
    winning_score: Optional[float] = None
    award_remarks: Optional[str] = None
    bid_result_details: Optional[Any] = None
    unsuccessful_bid: Optional[str] = None
    processed_at: Optional[str] = None
    qualification_confidence: Optional[float] = None
    
    # Document info
    document_directory: Optional[str] = None
    document_count: Optional[int] = None
    downloaded_count: Optional[int] = None
    documents: Optional[List[Any]] = None
    
    # LLM extracted data
    llm_extracted_data: Optional[Any] = None
    llm_extraction_timestamp: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class BiddingCaseListResponse(BaseModel):
    cases: List[BiddingCaseFrontendResponse]
    total: int
    page: int
    pages: int


class VectorSearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    min_similarity: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")


class VectorSearchResult(BaseModel):
    case: BiddingCaseResponse
    similarity: float = Field(..., description="Similarity score (0-1)")
    
    model_config = ConfigDict(from_attributes=True)


class FullTextSearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    fields: Optional[List[str]] = Field(None, description="Fields to search in")


class HealthCheckResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime


class BiddingStatsResponse(BaseModel):
    total_cases: int
    total_value: float
    active_cases: int
    completed_cases: int
    average_winning_price: float
    eligible_cases: int
    ineligible_cases: int
    eligibility_percentage: float
    cases_by_prefecture: Dict[str, int]
    cases_by_industry: Dict[str, int]
    recent_trends: List[Dict[str, Any]]