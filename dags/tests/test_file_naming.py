#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit tests for file naming utility"""

import pytest
from datetime import datetime
from pathlib import Path

from utils.file_naming import FileNaming


class TestFileNaming:
    """Test cases for FileNaming utility"""
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        # Test various unsafe characters
        assert FileNaming.sanitize_filename("file/name") == "file_name"
        assert FileNaming.sanitize_filename("file:name") == "file_name"
        assert FileNaming.sanitize_filename("file*name") == "file_name"
        assert FileNaming.sanitize_filename("file?name") == "file_name"
        assert FileNaming.sanitize_filename("file<>name") == "file_name"
        assert FileNaming.sanitize_filename("file|name") == "file_name"
        
        # Test multiple underscores
        assert FileNaming.sanitize_filename("file___name") == "file_name"
        
        # Test leading/trailing underscores
        assert FileNaming.sanitize_filename("_file_name_") == "file_name"
        
        # Test Japanese characters (should be preserved)
        assert FileNaming.sanitize_filename("案件_2024") == "案件_2024"
    
    def test_remove_extension_from_name(self):
        """Test extension removal"""
        assert FileNaming.remove_extension_from_name("document.pdf") == "document"
        assert FileNaming.remove_extension_from_name("document.PDF") == "document"
        assert FileNaming.remove_extension_from_name("report.docx") == "report"
        assert FileNaming.remove_extension_from_name("data.xlsx") == "data"
        assert FileNaming.remove_extension_from_name("archive.zip") == "archive"
        assert FileNaming.remove_extension_from_name("page.html") == "page"
        
        # No extension
        assert FileNaming.remove_extension_from_name("filename") == "filename"
        
        # Multiple dots
        assert FileNaming.remove_extension_from_name("file.name.pdf") == "file.name"
    
    def test_get_timestamped_filename(self):
        """Test timestamped filename generation"""
        # Test with specific timestamp
        test_time = datetime(2024, 1, 15, 10, 30, 45)
        filename = FileNaming.get_timestamped_filename("backup", ".csv", test_time)
        assert filename == "backup_20240115_103045.csv"
        
        # Test without timestamp (uses current time)
        filename = FileNaming.get_timestamped_filename("log", ".txt")
        assert filename.startswith("log_")
        assert filename.endswith(".txt")
        assert len(filename) == 19  # log_ + 8 date + _ + 6 time + .txt
    
    def test_get_njss_screenshot_name(self):
        """Test NJSS screenshot naming"""
        test_time = datetime(2024, 1, 15, 10, 30, 45)
        
        # Test with various stages
        assert FileNaming.get_njss_screenshot_name("login", test_time) == "njss_login_20240115_103045.png"
        assert FileNaming.get_njss_screenshot_name("before_search", test_time) == "njss_before_search_20240115_103045.png"
        
        # Test with unsafe characters in stage
        assert FileNaming.get_njss_screenshot_name("error/debug", test_time) == "njss_error_debug_20240115_103045.png"
    
    def test_get_case_document_path(self):
        """Test case document path generation"""
        # Normal case
        path = FileNaming.get_case_document_path("CASE-001", "specification.pdf", "pdf")
        assert path == Path("CASE-001") / "specification.pdf"
        
        # With unsafe characters
        path = FileNaming.get_case_document_path("CASE/001", "doc:name.pdf", "pdf")
        assert path == Path("CASE_001") / "doc_name.pdf"
        
        # Extension already in name
        path = FileNaming.get_case_document_path("CASE-001", "document.pdf", "pdf")
        assert path == Path("CASE-001") / "document.pdf"
    
    def test_get_concat_filename(self):
        """Test concatenated filename generation"""
        assert FileNaming.get_concat_filename("CASE-001") == "concat_CASE-001.txt"
        assert FileNaming.get_concat_filename("CASE/001") == "concat_CASE_001.txt"
    
    def test_get_search_result_filename(self):
        """Test search result filename generation"""
        test_time = datetime(2024, 1, 15, 10, 30, 45)
        filename = FileNaming.get_search_result_filename(test_time)
        assert filename == "search_result_20240115_103045.csv"
    
    def test_get_temp_filename(self):
        """Test temporary filename generation"""
        filename = FileNaming.get_temp_filename("download", ".tmp")
        assert filename.startswith("tmp_download_")
        assert filename.endswith(".tmp")
        
        # With unsafe prefix
        filename = FileNaming.get_temp_filename("temp/file", ".dat")
        assert filename.startswith("tmp_temp_file_")
        assert filename.endswith(".dat")