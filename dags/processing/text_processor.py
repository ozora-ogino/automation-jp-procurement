#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Text processing service for extracting and processing document content.
Refactored from preprocessor.py.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

from utils.file_service import FileService

logger = logging.getLogger(__name__)

# Try to import PDF processing libraries
try:
    from langchain.document_loaders import PyPDFLoader
    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("langchain not installed. PDF processing will be limited.")
    LANGCHAIN_AVAILABLE = False


class TextProcessor:
    """Service for processing various document formats and extracting text"""
    
    def __init__(self, file_service: FileService):
        self.file_service = file_service
        self.supported_extensions = {
            '.pdf': self._process_pdf,
            '.html': self._process_html,
            '.htm': self._process_html,
            '.txt': self._process_text,
            '.md': self._process_text,
        }
    
    def process_document(self, file_path: Path) -> str:
        """Process a document and extract text content"""
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return ""
        
        extension = file_path.suffix.lower()
        processor = self.supported_extensions.get(extension)
        
        if processor:
            return processor(file_path)
        else:
            logger.warning(f"Unsupported file type: {extension}")
            return ""
    
    def _process_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file"""
        if not LANGCHAIN_AVAILABLE:
            logger.warning(f"Cannot process PDF {file_path.name}: langchain not available")
            return ""
        
        try:
            loader = PyPDFLoader(str(file_path))
            pages = loader.load()
            
            text_content = []
            for i, page in enumerate(pages):
                page_text = page.page_content.strip()
                if page_text:
                    text_content.append(f"[Page {i+1}]\n{page_text}")
            
            return "\n\n".join(text_content)
            
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            return ""
    
    def _process_html(self, file_path: Path) -> str:
        """Extract text from HTML file"""
        try:
            # Check if it's actually an HTML file
            with open(file_path, 'rb') as f:
                header = f.read(8)
                # Check for OLE header (MS Office format)
                if header[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                    logger.info(f"File {file_path.name} is actually an Excel file")
                    return "[File is Excel format with .html extension, cannot process]"
            
            # Try multiple encodings
            content = None
            for encoding in ['utf-8', 'shift_jis', 'euc-jp', 'iso-2022-jp']:
                try:
                    content = self.file_service.read_text(file_path)
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                logger.error(f"Could not decode HTML file {file_path}")
                return ""
            
            # Parse HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'meta', 'link']):
                element.decompose()
            
            # Extract text
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.error(f"Error processing HTML {file_path}: {e}")
            return ""
    
    def _process_text(self, file_path: Path) -> str:
        """Process plain text file"""
        try:
            return self.file_service.read_text(file_path)
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            return ""
    
    def concatenate_documents(self, file_paths: List[Path], output_path: Path) -> Optional[Path]:
        """Concatenate multiple documents into a single text file"""
        try:
            combined_texts = []
            
            for file_path in file_paths:
                if not file_path.exists():
                    logger.warning(f"File not found, skipping: {file_path}")
                    continue
                
                text = self.process_document(file_path)
                if text:
                    combined_texts.append(f"=== {file_path.name} ===\n{text}")
            
            if combined_texts:
                final_text = "\n\n".join(combined_texts)
                self.file_service.write_text(final_text, output_path)
                logger.info(f"Concatenated {len(combined_texts)} documents to {output_path}")
                return output_path
            else:
                logger.warning("No valid documents to concatenate")
                return None
                
        except Exception as e:
            logger.error(f"Error concatenating documents: {e}")
            return None