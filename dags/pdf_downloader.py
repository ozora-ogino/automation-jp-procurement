"""NJSS PDF Downloader V3 - Downloads multiple documents per anken into organized directories."""

import os
import csv
import logging
import asyncio
import requests
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import unquote, urljoin

from playwright.async_api import async_playwright, Page
from njss_auth_config import NJSSAuthConfig
from consts import CSV_FILE_PATH, DATA_DIR, DOC_DIR, PLAYWRIGHT_UA

logger = logging.getLogger(__name__)


class NJSSMultiDocumentDownloader:
    """Downloads multiple documents per anken into organized directories."""

    def __init__(self):
        self.username, self.password = NJSSAuthConfig.get_credentials()
        self.download_base_dir = str(DOC_DIR)
        Path(self.download_base_dir).mkdir(parents=True, exist_ok=True)
        self.base_url = "https://www2.njss.info"
        self.session = requests.Session()

    async def login(self, page: Page) -> bool:
        """Login to NJSS."""
        try:
            current_url = page.url
            if '/users/login' not in current_url:
                logger.info("Already logged in")
                return True

            logger.info("Attempting login...")
            await page.wait_for_timeout(2000)

            # Fill login form with multiple selectors
            username_filled = False
            for selector in ['#email', 'input[type="email"]', 'input[name="email"]']:
                try:
                    if await page.locator(selector).count() > 0:
                        await page.fill(selector, self.username)
                        username_filled = True
                        break
                except:
                    continue

            if not username_filled:
                logger.error("Could not find username field")
                return False

            password_filled = False
            for selector in ['#password', 'input[type="password"]', 'input[name="password"]']:
                try:
                    if await page.locator(selector).count() > 0:
                        await page.fill(selector, self.password)
                        password_filled = True
                        break
                except:
                    continue

            if not password_filled:
                logger.error("Could not find password field")
                return False

            # Submit form
            await page.click('button[type="submit"]')

            # Wait for navigation
            await page.wait_for_timeout(5000)

            # Check if login successful
            if '/users/login' not in page.url:
                logger.info("Login successful!")
                return True
            else:
                logger.error("Login failed")
                return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    async def extract_all_documents(self, page: Page, anken_id: str) -> List[Dict]:
        """Extract all document links from the anken page."""
        documents = []

        try:
            # First scroll to make sure all content is loaded
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            # Look for document sections with icons (PDF/HTML icons in grid layout)
            # Based on screenshots, documents appear with icon classes
            icon_selectors = [
                'img[src*="pdf"]',
                'img[src*="PDF"]',
                'img[src*="doc"]',
                'img[src*="xls"]',
                'img[src*="html"]',
                'svg.pdf-icon',
                'svg.doc-icon',
                '[class*="pdf-icon"]',
                '[class*="doc-icon"]',
                '[class*="file-icon"]'
            ]

            # Try multiple strategies to find documents

            # Strategy 1: Look for elements with file icons
            for selector in icon_selectors:
                elements = await page.locator(selector).all()
                for element in elements:
                    try:
                        # Try to find the parent link
                        parent = await element.locator('xpath=ancestor::a[1]').first
                        if await parent.count() > 0:
                            href = await parent.get_attribute('href')
                            text = await parent.text_content()
                            if href:
                                documents.append(await self._process_document_link(href, text, len(documents), anken_id))
                    except:
                        pass

            # Strategy 2: Look for grid layout containers
            grid_selectors = [
                'div[class*="grid"]',
                'div[class*="document"]',
                'div[class*="file-list"]',
                'ul[class*="document"]',
                'div[class*="attachment"]'
            ]

            for selector in grid_selectors:
                containers = await page.locator(selector).all()
                for container in containers:
                    links = await container.locator('a').all()
                    for link in links:
                        try:
                            href = await link.get_attribute('href')
                            text = await link.text_content()
                            if href and self._is_document_link(href, text):
                                doc = await self._process_document_link(href, text, len(documents), anken_id)
                                if not any(d['url'] == doc['url'] for d in documents):
                                    documents.append(doc)
                        except:
                            continue

            # Strategy 3: Find all visible links and check for document patterns
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
                        doc = await self._process_document_link(href, text, len(documents), anken_id)
                        # Avoid duplicates
                        if not any(d['url'] == doc['url'] for d in documents):
                            documents.append(doc)
                            logger.info(f"Found: {doc['name'][:50]}... ({doc['type']})")

                except Exception as e:
                    logger.debug(f"Error processing link: {e}")
                    continue

            # Strategy 4: Look for text patterns that might be documents
            doc_texts = [
                '審査申込書', '電子契約のご案内', '入札説明書', '総合評価方式',
                '注意事項', '仕様書', '様式', '図面', '質問', '回答', '資料',
                '案内', '公告', '公示', '.pdf', '.doc', '.xls', '.html'
            ]

            for doc_text in doc_texts:
                elements = await page.locator(f'text="{doc_text}"').all()
                for element in elements:
                    try:
                        # Check if this element or its parent is a link
                        if await element.locator('xpath=self::a').count() > 0:
                            href = await element.get_attribute('href')
                            text = await element.text_content()
                        else:
                            parent = await element.locator('xpath=ancestor::a[1]').first
                            if await parent.count() > 0:
                                href = await parent.get_attribute('href')
                                text = await parent.text_content()
                            else:
                                continue

                        if href:
                            doc = await self._process_document_link(href, text, len(documents), anken_id)
                            if not any(d['url'] == doc['url'] for d in documents):
                                documents.append(doc)
                    except:
                        continue

            # Strategy 5: Extract from __NUXT__ data
            try:
                nuxt_data = await page.evaluate("() => window.__NUXT__ ? JSON.stringify(window.__NUXT__) : null")

                if nuxt_data:
                    import json
                    data = json.loads(nuxt_data)

                    # Navigate to bidFiles in the data structure
                    # Path: data./offers/view/{id}-url-page-offer-detail-and-organization-data.bidFiles
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

                                    # Determine document type from mimetype
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

                                    # Clean the download URL
                                    clean_url = download_url.replace('?no_download=true', '')

                                    doc_info = {
                                        'url': clean_url,
                                        'type': doc_type,
                                        'name': filename,
                                        'index': len(documents),
                                        'anken_id': anken_id
                                    }

                                    # Avoid duplicates
                                    if not any(d['url'] == clean_url for d in documents):
                                        documents.append(doc_info)
                                        logger.info(f"Found from NUXT data: {filename} ({doc_type})")
                                break
            except Exception as e:
                logger.debug(f"Error extracting from NUXT data: {e}")

            # Log what we found
            if documents:
                logger.info(f"Found {len(documents)} documents:")
                for doc in documents:
                    logger.info(f"  - {doc['name']} ({doc['type']})")
            else:
                logger.warning("No documents found, taking screenshot for debugging")
                await page.screenshot(path=f"no_docs_found_{anken_id}.png")

            return documents

        except Exception as e:
            logger.error(f"Error extracting documents: {e}")
            return documents

    def _is_document_link(self, href: str, text: str = '') -> bool:
        """Check if a link appears to be a document."""
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

    async def _process_document_link(self, href: str, text: str, index: int, anken_id: str) -> Dict:
        """Process a document link and return document info."""
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
            'anken_id': anken_id
        }

    async def download_document_with_browser(self, page: Page, doc_info: Dict, output_dir: Path) -> Optional[str]:
        """Download a document using browser automation."""
        try:
            url = doc_info['url']
            doc_name = doc_info.get('name', 'Document')
            doc_type = doc_info.get('type', 'unknown')
            index = doc_info.get('index', 0)

            logger.info(f"Downloading with browser: {doc_name} from {url[:80]}...")

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

    def download_document(self, doc_info: Dict, output_dir: Path) -> Optional[str]:
        """Download a single document using requests."""
        try:
            url = doc_info['url']
            doc_name = doc_info.get('name', 'Document')
            doc_type = doc_info.get('type', 'unknown')
            index = doc_info.get('index', 0)

            logger.info(f"Downloading: {doc_name} from {url[:80]}...")

            # Create filename
            # Clean document name for filesystem
            safe_name = re.sub(r'[^\w\s\-\.]', '_', doc_name).strip()

            # Remove extension if it's already in the name
            base_name = safe_name
            for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.html']:
                if base_name.lower().endswith(ext):
                    base_name = base_name[:-len(ext)]
                    break

            # Create filename with index for sorting
            filename = f"{index:02d}_{base_name}"

            # Add appropriate extension
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

            # Limit filename length
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
                'User-Agent': PLAYWRIGHT_UA,  # Use fixed UA from consts.py
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

    async def process_anken_page(self, page: Page, anken_url: str, anken_id: str) -> Dict:
        """Process single anken page and download all documents."""
        result = {
            'anken_id': anken_id,
            'documents': [],
            'downloaded': [],
            'directory': None
        }

        try:
            # Create directory for this anken
            anken_dir = Path(self.download_base_dir) / str(anken_id)
            anken_dir.mkdir(exist_ok=True)
            result['directory'] = str(anken_dir)

            # Navigate to anken page
            logger.info(f"Processing 案件ID {anken_id}")
            await page.goto(anken_url, wait_until='domcontentloaded')

            # Check if login required
            if '/users/login' in page.url:
                logger.info("Login required")
                if not await self.login(page):
                    return result
                # Navigate back
                await page.goto(anken_url, wait_until='domcontentloaded')

            # Wait for content
            await page.wait_for_timeout(3000)

            # Extract all documents
            documents = await self.extract_all_documents(page, anken_id)
            result['documents'] = documents

            if not documents:
                logger.warning(f"No documents found for 案件ID {anken_id}")
                return result

            # Save document info
            info_path = anken_dir / 'documents_info.json'
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(documents, f, ensure_ascii=False, indent=2)

            # Also save a README with instructions for accessing external documents
            readme_path = anken_dir / 'README.txt'
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(f"案件ID: {anken_id}\n")
                f.write(f"案件URL: {anken_url}\n")
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
                filepath = self.download_document(doc, anken_dir)

                # If direct download failed, try browser download
                if not filepath and not any(domain in doc['url'] for domain in ['tokyo.lg.jp', 'e-gunma.lg.jp', 'e-kanagawa.jp']):
                    filepath = await self.download_document_with_browser(page, doc, anken_dir)

                if filepath:
                    result['downloaded'].append(filepath)

            logger.info(f"Downloaded {len(result['downloaded'])}/{len(documents)} documents for 案件ID {anken_id}")

        except Exception as e:
            logger.error(f"Error processing 案件ID {anken_id}: {e}")

        return result

    async def process_search_results(self, csv_path: str) -> Dict[str, Dict]:
        """Process all anken from search results CSV."""
        all_results = {}

        # Read CSV
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        logger.info(f"Found {len(rows)} rows in CSV")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', f'--user-agent={PLAYWRIGHT_UA}']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=PLAYWRIGHT_UA,  # Use fixed UA from consts.py
                locale='ja-JP',
                timezone_id='Asia/Tokyo'
            )

            page = await context.new_page()

            # Login once
            logger.info("Initial login")
            await page.goto(f"{self.base_url}/users/login")
            if not await self.login(page):
                logger.error("Initial login failed")
                await browser.close()
                return all_results

            # Process each anken
            for i, row in enumerate(rows):
                anken_id = row.get('案件ID', '')
                anken_url = row.get('案件概要URL', '')

                if not anken_url or not anken_id:
                    continue

                logger.info(f"\nProcessing {i+1}/{len(rows)}: 案件ID {anken_id}")

                result = await self.process_anken_page(page, anken_url, anken_id)
                all_results[anken_id] = result

                # Delay between requests
                if i < len(rows) - 1:
                    await asyncio.sleep(2)

            await browser.close()

        return all_results

    def update_csv_with_results(self, csv_path: str, results: Dict[str, Dict]) -> str:
        """Update CSV with document download information."""
        # Read CSV
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames)
            rows = list(reader)

        # Add new columns
        new_columns = ['文書ディレクトリ', '文書数', 'ダウンロード済み数', '文書情報']
        for col in new_columns:
            if col not in fieldnames:
                fieldnames.append(col)

        # Update rows
        for row in rows:
            anken_id = row.get('案件ID', '')
            if anken_id in results:
                result = results[anken_id]
                row['文書ディレクトリ'] = result.get('directory', '')
                row['文書数'] = len(result.get('documents', []))
                row['ダウンロード済み数'] = len(result.get('downloaded', []))
                # Add JSON string of document info
                row['文書情報'] = json.dumps(result.get('documents', []), ensure_ascii=False)
            else:
                row['文書ディレクトリ'] = ''
                row['文書数'] = 0
                row['ダウンロード済み数'] = 0
                row['文書情報'] = '[]'

        # Write updated CSV (overwrite the original file)
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"Updated CSV: {csv_path}")
        return csv_path


