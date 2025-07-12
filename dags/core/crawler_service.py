#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Refactored crawler service using the new modular architecture.
This replaces the monolithic crawler.py with a cleaner service-based approach.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from playwright.async_api import async_playwright, Page, BrowserContext

from core.authentication import NJSSAuthenticationService
from utils.file_service import FileService
from utils.file_naming import FileNaming
from constants import CSV_FILE_PATH, DATA_DIR, PLAYWRIGHT_UA

logger = logging.getLogger(__name__)


class NJSSCrawlerService:
    """Service for crawling NJSS website"""
    
    def __init__(self, 
                 auth_service: NJSSAuthenticationService,
                 file_service: FileService,
                 base_url: str = "https://www.njss.info",
                 headless: bool = True,
                 timeout: int = 30000):
        self.auth_service = auth_service
        self.file_service = file_service
        self.base_url = base_url
        self.headless = headless
        self.timeout = timeout
        # Use the correct NJSS URLs based on original crawler
        self.login_url = "https://www2.njss.info/users/login"
        self.search_url = "https://www.njss.info/offers/"
    
    async def crawl_and_save(self, output_path: str = CSV_FILE_PATH) -> Dict[str, Any]:
        """
        Main entry point for crawling NJSS and saving results.
        Returns statistics about the crawl.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            context = await browser.new_context(
                user_agent=PLAYWRIGHT_UA,
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = await context.new_page()
            
            try:
                # Login if required
                await page.goto(self.login_url)
                login_success = await self.auth_service.login(page, self.login_url)
                
                if not login_success:
                    raise Exception("Login failed")
                
                # Navigate to search page
                await page.goto(self.search_url, wait_until='networkidle')
                
                # Perform search and collect results
                results = await self._search_and_collect(page)
                
                # Save results
                self.file_service.write_csv(results, output_path)
                
                # Also save as JSON for backup
                json_path = Path(output_path).with_suffix('.json')
                self.file_service.write_json(results, json_path)
                
                logger.info(f"Crawl completed. Found {len(results)} results")
                
                return {
                    'success': True,
                    'records_found': len(results),
                    'output_path': output_path,
                    'timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Crawl failed: {str(e)}")
                
                # Take screenshot for debugging
                if not self.headless:
                    await self.file_service.take_screenshot(page, "crawl_error", "error")
                
                return {
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                
            finally:
                await browser.close()
    
    async def _search_and_collect(self, page: Page) -> List[Dict[str, Any]]:
        """
        Perform search and collect all results.
        This is a simplified version - expand based on actual requirements.
        """
        results = []
        
        # TODO: Implement actual search logic based on NJSS website structure
        # This is a placeholder implementation
        
        # Wait for results to load
        await page.wait_for_selector('.search-results', timeout=self.timeout)
        
        # Extract case information
        cases = await page.query_selector_all('.case-item')
        
        for case in cases:
            case_data = await self._extract_case_data(case)
            if case_data:
                results.append(case_data)
        
        # Handle pagination if needed
        # TODO: Implement pagination logic
        
        return results
    
    async def _extract_case_data(self, element) -> Optional[Dict[str, Any]]:
        """Extract data from a single case element"""
        try:
            # TODO: Implement actual data extraction based on NJSS HTML structure
            # This is a placeholder
            
            case_data = {
                '案件ID': await self._safe_extract_text(element, '.case-id'),
                '案件名': await self._safe_extract_text(element, '.case-name'),
                '機関名': await self._safe_extract_text(element, '.organization'),
                '調達方式': await self._safe_extract_text(element, '.procurement-type'),
                '公開日': await self._safe_extract_text(element, '.publication-date'),
                '締切日': await self._safe_extract_text(element, '.deadline'),
                '案件URL': await self._safe_extract_href(element, '.case-link'),
                'timestamp': datetime.now().isoformat()
            }
            
            return case_data
            
        except Exception as e:
            logger.error(f"Error extracting case data: {e}")
            return None
    
    async def _safe_extract_text(self, element, selector: str) -> str:
        """Safely extract text from element"""
        try:
            sub_element = await element.query_selector(selector)
            if sub_element:
                return await sub_element.text_content()
            return ""
        except:
            return ""
    
    async def _safe_extract_href(self, element, selector: str) -> str:
        """Safely extract href from element"""
        try:
            sub_element = await element.query_selector(selector)
            if sub_element:
                href = await sub_element.get_attribute('href')
                if href and not href.startswith('http'):
                    href = f"{self.base_url}{href}"
                return href
            return ""
        except:
            return ""