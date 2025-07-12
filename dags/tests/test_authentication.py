#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit tests for authentication service"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from core.authentication import NJSSAuthenticationService


class TestNJSSAuthenticationService:
    """Test cases for NJSS authentication"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.auth_service = NJSSAuthenticationService(
            username="test_user",
            password="test_pass",
            headless=True
        )
    
    @pytest.mark.asyncio
    async def test_login_already_logged_in(self):
        """Test login when already logged in"""
        # Mock page
        page = Mock()
        page.url = "https://www.njss.info/users/home"
        
        # Should return True immediately
        result = await self.auth_service.login(page, "https://www.njss.info/users/login")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_login_successful(self):
        """Test successful login flow"""
        # Mock page with async methods
        page = AsyncMock()
        page.url = "https://www.njss.info/users/login"
        page.context = AsyncMock()
        page.context.cookies = AsyncMock(return_value=[{'name': 'session', 'value': '123'}])
        
        # Mock successful login redirect
        page.goto = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.query_selector = AsyncMock(return_value=AsyncMock())
        page.wait_for_navigation = AsyncMock()
        
        # After login, URL changes to home
        page.url = "https://www.njss.info/users/home"
        
        result = await self.auth_service.login(page, "https://www.njss.info/users/login")
        assert result is True
        assert len(self.auth_service.cookies) > 0
    
    def test_is_logged_in(self):
        """Test URL checking for login status"""
        # Test various URLs
        assert self.auth_service._is_logged_in("https://www.njss.info/users/home") is True
        assert self.auth_service._is_logged_in("https://www.njss.info/users/profile") is True
        assert self.auth_service._is_logged_in("https://www.njss.info/users/login") is False
        assert self.auth_service._is_logged_in("https://www.njss.info/") is False