async def download_multi_documents(csv_path: str = None):
    """Main function to download multiple documents per anken."""
    if csv_path is None:
        csv_path = str(CSV_FILE_PATH)

    if not os.path.exists(csv_path):
        logger.error(f"CSV not found: {csv_path}")
        return None

    downloader = NJSSMultiDocumentDownloader()

    # Process and download
    results = await downloader.process_search_results(csv_path)

    # Summary
    total_anken = len(results)
    total_docs = sum(len(r.get('documents', [])) for r in results.values())
    total_downloaded = sum(len(r.get('downloaded', [])) for r in results.values())

    logger.info(f"\nSummary:")
    logger.info(f"- Processed {total_anken} anken")
    logger.info(f"- Found {total_docs} documents")
    logger.info(f"- Downloaded {total_downloaded} documents")

    # Update CSV
    if results:
        output_csv = downloader.update_csv_with_results(csv_path, results)
        return output_csv

    return None


def download_njss_multi_docs(**context):
    """Airflow task."""
    logger.info("Starting NJSS multi-document download...")

    csv_path = context.get('csv_path')
    result = asyncio.run(download_multi_documents(csv_path))

    if result:
        logger.info(f"Download completed: {result}")
        return result
    else:
        raise Exception("Multi-document download failed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(download_multi_documents())
