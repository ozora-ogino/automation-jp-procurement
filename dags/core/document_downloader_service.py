#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Downloader Service - Downloads all documents for bidding cases.
Based on the original implementation but with improved naming and structure.
"""

import os
import re
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import unquote, urljoin

import requests
from playwright.async_api import async_playwright, Page

from core.authentication import NJSSAuthenticationService
from utils.file_service import FileService
from data.models import Document
from constants import DOC_DIR, PLAYWRIGHT_UA

logger = logging.getLogger(__name__)


class DocumentDownloaderService:
    """Service for downloading documents from NJSS bidding cases"""
    
    def __init__(self, auth_service: NJSSAuthenticationService, file_service: FileService):
        self.auth_service = auth_service
        self.file_service = file_service
        self.download_base_dir = str(DOC_DIR)
        Path(self.download_base_dir).mkdir(parents=True, exist_ok=True)
        self.base_url = "https://www2.njss.info"
        self.session = requests.Session()  # Maintain session for HTTP downloads
    
    async def download_documents_for_cases(self, cases: List[Dict[str, str]]) -> List[Dict]:
        """Download documents for multiple cases using a single browser session"""
        all_results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', f'--user-agent={PLAYWRIGHT_UA}']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=PLAYWRIGHT_UA,
                locale='ja-JP',
                timezone_id='Asia/Tokyo'
            )
            
            page = await context.new_page()
            
            # Login once at the beginning
            logger.info("Initial login to NJSS")
            await page.goto(f"{self.base_url}/users/login")
            
            # Perform login
            if not await self._login(page):
                logger.error("Initial login failed")
                await browser.close()
                return all_results
            
            # Process each case with the same browser session
            for i, case in enumerate(cases):
                case_id = case['case_id']
                case_url = case['anken_url']
                
                logger.info(f"\nProcessing {i+1}/{len(cases)}: Case ID {case_id}")
                
                result = await self._process_case_documents(page, case_url, case_id)
                all_results.append(result)
                
                # Add delay between requests to be respectful
                if i < len(cases) - 1:
                    await asyncio.sleep(2)
            
            await browser.close()
        
        return all_results
    
    async def _login(self, page: Page) -> bool:
        """Perform login to NJSS"""
        try:
            current_url = page.url
            if '/users/login' not in current_url:
                logger.info("Already logged in")
                return True
            
            logger.info("Attempting to login...")
            await page.wait_for_timeout(2000)
            
            # Use authentication service
            return await self.auth_service.login(page, page.url)
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    async def _process_case_documents(self, page: Page, case_url: str, case_id: str) -> Dict:
        """Process documents for a single case"""
        result = {
            'case_id': case_id,
            'case_url': case_url,
            'success': True,
            'documents_found': 0,
            'documents_downloaded': 0,
            'files': [],
            'directory': None,
            'error': None
        }
        
        try:
            # Create directory for this case
            case_dir = Path(self.download_base_dir) / str(case_id)
            case_dir.mkdir(exist_ok=True)
            result['directory'] = str(case_dir)
            
            # Navigate to case page
            logger.info(f"Processing case ID {case_id}")
            await page.goto(case_url, wait_until='domcontentloaded')
            
            # Check if login required
            if '/users/login' in page.url:
                logger.info("Login required")
                if not await self._login(page):
                    result['success'] = False
                    result['error'] = "Login failed"
                    return result
                # Navigate back
                await page.goto(case_url, wait_until='domcontentloaded')
            
            # Wait for content
            await page.wait_for_timeout(3000)
            
            # Extract all documents
            documents = await self._extract_all_documents(page, case_id)
            result['documents_found'] = len(documents)
            
            if not documents:
                logger.warning(f"No documents found for case ID {case_id}")
                # Take screenshot for debugging
                await page.screenshot(path=str(case_dir / f"no_docs_found_{case_id}.png"))
                return result
            
            # Save document metadata
            info_path = case_dir / 'documents_info.json'
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(documents, f, ensure_ascii=False, indent=2)
            
            # Save README with case information
            readme_path = case_dir / 'README.txt'
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(f"案件ID: {case_id}\n")
                f.write(f"案件URL: {case_url}\n")
                f.write(f"ダウンロード日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("ドキュメント一覧:\n")
                for doc in documents:
                    f.write(f"- {doc['name']}\n")
                    f.write(f"  URL: {doc['url']}\n")
                    f.write(f"  タイプ: {doc['type']}\n\n")
                
                if any('tokyo.lg.jp' in doc['url'] for doc in documents):
                    f.write("\n注意: 東京都の電子調達システムのドキュメントは、\n")
                    f.write("別途東京都のシステムにログインして取得する必要があります。\n")
                
                if any('e-gunma.lg.jp' in doc['url'] for doc in documents):
                    f.write("\n注意: 群馬県の電子入札システムのドキュメントは、\n")
                    f.write("別途群馬県のシステムにログインして取得する必要があります。\n")
            
            # Download each document
            for doc in documents:
                # Try direct download first
                filepath = self._download_document(doc, case_dir)
                
                # If direct download failed, try browser download
                if not filepath and not any(domain in doc['url'] for domain in ['tokyo.lg.jp', 'e-gunma.lg.jp', 'e-kanagawa.jp']):
                    filepath = await self._download_document_with_browser(page, doc, case_dir)
                
                if filepath:
                    result['files'].append({
                        'name': doc['name'],
                        'path': str(filepath),
                        'type': doc['type'],
                        'url': doc['url']
                    })
            
            result['documents_downloaded'] = len(result['files'])
            logger.info(f"Downloaded {result['documents_downloaded']}/{len(documents)} documents for case ID {case_id}")
            
        except Exception as e:
            logger.error(f"Error processing case ID {case_id}: {e}")
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    async def _extract_all_documents(self, page: Page, case_id: str) -> List[Dict]:
        """Extract all documents from the case page"""
        documents = []
        
        try:
            # Scroll to load all content
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            
            # Try to extract from __NUXT__ data first
            try:
                nuxt_data = await page.evaluate("() => window.__NUXT__ ? JSON.stringify(window.__NUXT__) : null")
                
                if nuxt_data:
                    data = json.loads(nuxt_data)
                    
                    if 'data' in data and isinstance(data['data'], dict):
                        for key, value in data['data'].items():
                            if 'bidFiles' in value and isinstance(value['bidFiles'], list):
                                logger.info(f"Found bidFiles in {key}")
                                
                                for file_info in value['bidFiles']:
                                    if not isinstance(file_info, dict):
                                        continue
                                    
                                    filename = file_info.get('fileName')
                                    download_url = file_info.get('fileDownloadUrl')
                                    mimetype = file_info.get('fileMimeType', '')
                                    
                                    if not filename or not download_url:
                                        continue
                                    
                                    # Determine document type
                                    doc_type = 'unknown'
                                    if 'pdf' in mimetype:
                                        doc_type = 'pdf'
                                    elif 'html' in mimetype:
                                        doc_type = 'html'
                                    elif 'doc' in mimetype:
                                        doc_type = 'doc'
                                    elif 'xls' in mimetype:
                                        doc_type = 'xls'
                                    elif 'zip' in mimetype:
                                        doc_type = 'zip'
                                    
                                    # Clean URL
                                    clean_url = download_url.replace('?no_download=true', '')
                                    
                                    doc_info = {
                                        'url': clean_url,
                                        'type': doc_type,
                                        'name': filename,
                                        'index': len(documents),
                                        'case_id': case_id
                                    }
                                    
                                    if not any(d['url'] == clean_url for d in documents):
                                        documents.append(doc_info)
                                        logger.info(f"Found from NUXT data: {filename} ({doc_type})")
                                break
            except Exception as e:
                logger.debug(f"Error extracting from NUXT data: {e}")
            
            # If no documents from NUXT, use other strategies
            if not documents:
                # Look for all visible links
                all_links = await page.locator('a:visible').all()
                logger.info(f"Found {len(all_links)} visible links on page")
                
                for link in all_links:
                    try:
                        href = await link.get_attribute('href')
                        text = await link.text_content()
                        
                        if not href:
                            continue
                        
                        text = text.strip() if text else ''
                        
                        # Check if this looks like a document
                        if self._is_document_link(href, text):
                            doc = await self._process_document_link(href, text, len(documents), case_id)
                            # Avoid duplicates
                            if not any(d['url'] == doc['url'] for d in documents):
                                documents.append(doc)
                                logger.info(f"Found: {doc['name'][:50]}... ({doc['type']})")
                    
                    except Exception as e:
                        logger.debug(f"Error processing link: {e}")
                        continue
            
            # Log results
            if documents:
                logger.info(f"Found {len(documents)} documents:")
                for doc in documents:
                    logger.info(f"  - {doc['name']} ({doc['type']})")
            else:
                logger.warning("No documents found, taking screenshot for debugging")
                await page.screenshot(path=f"no_docs_found_{case_id}.png")
            
            return documents
            
        except Exception as e:
            logger.error(f"Error extracting documents: {e}")
            return documents
    
    def _is_document_link(self, href: str, text: str = '') -> bool:
        """Check if link is a document (from original)"""
        if not href:
            return False
        
        # Check for file extensions
        doc_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.html']
        if any(ext in href.lower() for ext in doc_extensions):
            return True
        
        # Check for redirect patterns
        if '/redirectExternalLink?to=' in href:
            return True
        
        # Check for download patterns
        if any(pattern in href.lower() for pattern in ['download', 'file', 'document']):
            return True
        
        # Check text content
        if text:
            doc_keywords = ['仕様書', '入札説明', '様式', '図面', '質問', '回答', '資料',
                          '案内', '公告', '公示', 'ダウンロード', '.pdf', '.doc', '.xls',
                          '審査申込書', '電子契約', '注意事項', '総合評価']
            if any(keyword in text for keyword in doc_keywords):
                return True
        
        return False
    
    async def _process_document_link(self, href: str, text: str, index: int, case_id: str) -> Dict:
        """Process document link (from original)"""
        # Handle external redirects
        if '/redirectExternalLink?to=' in href:
            match = re.search(r'to=([^&]+)', href)
            if match:
                encoded_url = match.group(1)
                href = unquote(unquote(encoded_url))
        
        # Make absolute URL if needed
        if href.startswith('/'):
            href = urljoin(self.base_url, href)
        
        # Determine document type
        doc_type = 'html'
        if '.pdf' in href.lower() or (text and '.pdf' in text.lower()):
            doc_type = 'pdf'
        elif any(ext in href.lower() for ext in ['.doc', '.docx']):
            doc_type = 'doc'
        elif any(ext in href.lower() for ext in ['.xls', '.xlsx']):
            doc_type = 'xls'
        elif '.zip' in href.lower():
            doc_type = 'zip'
        
        # Use the actual link text as document name
        doc_name = text.strip() if text else os.path.basename(href.split('?')[0])
        if not doc_name:
            doc_name = f"Document_{index+1}"
        
        return {
            'url': href,
            'type': doc_type,
            'name': doc_name,
            'index': index,
            'case_id': case_id
        }
    
    def _download_document(self, doc_info: Dict, output_dir: Path) -> Optional[str]:
        """Download document using requests (from original)"""
        try:
            url = doc_info['url']
            doc_name = doc_info.get('name', 'Document')
            doc_type = doc_info.get('type', 'unknown')
            index = doc_info.get('index', 0)
            
            logger.info(f"Downloading: {doc_name} from {url[:80]}...")
            
            # Create filename
            safe_name = re.sub(r'[^\w\s\-\.]', '_', doc_name).strip()
            
            # Remove extension if already in name
            base_name = safe_name
            for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.html']:
                if base_name.lower().endswith(ext):
                    base_name = base_name[:-len(ext)]
                    break
            
            # Create filename with index
            filename = f"{index:02d}_{base_name}"
            
            # Add extension
            if doc_type == 'pdf':
                filename += '.pdf'
            elif doc_type == 'doc':
                filename += '.doc'
            elif doc_type == 'xls':
                filename += '.xls'
            elif doc_type == 'zip':
                filename += '.zip'
            else:
                filename += '.html'
            
            if len(filename) > 200:
                filename = filename[:196] + '.' + filename.split('.')[-1]
            
            filepath = output_dir / filename
            
            # Skip if external system URL
            if any(domain in url for domain in ['tokyo.lg.jp', 'e-gunma.lg.jp', 'e-kanagawa.jp']):
                logger.info(f"Skipping external system URL: {url}")
                # Save URL info instead
                url_file = filepath.with_suffix('.url')
                with open(url_file, 'w', encoding='utf-8') as f:
                    f.write(f"[InternetShortcut]\n")
                    f.write(f"URL={url}\n")
                    f.write(f"# {doc_name}\n")
                return str(url_file)
            
            # Download for NJSS internal documents
            headers = {
                'User-Agent': PLAYWRIGHT_UA,
                'Accept': '*/*',
                'Accept-Language': 'ja,en;q=0.9',
                'Referer': self.base_url
            }
            
            response = self.session.get(url, headers=headers, stream=True, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'html' in content_type and doc_type != 'html':
                # This might be a login page or error page
                logger.warning(f"Expected {doc_type} but got HTML response")
                # Save as HTML for inspection
                filepath = filepath.with_suffix('.html')
            
            # Save file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Saved: {filepath.name}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Download error for {doc_name}: {e}")
            return None
    
    async def _download_document_with_browser(self, page: Page, doc_info: Dict, output_dir: Path) -> Optional[str]:
        """Download document using browser (from original)"""
        try:
            url = doc_info['url']
            doc_name = doc_info.get('name', 'Document')
            doc_type = doc_info.get('type', 'unknown')
            index = doc_info.get('index', 0)
            
            logger.info(f"Downloading with browser: {doc_name} from {url[:80]}...")
            
            # Create filename (same logic as above)
            safe_name = re.sub(r'[^\w\s\-\.]', '_', doc_name).strip()
            base_name = safe_name
            for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.html']:
                if base_name.lower().endswith(ext):
                    base_name = base_name[:-len(ext)]
                    break
            
            filename = f"{index:02d}_{base_name}"
            
            if doc_type == 'pdf':
                filename += '.pdf'
            elif doc_type == 'doc':
                filename += '.doc'
            elif doc_type == 'xls':
                filename += '.xls'
            elif doc_type == 'zip':
                filename += '.zip'
            else:
                filename += '.html'
            
            if len(filename) > 200:
                filename = filename[:196] + '.' + filename.split('.')[-1]
            
            filepath = output_dir / filename
            
            # Set up download handling
            async with page.expect_download() as download_info:
                await page.click(f'text="{doc_name}"')
                download = await download_info.value
            
            # Save the downloaded file
            await download.save_as(filepath)
            logger.info(f"Saved: {filepath.name}")
            return str(filepath)
            
        except Exception as e:
            logger.debug(f"Browser download failed, trying direct download: {e}")
            return None