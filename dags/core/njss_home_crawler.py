#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NJSS Home Crawler Service - Downloads CSV from NJSS home page.
This is a refactored version that maintains the exact same functionality as the original.
"""

import os
import asyncio
import logging
import zipfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from playwright.async_api import async_playwright, Page, BrowserContext, Download
import pandas as pd

from core.authentication import NJSSAuthenticationService
from utils.file_service import FileService
from constants import CSV_FILE_PATH, DATA_DIR, PLAYWRIGHT_UA

logger = logging.getLogger(__name__)


class NJSSHomeCrawlerService:
    """Service for downloading CSV from NJSS home page after login."""

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
        self.login_url = "https://www2.njss.info/users/login"
        self.download_dir = Path(DATA_DIR) / "downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def download_from_home(self) -> List[str]:
        """
        Download CSV files from NJSS home page after login.
        This follows the exact same logic as the original NJSSHomeCrawler.
        """
        downloaded_files = []

        # Clean up old downloads from today to avoid conflicts
        today = datetime.now().strftime('%Y%m%d')
        for file in self.download_dir.glob(f"njss_home_*_{today}_*"):
            try:
                if file.is_file():
                    file.unlink()
                elif file.is_dir():
                    shutil.rmtree(file)
                logger.info(f"Cleaned up old file/directory: {file}")
            except Exception as e:
                logger.warning(f"Could not clean up {file}: {e}")

        async with async_playwright() as p:
            # Use same browser configuration as original
            browser_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                f'--user-agent={PLAYWRIGHT_UA}'
            ]

            # Check for system Chrome/Chromium
            executable_path = None
            for path in ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome']:
                if os.path.exists(path):
                    executable_path = path
                    logger.info(f"Using system browser: {path}")
                    break

            browser = await p.chromium.launch(
                headless=self.headless,
                executable_path=executable_path,
                args=browser_args
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=PLAYWRIGHT_UA,
                accept_downloads=True
            )

            page = await context.new_page()

            try:
                # Login
                login_success = await self.auth_service.login(page, self.login_url)
                if not login_success:
                    raise Exception("Authentication failed")

                # Wait for initial page to load
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)

                # Check current URL after login
                current_url = page.url
                logger.info(f"Current URL after login: {current_url}")

                # If login was successful, we should already be on /users/home
                if '/users/home' in current_url:
                    logger.info("Already on /users/home page after login")
                elif '/users/' in current_url and '/users/login' not in current_url:
                    logger.info(f"In users area: {current_url}")
                    # Navigate to home if not already there
                    if '/users/home' not in current_url:
                        logger.info("Navigating to /users/home...")
                        await page.goto('https://www2.njss.info/users/home', wait_until='networkidle')
                        await page.wait_for_timeout(2000)
                else:
                    logger.error(f"Not in users area after login. Current URL: {current_url}")
                    raise Exception("Login did not redirect to users area as expected")

                # Log current URL to understand where we are
                current_url = page.url
                logger.info(f"Current URL after navigation: {current_url}")

                # Take screenshot for debugging
                if not self.headless:
                    screenshot_path = await self.file_service.take_screenshot(
                        page, "users_home", f"users_home_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    )
                    logger.info(f"Screenshot saved: {screenshot_path}")

                logger.info("Looking for download buttons on users/home page...")

                # Try multiple selectors for download buttons
                download_selectors = [
                    'button:has-text("ダウンロード")',
                    'a:has-text("ダウンロード")',
                    'button:has-text("Download")',
                    'a:has-text("Download")',
                    'button:has-text("CSV")',
                    'a:has-text("CSV")',
                    'button:has-text("CSVダウンロード")',
                    'a:has-text("CSVダウンロード")',
                    '.download-button',
                    'button[class*="download"]',
                    'a[class*="download"]',
                    'button[onclick*="download"]',
                    'a[href*="download"]',
                    'a[href*=".csv"]',
                    'button[title*="ダウンロード"]',
                    'a[title*="ダウンロード"]'
                ]

                download_buttons = []
                for selector in download_selectors:
                    buttons = await page.query_selector_all(selector)
                    if buttons:
                        logger.info(f"Found {len(buttons)} buttons with selector: {selector}")
                        download_buttons.extend(buttons)

                # Remove duplicates
                unique_buttons = []
                for btn in download_buttons:
                    if btn not in unique_buttons:
                        unique_buttons.append(btn)
                download_buttons = unique_buttons

                logger.info(f"Found total {len(download_buttons)} download buttons")

                # If no download buttons found, explore the page structure
                if len(download_buttons) == 0:
                    logger.info("No download buttons found. Exploring page structure...")

                    # Look for tables with saved search conditions
                    tables = await page.query_selector_all('table')
                    logger.info(f"Found {len(tables)} tables on page")

                    # Look for "入札案件の検索条件結果" section
                    search_condition_texts = [
                        '入札案件の検索条件結果',
                        '検索条件結果',
                        '検索条件',
                        '保存した検索条件',
                        'お気に入り検索条件'
                    ]

                    for i, table in enumerate(tables):
                        try:
                            table_text = await table.text_content()
                            logger.info(f"Table {i} preview: {table_text[:200]}...")

                            # Look for download links in table rows
                            rows = await table.query_selector_all('tr')
                            for row in rows:
                                row_text = await row.text_content()
                                if any(text in row_text for text in search_condition_texts):
                                    logger.info(f"Found search condition row: {row_text[:100]}")

                                    # Look for download button/link in this row
                                    download_link = await row.query_selector('a:has-text("ダウンロード"), button:has-text("ダウンロード"), a[href*="download"]')
                                    if download_link:
                                        logger.info("Found download link in table row")
                                        download_buttons.append(download_link)
                        except:
                            continue

                # Process download buttons
                for i, btn in enumerate(download_buttons):
                    try:
                        if not await btn.is_visible():
                            continue

                        # Set up download handler
                        download_path = None

                        async def handle_download(download: Download):
                            nonlocal download_path
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            filename = f"njss_home_{i+1}_{timestamp}_{download.suggested_filename or 'download.zip'}"
                            download_path = self.download_dir / filename

                            # Remove existing file if it exists
                            if download_path.exists():
                                download_path.unlink()
                                logger.info(f"Removed existing file: {download_path}")

                            await download.save_as(str(download_path))
                            logger.info(f"Downloaded: {download_path}")

                        page.on('download', handle_download)

                        # Click download button
                        await btn.click()
                        logger.info(f"Clicked download button {i+1}")

                        # Wait for modal
                        await page.wait_for_timeout(2000)

                        # Handle modal if it appears
                        modal = await page.query_selector('div[role="dialog"]')
                        if modal:
                            logger.info("Modal appeared, looking for download button")
                            modal_download = await modal.query_selector('button:has-text("ダウンロード")')
                            if modal_download:
                                await modal_download.click()
                                logger.info("Clicked modal download button")

                        # Wait for download
                        await page.wait_for_timeout(5000)

                        if download_path and download_path.exists():
                            downloaded_files.append(str(download_path))

                        page.remove_listener('download', handle_download)

                    except Exception as e:
                        logger.error(f"Error with download button {i+1}: {str(e)}")
                        continue

                # If no files downloaded, save debugging info
                if not downloaded_files:
                    html_path = self.download_dir / f"njss_home_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                    page_html = await page.content()
                    self.file_service.write_text(page_html, html_path)
                    logger.error(f"No files downloaded from NJSS. Page HTML saved for debugging: {html_path}")

                    # Take a screenshot for debugging
                    if not self.headless:
                        screenshot_path = await self.file_service.take_screenshot(
                            page, "no_download", f"no_download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        )
                        logger.error(f"Screenshot saved: {screenshot_path}")

                    # Log page text
                    page_text = await page.evaluate('() => document.body.innerText')
                    logger.info(f"Page text (first 1000 chars): {page_text[:1000]}")

                    raise Exception("Failed to download CSV from NJSS. No download buttons found or download failed.")

                return downloaded_files

            finally:
                await browser.close()

    def process_downloaded_files(self, downloaded_files: List[str]) -> str:
        """
        Process downloaded files and merge them into a single CSV.
        This follows the exact same logic as the original main() function.
        """
        if not downloaded_files:
            logger.warning("No files were downloaded from NJSS")
            raise Exception("No files downloaded")

        logger.info(f"Downloaded {len(downloaded_files)} files")

        # Process downloaded files
        all_csv_files = []

        for file_path in downloaded_files:
            logger.info(f"Processing: {file_path}")

            if file_path.endswith('.zip'):
                # Extract ZIP file
                extract_dir = file_path.replace('.zip', '_extracted')

                # Remove existing extract directory if it exists
                if os.path.exists(extract_dir):
                    import shutil
                    shutil.rmtree(extract_dir)
                    logger.info(f"Removed existing extract directory: {extract_dir}")

                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)

                    # Find CSV files in the ZIP
                    for fname in zip_ref.namelist():
                        if fname.endswith('.csv'):
                            csv_path = os.path.join(extract_dir, fname)
                            all_csv_files.append(csv_path)

            elif file_path.endswith('.csv'):
                all_csv_files.append(file_path)

        if not all_csv_files:
            logger.warning("No CSV files found in downloads")
            raise Exception("No CSV files found")

        # Prepare final output path
        final_csv_path = CSV_FILE_PATH

        # Ensure output directory exists
        os.makedirs(os.path.dirname(final_csv_path), exist_ok=True)

        # If we have CSV files, use them
        if len(all_csv_files) == 1:
            # Single CSV file, just copy it
            shutil.copy2(all_csv_files[0], final_csv_path)
            logger.info(f"Copied single CSV to {final_csv_path}")
        else:
            # Multiple CSV files - merge them
            dfs = []
            for csv_file in all_csv_files:
                try:
                    # Try different encodings
                    for encoding in ['shift_jis', 'utf-8', 'cp932']:
                        try:
                            df = pd.read_csv(csv_file, encoding=encoding)
                            dfs.append(df)
                            logger.info(f"Read CSV {csv_file} with {len(df)} rows")
                            break
                        except:
                            continue
                except Exception as e:
                    logger.error(f"Failed to read {csv_file}: {e}")

            if dfs:
                # Concatenate all dataframes
                merged_df = pd.concat(dfs, ignore_index=True)

                # Save to final CSV
                merged_df.to_csv(final_csv_path, index=False, encoding='utf-8')
                logger.info(f"Merged {len(dfs)} CSV files into {final_csv_path} with {len(merged_df)} total rows")
            else:
                # If no dataframes could be read, just copy the first file
                shutil.copy2(all_csv_files[0], final_csv_path)
                logger.info(f"Copied first CSV to {final_csv_path}")

        # Clean up temporary files
        for file_path in downloaded_files:
            try:
                if file_path.endswith('.zip'):
                    os.remove(file_path)
                    extract_dir = file_path.replace('.zip', '_extracted')
                    if os.path.exists(extract_dir):
                        shutil.rmtree(extract_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up {file_path}: {e}")

        logger.info(f"Successfully saved CSV to {final_csv_path}")
        return str(final_csv_path)
