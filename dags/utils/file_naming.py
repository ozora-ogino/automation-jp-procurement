#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from datetime import datetime
from pathlib import Path
from typing import Optional


class FileNaming:
    """Centralized file naming utilities for consistent naming across the system"""
    
    # File prefixes
    NJSS_PREFIX = "njss"
    SEARCH_RESULT_PREFIX = "search_result"
    CONCAT_PREFIX = "concat"
    
    # File extensions
    PDF_EXT = ".pdf"
    CSV_EXT = ".csv"
    JSON_EXT = ".json"
    TXT_EXT = ".txt"
    HTML_EXT = ".html"
    
    # Common extensions for sanitization
    DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.html', '.htm', '.txt']
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for filesystem safety"""
        # Remove or replace unsafe characters
        safe_name = re.sub(r'[^\w\s\-\.]', '_', filename).strip()
        
        # Remove multiple underscores
        safe_name = re.sub(r'_+', '_', safe_name)
        
        # Remove leading/trailing underscores
        safe_name = safe_name.strip('_')
        
        return safe_name
    
    @staticmethod
    def remove_extension_from_name(filename: str) -> str:
        """Remove common extensions if they appear in the filename"""
        base_name = filename
        for ext in FileNaming.DOCUMENT_EXTENSIONS:
            if base_name.lower().endswith(ext):
                base_name = base_name[:-len(ext)]
                break
        return base_name
    
    @staticmethod
    def get_timestamped_filename(prefix: str, extension: str, timestamp: Optional[datetime] = None) -> str:
        """Generate a timestamped filename"""
        if timestamp is None:
            timestamp = datetime.now()
        
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp_str}{extension}"
    
    @staticmethod
    def get_njss_screenshot_name(stage: str, timestamp: Optional[datetime] = None) -> str:
        """Generate NJSS screenshot filename"""
        if timestamp is None:
            timestamp = datetime.now()
        
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        safe_stage = FileNaming.sanitize_filename(stage)
        return f"{FileNaming.NJSS_PREFIX}_{safe_stage}_{timestamp_str}.png"
    
    @staticmethod
    def get_case_document_path(case_id: str, doc_name: str, doc_type: str) -> Path:
        """Generate path for case documents"""
        safe_case_id = FileNaming.sanitize_filename(case_id)
        safe_doc_name = FileNaming.sanitize_filename(doc_name)
        
        # Remove extension from doc_name if present
        base_name = FileNaming.remove_extension_from_name(safe_doc_name)
        
        # Add appropriate extension
        if doc_type.lower() == 'pdf' and not base_name.lower().endswith('.pdf'):
            filename = f"{base_name}{FileNaming.PDF_EXT}"
        else:
            filename = base_name
            
        return Path(safe_case_id) / filename
    
    @staticmethod
    def get_concat_filename(case_id: str) -> str:
        """Generate concatenated text filename for a case"""
        safe_case_id = FileNaming.sanitize_filename(case_id)
        return f"{FileNaming.CONCAT_PREFIX}_{safe_case_id}{FileNaming.TXT_EXT}"
    
    @staticmethod
    def get_search_result_filename(timestamp: Optional[datetime] = None) -> str:
        """Generate search result CSV filename"""
        return FileNaming.get_timestamped_filename(
            FileNaming.SEARCH_RESULT_PREFIX, 
            FileNaming.CSV_EXT, 
            timestamp
        )
    
    @staticmethod
    def get_temp_filename(prefix: str, extension: str) -> str:
        """Generate temporary filename with timestamp"""
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_prefix = FileNaming.sanitize_filename(prefix)
        return f"tmp_{safe_prefix}_{timestamp_str}{extension}"