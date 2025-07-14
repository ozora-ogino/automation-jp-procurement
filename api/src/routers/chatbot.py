from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import logging
from pathlib import Path

from openai import OpenAI
from src.database import get_db
from src.models import BiddingCase

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    case_id: str
    message: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    response: str
    context_used: bool
    error: Optional[str] = None


class ChatbotService:
    """Service for handling case-specific chatbot interactions"""
    
    SYSTEM_PROMPT = """あなたは日本政府調達・入札案件の専門アシスタントです。
ユーザーから特定の入札案件について質問を受けた際、その案件の文書内容に基づいて正確かつ有用な回答を提供してください。

重要な指示:
1. 提供された案件文書の内容に基づいて回答してください
2. 文書に記載されていない情報について推測しないでください
3. 不明な点は「文書に記載がありません」と明確に伝えてください
4. 専門用語は適切に説明してください
5. 入札参加の判断に役立つ実用的な情報を優先してください"""

    CHAT_PROMPT_TEMPLATE = """以下は入札案件「{case_name}」（案件ID: {case_id}）に関する文書内容です：

---
{document_content}
---

ユーザーの質問: {user_question}

上記の文書内容に基づいて、ユーザーの質問に回答してください。"""

    def __init__(self, openai_api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model
        
    def generate_response(self, 
                         case_data: Dict[str, Any],
                         document_content: str,
                         user_message: str,
                         chat_history: List[ChatMessage]) -> str:
        """Generate chatbot response based on case documents"""
        try:
            # Build conversation history
            messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
            
            # Add document context for the first message or when needed
            if not chat_history or len(chat_history) == 0:
                context_message = self.CHAT_PROMPT_TEMPLATE.format(
                    case_name=case_data.get('case_name', ''),
                    case_id=case_data.get('case_id', ''),
                    document_content=document_content,
                    user_question=user_message
                )
                messages.append({"role": "user", "content": context_message})
            else:
                # Add chat history
                for msg in chat_history[-6:]:  # Keep last 6 messages for context
                    messages.append({"role": msg.role, "content": msg.content})
                
                # Add current message
                messages.append({"role": "user", "content": user_message})
            
            # Generate response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating chatbot response: {e}")
            raise


def get_chatbot_service() -> ChatbotService:
    """Get chatbot service instance"""
    import os
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    return ChatbotService(openai_api_key)


def read_concatenated_document(case_id: str) -> Optional[str]:
    """Read the concatenated document for a case"""
    try:
        # Check standard locations for concatenated files
        base_paths = [
            Path("/data/concatenated"),
            Path("data/concatenated"),
            Path("/app/data/concatenated")
        ]
        
        # The file naming convention is concat_{case_id}.txt
        for base_path in base_paths:
            concat_file = base_path / f"concat_{case_id}.txt"
            if concat_file.exists():
                with open(concat_file, 'r', encoding='utf-8') as f:
                    return f.read()
        
        return None
    except Exception as e:
        logger.error(f"Error reading concatenated document: {e}")
        return None


def prepare_document_content(case: BiddingCase) -> str:
    """Prepare document content for the chatbot"""
    # First try to read concatenated document
    case_id = str(case.case_id)
    concatenated_content = read_concatenated_document(case_id)
    
    if concatenated_content:
        # Truncate if too long
        max_chars = 50000
        if len(concatenated_content) > max_chars:
            concatenated_content = concatenated_content[:max_chars] + "\n\n[... 文書の続きは省略されています ...]"
        return concatenated_content
    
    # Fallback: build content from database fields
    content_parts = []
    
    # Basic information
    content_parts.append(f"案件名: {case.case_name}")
    content_parts.append(f"案件ID: {case.case_id}")
    
    if case.org_name:
        content_parts.append(f"機関名: {case.org_name}")
    if case.org_location:
        content_parts.append(f"所在地: {case.org_location}")
    
    # Dates
    if case.announcement_date:
        content_parts.append(f"公告日: {case.announcement_date}")
    if case.bidding_date:
        content_parts.append(f"入札日: {case.bidding_date}")
    if case.briefing_date:
        content_parts.append(f"説明会日: {case.briefing_date}")
    
    # Qualification requirements
    if case.qualifications_raw:
        content_parts.append(f"\n入札資格要件:\n{case.qualifications_raw}")
    
    # Business content
    if case.overview:
        content_parts.append(f"\n業務概要:\n{case.overview}")
    
    # LLM extracted data
    if case.llm_extracted_data:
        content_parts.append("\n\nAI抽出情報:")
        content_parts.append(json.dumps(case.llm_extracted_data, ensure_ascii=False, indent=2))
    
    # Prices
    if case.planned_price_normalized:
        content_parts.append(f"\n予定価格: {case.planned_price_normalized:,.0f}円")
    
    # Additional info
    if case.remarks:
        content_parts.append(f"\n備考:\n{case.remarks}")
    
    return "\n".join(content_parts)


@router.post("/chat", response_model=ChatResponse)
async def chat_with_case(
    request: ChatRequest,
    db: Session = Depends(get_db),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """Chat about a specific bidding case"""
    try:
        # Get the case from database
        case = db.query(BiddingCase).filter(
            BiddingCase.case_id == int(request.case_id)
        ).first()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Prepare case data
        case_data = {
            'case_id': case.case_id,
            'case_name': case.case_name,
            'organization': case.org_name
        }
        
        # Prepare document content
        document_content = prepare_document_content(case)
        
        if not document_content:
            return ChatResponse(
                response="申し訳ございません。この案件の文書情報が見つかりませんでした。",
                context_used=False,
                error="No document content available"
            )
        
        # Generate response
        response = chatbot_service.generate_response(
            case_data=case_data,
            document_content=document_content,
            user_message=request.message,
            chat_history=request.history
        )
        
        return ChatResponse(
            response=response,
            context_used=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return ChatResponse(
            response="申し訳ございません。エラーが発生しました。しばらくしてから再度お試しください。",
            context_used=False,
            error=str(e)
        )


@router.get("/chat/status/{case_id}")
async def check_chat_availability(
    case_id: str,
    db: Session = Depends(get_db)
):
    """Check if chat is available for a specific case"""
    try:
        case = db.query(BiddingCase).filter(
            BiddingCase.case_id == int(case_id)
        ).first()
        
        if not case:
            return {
                "available": False,
                "reason": "Case not found"
            }
        
        # Check if concatenated document exists
        has_concatenated = read_concatenated_document(str(case.case_id)) is not None
        
        # Check if we have enough data
        has_basic_info = bool(case.case_name and (case.overview or case.qualifications_raw))
        has_llm_data = bool(case.llm_extracted_data)
        
        available = has_concatenated or has_basic_info or has_llm_data
        
        return {
            "available": available,
            "has_concatenated_doc": has_concatenated,
            "has_basic_info": has_basic_info,
            "has_llm_extraction": has_llm_data,
            "document_count": case.document_count or 0
        }
        
    except Exception as e:
        logger.error(f"Error checking chat availability: {e}")
        return {
            "available": False,
            "error": str(e)
        }