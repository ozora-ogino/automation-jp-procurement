#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit tests for file service"""

import pytest
import tempfile
import json
from pathlib import Path
import pandas as pd

from utils.file_service import FileService


class TestFileService:
    """Test cases for file service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.file_service = FileService(base_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_write_read_text(self):
        """Test text file operations"""
        test_path = Path(self.temp_dir) / "test.txt"
        test_content = "Hello, World!"
        
        # Write
        self.file_service.write_text(test_content, test_path)
        assert test_path.exists()
        
        # Read
        content = self.file_service.read_text(test_path)
        assert content == test_content
    
    def test_write_read_json(self):
        """Test JSON file operations"""
        test_path = Path(self.temp_dir) / "test.json"
        test_data = {"key": "value", "number": 42}
        
        # Write
        self.file_service.write_json(test_data, test_path)
        assert test_path.exists()
        
        # Read
        data = self.file_service.read_json(test_path)
        assert data == test_data
    
    def test_write_read_csv(self):
        """Test CSV file operations"""
        test_path = Path(self.temp_dir) / "test.csv"
        test_df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': ['a', 'b', 'c']
        })
        
        # Write
        self.file_service.write_csv(test_df, test_path)
        assert test_path.exists()
        
        # Read
        df = self.file_service.read_csv(test_path)
        pd.testing.assert_frame_equal(df, test_df)
    
    def test_create_directory(self):
        """Test directory creation"""
        dir_path = Path(self.temp_dir) / "subdir" / "nested"
        created_path = self.file_service.create_directory(dir_path)
        
        assert created_path.exists()
        assert created_path.is_dir()
    
    def test_file_exists(self):
        """Test file existence check"""
        test_path = Path(self.temp_dir) / "test.txt"
        
        assert not self.file_service.file_exists(test_path)
        
        self.file_service.write_text("content", test_path)
        assert self.file_service.file_exists(test_path)
    
    def test_get_file_size(self):
        """Test file size calculation"""
        test_path = Path(self.temp_dir) / "test.txt"
        test_content = "Hello, World!"
        
        # Non-existent file
        assert self.file_service.get_file_size(test_path) == 0
        
        # Existing file
        self.file_service.write_text(test_content, test_path)
        size = self.file_service.get_file_size(test_path)
        assert size == len(test_content.encode('utf-8'))
    
    def test_list_files(self):
        """Test file listing"""
        # Create test files
        self.file_service.write_text("1", Path(self.temp_dir) / "file1.txt")
        self.file_service.write_text("2", Path(self.temp_dir) / "file2.txt")
        self.file_service.write_json({}, Path(self.temp_dir) / "data.json")
        
        # List all files
        all_files = self.file_service.list_files(self.temp_dir)
        assert len(all_files) == 3
        
        # List with pattern
        txt_files = self.file_service.list_files(self.temp_dir, "*.txt")
        assert len(txt_files) == 2