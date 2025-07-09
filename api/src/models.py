from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, func, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid

Base = declarative_base()


class BiddingCase(Base):
    __tablename__ = "bidding_cases"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(BigInteger, unique=True, nullable=False, index=True)
    case_name = Column(Text, nullable=False)
    search_condition = Column(Text)
    bidding_format = Column(Text)
    case_url = Column(Text)
    
    # Organization info
    org_name = Column(Text)
    org_location = Column(Text)
    org_prefecture = Column(Text)
    delivery_location = Column(Text)
    
    # Schedule info
    announcement_date = Column(DateTime)
    bidding_date = Column(DateTime)
    document_submission_date = Column(DateTime)
    briefing_date = Column(DateTime)
    award_announcement_date = Column(DateTime)
    award_date = Column(DateTime)
    
    # Qualification requirements
    qualifications_raw = Column(Text)
    qualifications_parsed = Column(JSON)
    qualifications_summary = Column(JSON)
    business_types_raw = Column(Text)
    business_types_normalized = Column(ARRAY(Text))
    business_type = Column(ARRAY(Text))
    business_type_code = Column(ARRAY(Text))
    
    # Content
    overview = Column(Text)
    remarks = Column(Text)
    
    # Price info
    planned_price_raw = Column(Text)
    planned_price_normalized = Column(Float)
    planned_unit_price = Column(Float)
    award_price_raw = Column(Text)
    award_price_normalized = Column(Float)
    award_unit_price = Column(Float)
    main_price = Column(Float)
    
    # Award info
    winning_company = Column(Text)
    winning_company_address = Column(Text)
    winning_reason = Column(Text)
    winning_score = Column(Float)
    award_remarks = Column(Text)
    bid_result_details = Column(JSON)
    unsuccessful_bid = Column(Text)
    
    # Processing info
    processed_at = Column(DateTime)
    qualification_confidence = Column(Float)
    
    # Eligibility info
    is_eligible_to_bid = Column(Boolean)
    eligibility_details = Column(JSON)
    eligibility_reason = Column(Text)
    
    # Document info
    document_directory = Column(Text)
    document_count = Column(Integer, default=0)
    downloaded_count = Column(Integer, default=0)
    documents = Column(JSON)  # Array of document info: [{name, type, url, path}]
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    search_vector = Column(TSVECTOR)
    
    embedding = relationship("CaseEmbedding", back_populates="bidding_case", uselist=False)


class CaseEmbedding(Base):
    __tablename__ = "case_embeddings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(BigInteger, ForeignKey("bidding_cases.case_id"), unique=True, nullable=False)
    
    # Vector data
    case_name_embedding = Column(Vector(3072))
    overview_embedding = Column(Vector(3072))
    combined_embedding = Column(Vector(3072))
    
    # Metadata
    embedding_model = Column(String(100), default="text-embedding-3-large")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    bidding_case = relationship("BiddingCase", back_populates="embedding")


class JobExecutionLog(Base):
    __tablename__ = "job_execution_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_name = Column(Text, nullable=False)
    execution_time = Column(DateTime, server_default=func.now())
    status = Column(String(50))  # 'running', 'success', 'failed', 'timeout'
    records_processed = Column(Integer, default=0)
    new_records_added = Column(Integer, default=0)
    updated_records = Column(Integer, default=0)
    error_message = Column(Text)
    execution_duration_seconds = Column(Integer)
    job_metadata = Column(JSON)