#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ProcurementType(Enum):
    """Enum for procurement types"""
    GENERAL_COMPETITIVE = "一般競争入札"
    DESIGNATED_COMPETITIVE = "指名競争入札"
    NEGOTIATED_CONTRACT = "随意契約"
    PROPOSAL_REQUEST = "企画競争"
    PUBLIC_OFFERING = "公募"
    OTHER = "その他"


class JobStatus(Enum):
    """Enum for job execution status"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    RUNNING = "running"


@dataclass
class BiddingCase:
    """Data model for a bidding case"""
    case_id: str
    case_name: str
    organization_name: str
    
    # Optional fields
    department_name: Optional[str] = None  # Maps to org_location in DB
    procurement_type: Optional[str] = None  # Maps to bidding_format in DB
    details: Optional[str] = None  # Maps to overview in DB
    publication_date: Optional[datetime] = None  # Maps to announcement_date in DB
    deadline_date: Optional[datetime] = None  # Maps to document_submission_date in DB
    delivery_deadline: Optional[datetime] = None
    delivery_location: Optional[str] = None
    bid_opening_date: Optional[datetime] = None  # Maps to bidding_date in DB
    bid_opening_location: Optional[str] = None
    contact_point: Optional[str] = None
    qualification_info: Optional[str] = None  # Maps to qualifications_raw in DB
    remarks: Optional[str] = None
    attachment_info: Optional[str] = None
    
    # Additional date fields
    briefing_date: Optional[datetime] = None
    award_announcement_date: Optional[datetime] = None
    award_date: Optional[datetime] = None
    
    # Business and price information
    business_types_raw: Optional[str] = None
    search_condition: Optional[str] = None
    planned_price_raw: Optional[str] = None
    award_price_raw: Optional[str] = None
    
    # Winning information
    winning_company: Optional[str] = None
    winning_company_address: Optional[str] = None
    winning_reason: Optional[str] = None
    award_remarks: Optional[str] = None
    unsuccessful_bid: Optional[str] = None
    
    # URLs and file info
    related_info_url: Optional[str] = None
    anken_url: Optional[str] = None  # Maps to case_url in DB
    document_directory: Optional[str] = None
    document_count: int = 0
    
    # LLM extracted data
    llm_extracted_data: Optional[Dict[str, Any]] = None
    llm_extraction_timestamp: Optional[datetime] = None
    
    # AI analysis results
    is_target: Optional[bool] = None
    match_score: Optional[float] = None
    reasons: Optional[List[str]] = field(default_factory=list)
    ai_summary: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        data = {
            'case_id': self.case_id,
            'case_name': self.case_name,
            'organization_name': self.organization_name,
            'document_count': self.document_count
        }
        
        # Add optional fields if they have values
        optional_fields = [
            'department_name', 'procurement_type', 'details',
            'delivery_location', 'bid_opening_location', 'contact_point',
            'qualification_info', 'remarks', 'attachment_info',
            'related_info_url', 'anken_url', 'document_directory',
            'is_target', 'match_score', 'ai_summary',
            'business_types_raw', 'search_condition', 'planned_price_raw',
            'award_price_raw', 'winning_company', 'winning_company_address',
            'winning_reason', 'award_remarks', 'unsuccessful_bid'
        ]
        
        for field_name in optional_fields:
            value = getattr(self, field_name)
            if value is not None:
                data[field_name] = value
        
        # Handle datetime fields
        datetime_fields = [
            'publication_date', 'deadline_date', 'delivery_deadline',
            'bid_opening_date', 'llm_extraction_timestamp',
            'briefing_date', 'award_announcement_date', 'award_date'
        ]
        
        for field_name in datetime_fields:
            value = getattr(self, field_name)
            if value is not None:
                data[field_name] = value.isoformat() if isinstance(value, datetime) else value
        
        # Handle list/dict fields
        if self.reasons:
            data['reasons'] = self.reasons
        
        if self.llm_extracted_data:
            data['llm_extracted_data'] = self.llm_extracted_data
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BiddingCase':
        """Create instance from dictionary"""
        # Convert datetime strings back to datetime objects
        datetime_fields = [
            'publication_date', 'deadline_date', 'delivery_deadline',
            'bid_opening_date', 'llm_extraction_timestamp', 'created_at', 'updated_at',
            'briefing_date', 'award_announcement_date', 'award_date'
        ]
        
        for field_name in datetime_fields:
            if field_name in data and data[field_name]:
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name])
        
        return cls(**data)


@dataclass
class JobExecutionLog:
    """Data model for job execution logs"""
    job_name: str
    status: str
    records_processed: int = 0
    new_records_added: int = 0
    updated_records: int = 0
    error_message: Optional[str] = None
    execution_duration_seconds: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None


@dataclass
class Document:
    """Data model for a document"""
    case_id: str
    document_name: str
    document_url: str
    document_type: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    download_status: Optional[str] = None
    download_timestamp: Optional[datetime] = None
    text_content: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'case_id': self.case_id,
            'document_name': self.document_name,
            'document_url': self.document_url,
            'document_type': self.document_type,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'download_status': self.download_status,
            'download_timestamp': self.download_timestamp.isoformat() if self.download_timestamp else None,
            'text_content': self.text_content
        }