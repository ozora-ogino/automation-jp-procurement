#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit tests for repository classes"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from db.repositories import BiddingCaseRepository, JobExecutionLogRepository
from db.connection import PostgreSQLConnection


class TestBiddingCaseRepository:
    """Test cases for BiddingCase repository"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Mock database connection
        self.mock_db = Mock(spec=PostgreSQLConnection)
        self.repo = BiddingCaseRepository(self.mock_db)
    
    def test_find_unprocessed_cases(self):
        """Test finding unprocessed cases"""
        # Mock cursor and results
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('case001', '/path/to/docs'),
            ('case002', '/path/to/docs2')
        ]
        
        self.mock_db.get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Call method
        results = self.repo.find_unprocessed_cases(limit=10)
        
        # Assertions
        assert len(results) == 2
        assert results[0]['case_id'] == 'case001'
        assert results[1]['case_id'] == 'case002'
        
        # Verify SQL was called correctly
        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        assert 'llm_extracted_data IS NULL' in sql
        assert 'LIMIT' in sql
    
    def test_get_case_by_id(self):
        """Test getting case by ID"""
        # Mock cursor and result
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ('case001', 'Test Case', 'Test Org')
        mock_cursor.description = [
            ('case_id',), ('case_name',), ('organization_name',)
        ]
        
        self.mock_db.get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Call method
        result = self.repo.get_case_by_id('case001')
        
        # Assertions
        assert result is not None
        assert result['case_id'] == 'case001'
        assert result['case_name'] == 'Test Case'
        assert result['organization_name'] == 'Test Org'
    
    def test_upsert_new_case(self):
        """Test inserting a new case"""
        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # Case doesn't exist
        
        self.mock_db.get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Test data
        case_data = {
            'case_id': 'case001',
            'case_name': 'Test Case',
            'organization_name': 'Test Org'
        }
        
        # Call method
        success, is_new = self.repo.upsert_bidding_case(case_data)
        
        # Assertions
        assert success is True
        assert is_new is True
        
        # Verify INSERT was called
        calls = mock_cursor.execute.call_args_list
        assert len(calls) == 2  # SELECT + INSERT
        assert 'INSERT INTO' in calls[1][0][0]
    
    def test_update_llm_extraction(self):
        """Test updating LLM extraction data"""
        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        
        self.mock_db.get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Test data
        extracted_data = {
            'summary': 'Test summary',
            'requirements': ['req1', 'req2']
        }
        
        # Call method
        success = self.repo.update_llm_extraction('case001', extracted_data)
        
        # Assertions
        assert success is True
        
        # Verify UPDATE was called
        calls = mock_cursor.execute.call_args_list
        assert any('ALTER TABLE' in str(call) for call in calls)
        assert any('UPDATE bidding_cases' in str(call) for call in calls)


class TestJobExecutionLogRepository:
    """Test cases for JobExecutionLog repository"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_db = Mock(spec=PostgreSQLConnection)
        self.repo = JobExecutionLogRepository(self.mock_db)
    
    def test_create_log(self):
        """Test creating a job log"""
        # Mock cursor
        mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Call method
        self.repo.create_log(
            job_name='test_job',
            status='success',
            records_processed=100,
            new_records_added=10
        )
        
        # Verify INSERT was called
        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        assert 'INSERT INTO job_execution_logs' in sql
    
    def test_get_recent_logs(self):
        """Test getting recent logs"""
        # Mock cursor and results
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('test_job', 'success', 100, datetime.now()),
        ]
        mock_cursor.description = [
            ('job_name',), ('status',), ('records_processed',), ('created_at',)
        ]
        
        self.mock_db.get_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Call method
        results = self.repo.get_recent_logs(job_name='test_job', limit=5)
        
        # Assertions
        assert len(results) == 1
        assert results[0]['job_name'] == 'test_job'
        assert results[0]['status'] == 'success'