"""NJSS PDF Downloader - Downloads PDFs from 案件公示書 links after crawling."""

import os
import csv
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from playwright.async_api import async_playwright, Page
from njss_auth_config import NJSSAuthConfig
from consts import CSV_FILE_PATH, DATA_DIR

logger = logging.getLogger(__name__)


class NJSSPDFDownloader:
    """Downloads PDFs from NJSS 案件 pages."""
    
    def __init__(self):
        self.username, self.password = NJSSAuthConfig.get_credentials()
        self.download_dir = os.path.join(NJSSAuthConfig.get_download_dir(), 'pdfs')
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
        self.logged_in = False
        
    async def login(self, page: Page) -> bool:
        """Login to NJSS if needed."""
        try:
            # Check if already logged in
            current_url = page.url
            if '/users/login' not in current_url:
                logger.info("Already logged in")
                return True
                
            logger.info("Attempting login...")
            
            # Wait for page to be ready
            await page.wait_for_timeout(2000)
            
            # Try multiple selectors for username field
            username_selectors = [
                '#email',
                'input[type="email"]',
                'input[name="email"]',
                'input[name="username"]'
            ]
            
            username_filled = False
            for selector in username_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        await page.fill(selector, self.username)
                        username_filled = True
                        logger.info(f"Filled username using selector: {selector}")
                        break
                except:
                    continue
            
            if not username_filled:
                logger.error("Could not find username field")
                return False
            
            # Try multiple selectors for password field
            password_selectors = [
                '#password',
                'input[type="password"]',
                'input[name="password"]'
            ]
            
            password_filled = False
            for selector in password_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        await page.fill(selector, self.password)
                        password_filled = True
                        logger.info(f"Filled password using selector: {selector}")
                        break
                except:
                    continue
            
            if not password_filled:
                logger.error("Could not find password field")
                return False
            
            # Try multiple ways to submit
            submit_methods = [
                lambda: page.click('button[type="submit"]'),
                lambda: page.click('input[type="submit"]'),
                lambda: page.click('button:has-text("ログイン")'),
                lambda: page.press('input[type="password"]', 'Enter'),
                lambda: page.evaluate('document.querySelector("form").submit()')
            ]
            
            submitted = False
            for method in submit_methods:
                try:
                    await method()
                    submitted = True
                    logger.info("Form submitted")
                    break
                except:
                    continue
            
            if not submitted:
                logger.error("Could not submit login form")
                return False
            
            # Wait for navigation
            await page.wait_for_timeout(5000)
            
            # Check if login successful
            if '/users/login' not in page.url:
                logger.info("Login successful!")
                self.logged_in = True
                return True
            else:
                # Check for logout button as alternative confirmation
                if await page.locator('*:has-text("ログアウト")').count() > 0:
                    logger.info("Login successful (found logout button)!")
                    self.logged_in = True
                    return True
                logger.error("Login failed - still on login page")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    async def download_pdf_from_page(self, page: Page, anken_url: str, anken_id: str) -> Optional[str]:
        """Visit anken page and download PDF from 案件公示書 link."""
        try:
            # Always login first before visiting anken page
            if not self.logged_in:
                logger.info("Logging in before visiting anken page...")
                await page.goto('https://www2.njss.info/users/login', wait_until='domcontentloaded')
                if not await self.login(page):
                    logger.error("Failed to login")
                    return None
            
            logger.info(f"Visiting anken page: {anken_url}")
            await page.goto(anken_url, wait_until='domcontentloaded')
            
            # Check if we were logged out and need to login again
            if '/users/login' in page.url:
                logger.info("Session expired, logging in again...")
                if not await self.login(page):
                    logger.error("Failed to login")
                    return None
                # Go back to anken page after login
                await page.goto(anken_url, wait_until='domcontentloaded')
            
            # Wait for page to load
            await page.wait_for_timeout(3000)
            
            # Look for 案件公示書 link or clickable element - try multiple selectors
            pdf_selectors = [
                # Direct clickable elements
                '*:has-text("案件公示書"):visible',  # Any visible element with the text
                'text=案件公示書',  # Direct text match
                # Link selectors
                'a:has-text("案件公示書")',  # Text link
                '*:has-text("案件公示書") a',  # Link within element containing text
                'a[href*=".pdf"]',  # Direct PDF links
                '.pdf-icon + a',  # Link after PDF icon
                'img[alt*="PDF"] + a',  # Link after PDF image
                'a:has(img[alt*="PDF"])',  # Link containing PDF image
                # Based on screenshot, try near the PDF icon
                'text=案件公示書 >> .. >> a',  # Link near the text
                ':text("案件公示書") >> xpath=.. >> a',  # Parent's link
                # Look for the section containing PDF icon
                '.pdf-section *:has-text("案件公示書")',
                '[class*="pdf"] *:has-text("案件公示書")',
            ]
            
            pdf_links = []
            for selector in pdf_selectors:
                try:
                    found_links = await page.locator(selector).all()
                    if found_links:
                        pdf_links = found_links
                        logger.info(f"Found PDF link using selector: {selector}")
                        break
                except:
                    continue
            
            # If still not found, look for the PDF icon section
            if not pdf_links:
                # Look for elements containing 案件公示書 text and find nearby links
                elements_with_text = await page.locator('*:has-text("案件公示書")').all()
                for element in elements_with_text:
                    # Get parent and look for links
                    parent_links = await element.locator('xpath=.. >> a').all()
                    if parent_links:
                        pdf_links = parent_links
                        logger.info("Found PDF link near 案件公示書 text")
                        break
                    
                    # Also check siblings
                    sibling_links = await element.locator('xpath=following-sibling::a').all()
                    if sibling_links:
                        pdf_links = sibling_links
                        logger.info("Found PDF link as sibling of 案件公示書 text")
                        break
            
            if not pdf_links:
                # Final attempt - look for any PDF-related links
                pdf_related = await page.locator('a[href*="pdf"], a[href*="PDF"], a:has-text("ダウンロード")').all()
                if pdf_related:
                    logger.info(f"Found {len(pdf_related)} PDF-related links, using first one")
                    pdf_links = pdf_related[:1]
            
            if not pdf_links:
                logger.warning(f"No 案件公示書 link found for {anken_id}")
                # Debug: take a screenshot
                screenshot_path = f"/tmp/debug_{anken_id}.png"
                await page.screenshot(path=screenshot_path)
                logger.info(f"Debug screenshot saved to: {screenshot_path}")
                return None
            
            # Get the first PDF element (link or clickable element)
            pdf_element = pdf_links[0]
            
            # Try to get href attribute if it's a link
            href = await pdf_element.get_attribute('href')
            
            # Set up download path
            pdf_filename = f"anken_{anken_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = os.path.join(self.download_dir, pdf_filename)
            
            # If it has href and it's a direct PDF link, we can navigate to it
            if href and (href.endswith('.pdf') or 'pdf' in href.lower()):
                if href.startswith('/'):
                    href = f"https://www2.njss.info{href}"
                logger.info(f"Found direct PDF link: {href}")
                
                # Download directly
                try:
                    async with page.expect_download() as download_info:
                        await page.goto(href)
                        download = await download_info.value
                        await download.save_as(pdf_path)
                        logger.info(f"PDF downloaded via direct link: {pdf_path}")
                        return pdf_path
                except:
                    logger.info("Direct download failed, trying click method")
            
            # Otherwise, click the element and expect a download
            logger.info(f"Clicking element to download PDF")
            
            try:
                async with page.expect_download() as download_info:
                    await pdf_element.click()
                    download = await download_info.value
                    
                    # Save the downloaded file
                    await download.save_as(pdf_path)
                    logger.info(f"PDF downloaded via click: {pdf_path}")
                    return pdf_path
            except Exception as e:
                logger.error(f"Failed to download PDF by clicking: {e}")
                
                # As a last resort, try to find any downloadable link after click
                await page.wait_for_timeout(2000)
                download_links = await page.locator('a[href*=".pdf"], a[download]').all()
                if download_links:
                    logger.info(f"Found {len(download_links)} download links after click")
                    async with page.expect_download() as download_info:
                        await download_links[0].click()
                        download = await download_info.value
                        await download.save_as(pdf_path)
                        logger.info(f"PDF downloaded via secondary link: {pdf_path}")
                        return pdf_path
                    
                return None
                
        except Exception as e:
            logger.error(f"Error downloading PDF for {anken_id}: {e}")
            return None
    
    async def process_search_results(self, csv_path: str) -> Dict[str, str]:
        """Process search_result.csv and download PDFs for each anken."""
        pdf_paths = {}
        
        # Read CSV file
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        logger.info(f"Found {len(rows)} rows in CSV")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='ja-JP',
                timezone_id='Asia/Tokyo',
                accept_downloads=True
            )
            
            page = await context.new_page()
            
            # Add stealth scripts
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => false});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            """)
            
            # Login once at the beginning
            logger.info("Performing initial login...")
            await page.goto('https://www2.njss.info/users/login', wait_until='domcontentloaded')
            if not await self.login(page):
                logger.error("Initial login failed")
                await browser.close()
                return pdf_paths
            
            # Process each row
            for i, row in enumerate(rows):
                anken_id = row.get('案件ID', '')
                anken_url = row.get('案件概要URL', '')
                
                if not anken_url or not anken_id:
                    logger.warning(f"Row {i+1} missing 案件ID or URL")
                    continue
                
                logger.info(f"Processing {i+1}/{len(rows)}: 案件ID {anken_id}")
                
                # Download PDF
                pdf_path = await self.download_pdf_from_page(page, anken_url, anken_id)
                if pdf_path:
                    pdf_paths[anken_id] = pdf_path
                
                # Small delay between requests
                if i < len(rows) - 1:
                    await asyncio.sleep(2)
            
            await browser.close()
        
        return pdf_paths
    
    def update_csv_with_pdf_paths(self, csv_path: str, pdf_paths: Dict[str, str]):
        """Update the CSV file with PDF file paths."""
        # Read existing CSV
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        
        # Add new column if not exists
        if 'PDF_ファイルパス' not in fieldnames:
            fieldnames = list(fieldnames) + ['PDF_ファイルパス']
        
        # Update rows with PDF paths
        for row in rows:
            anken_id = row.get('案件ID', '')
            if anken_id in pdf_paths:
                row['PDF_ファイルパス'] = pdf_paths[anken_id]
            else:
                row['PDF_ファイルパス'] = ''
        
        # Write updated CSV
        output_path = csv_path.replace('.csv', '_with_pdfs.csv')
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        logger.info(f"Updated CSV saved to: {output_path}")
        return output_path


async def download_pdfs_from_search_results(csv_path: str = None):
    """Main function to download PDFs from search results."""
    if csv_path is None:
        # Use the path from consts.py
        csv_path = str(CSV_FILE_PATH)
    
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found: {csv_path}")
        return None
    
    downloader = NJSSPDFDownloader()
    
    # Download PDFs
    pdf_paths = await downloader.process_search_results(csv_path)
    logger.info(f"Downloaded {len(pdf_paths)} PDFs")
    
    # Update CSV with PDF paths
    if pdf_paths:
        output_csv = downloader.update_csv_with_pdf_paths(csv_path, pdf_paths)
        return output_csv
    
    return None


def download_njss_pdfs(**context):
    """Airflow task to download PDFs."""
    logger.info("Starting NJSS PDF download...")
    
    # Get CSV path from context or use default
    csv_path = context.get('csv_path', None)
    
    result = asyncio.run(download_pdfs_from_search_results(csv_path))
    
    if result:
        logger.info(f"PDF download completed. Updated CSV: {result}")
        return result
    else:
        raise Exception("PDF download failed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(download_pdfs_from_search_results())