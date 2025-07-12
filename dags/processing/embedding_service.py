#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Text embedding service for semantic search capabilities.
Refactored from text_embedding.py.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from openai import OpenAI

from db.repositories import BiddingCaseRepository, BiddingEmbeddingRepository

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing text embeddings"""
    
    def __init__(self,
                 case_repository: BiddingCaseRepository,
                 embedding_repository: BiddingEmbeddingRepository,
                 openai_api_key: str,
                 model: str = "text-embedding-ada-002"):
        self.case_repo = case_repository
        self.embedding_repo = embedding_repository
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model
    
    def generate_embeddings_batch(self, limit: int = 100) -> Dict[str, Any]:
        """Generate embeddings for cases without embeddings"""
        start_time = datetime.now()
        processed_count = 0
        success_count = 0
        errors = []
        
        try:
            # Get cases that need embeddings
            cases = self._get_cases_without_embeddings(limit)
            logger.info(f"Found {len(cases)} cases needing embeddings")
            
            for case in cases:
                try:
                    # Create text for embedding
                    text = self._create_embedding_text(case)
                    
                    if not text:
                        logger.warning(f"No text to embed for case {case['case_id']}")
                        continue
                    
                    # Generate embedding
                    embedding = self._generate_embedding(text)
                    
                    if embedding:
                        # Store embedding
                        success = self.embedding_repo.create_embedding(
                            case['case_id'],
                            embedding,
                            self.model
                        )
                        
                        if success:
                            success_count += 1
                            logger.info(f"Generated embedding for case {case['case_id']}")
                        else:
                            errors.append(f"Failed to store embedding for case {case['case_id']}")
                    else:
                        errors.append(f"Failed to generate embedding for case {case['case_id']}")
                    
                    processed_count += 1
                    
                except Exception as e:
                    error_msg = f"Error processing case {case['case_id']}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    processed_count += 1
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'total_cases': len(cases),
                'processed': processed_count,
                'successful': success_count,
                'errors': errors,
                'duration_seconds': duration
            }
            
        except Exception as e:
            logger.error(f"Embedding batch failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_cases_without_embeddings(self, limit: int) -> List[Dict[str, Any]]:
        """Get cases that don't have embeddings yet"""
        with self.case_repo.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    bc.case_id, bc.case_name, bc.org_name as organization_name,
                    bc.bidding_format as procurement_type, bc.overview as details, 
                    bc.eligibility_reason as ai_summary
                FROM bidding_cases bc
                LEFT JOIN bidding_anken_embeddings be ON bc.case_id = be.case_id
                WHERE be.case_id IS NULL
                ORDER BY bc.created_at DESC
                LIMIT %s
            """, (limit,))
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    def _create_embedding_text(self, case: Dict[str, Any]) -> str:
        """Create text representation for embedding"""
        parts = []
        
        # Add case name
        if case.get('case_name'):
            parts.append(f"案件名: {case['case_name']}")
        
        # Add organization
        if case.get('organization_name'):
            parts.append(f"機関名: {case['organization_name']}")
        
        # Add procurement type
        if case.get('procurement_type'):
            parts.append(f"調達方式: {case['procurement_type']}")
        
        # Add details
        if case.get('details'):
            parts.append(f"詳細: {case['details'][:500]}")  # Limit length
        
        # Add AI summary if available
        if case.get('ai_summary'):
            parts.append(f"概要: {case['ai_summary']}")
        
        return '\n'.join(parts)
    
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding vector for text"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def search_similar_cases(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar cases using semantic search"""
        try:
            # Generate embedding for query
            query_embedding = self._generate_embedding(query)
            
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Search similar cases
            results = self.embedding_repo.find_similar_cases(query_embedding, limit)
            
            return results
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []