import asyncio
import csv
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from playwright.async_api import async_playwright, Page, BrowserContext, Download
from consts import CSV_FILE_PATH, DATA_DIR, PLAYWRIGHT_UA

try:
    from .njss_auth_config import NJSSAuthConfig, NJSS_SELECTORS
except ImportError:
    try:
        from njss_auth_config import NJSSAuthConfig, NJSS_SELECTORS
    except ImportError:
        # Fallback to local version without Airflow dependencies
        try:
            from njss_auth_config_local import NJSSAuthConfig, NJSS_SELECTORS
        except ImportError:
            # If all else fails, define minimal config inline
            import os

            class NJSSAuthConfig:
                @staticmethod
                def get_credentials():
                    username = os.getenv('NJSS_USERNAME')
                    password = os.getenv('NJSS_PASSWORD')
                    if not username or not password:
                        raise ValueError("NJSS credentials not found")
                    return username, password

                @staticmethod
                def get_download_dir():
                    return os.getenv('NJSS_DOWNLOAD_DIR', os.path.join(os.getcwd(), 'downloads'))

            NJSS_SELECTORS = {
                'login': {
                    'form': 'form',
                    'username': '#email',
                    'password': '#password',
                    'submit': 'button[type="submit"]',
                    'logout': 'a[href*="logout"]'
                },
                'search': {
                    'results': 'table, .results',
                    'csv_download': ['button:has-text("ダウンロード")']
                }
            }

logger = logging.getLogger(__name__)


class NJSSCrawler:
    """Crawler for NJSS (National Japan Supercomputer System) procurement data."""

    def __init__(self, headless: bool = True, timeout: int = 30000, authenticate: bool = False):
        self.headless = headless
        self.timeout = timeout
        self.authenticate = authenticate
        self.base_url = "https://www.njss.info/offers/"
        self.login_url = "https://www2.njss.info/users/login"  # Updated based on inspection

        if authenticate:
            try:
                self.username, self.password = NJSSAuthConfig.get_credentials()
            except ValueError as e:
                logger.warning(f"Authentication requested but credentials not found: {e}")
                self.authenticate = False

    async def _setup_browser(self):
        """Setup browser with required configurations."""
        self.playwright = await async_playwright().start()

        # Use minimal configuration that works in Docker with fixed User-Agent
        browser_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            f'--user-agent={PLAYWRIGHT_UA}'  # Fixed UA to prevent "new device" detection
        ]

        # Check for system Chrome/Chromium
        executable_path = None
        for path in ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome']:
            if os.path.exists(path):
                executable_path = path
                logger.info(f"Using system browser: {path}")
                break

        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            executable_path=executable_path,
            args=browser_args
        )

        # Use context configuration with fixed User-Agent
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=PLAYWRIGHT_UA  # Also set UA in context for consistency
        )

    async def _cleanup(self):
        """Clean up browser resources."""
        if hasattr(self, 'context'):
            await self.context.close()
        if hasattr(self, 'browser'):
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

    async def _login(self, page: Page) -> bool:
        """Login to NJSS if authentication is required."""
        if not self.authenticate:
            return True

        try:
            logger.info("Attempting to login to NJSS")
            await page.goto(self.login_url, wait_until='networkidle', timeout=self.timeout)

            # Debug: Log current URL
            logger.info(f"Current URL after navigation: {page.url}")

            # Wait for login form
            await page.wait_for_selector(NJSS_SELECTORS['login']['form'], timeout=self.timeout)

            # Debug: Take screenshot before login
            if not self.headless:
                screenshot_path = f"/tmp/njss_before_login_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_path)
                logger.info(f"Screenshot saved: {screenshot_path}")

            # Fill credentials properly
            logger.info(f"Filling username field with: {self.username}")

            # Find and fill username field
            username_field = await page.query_selector(NJSS_SELECTORS['login']['username'])
            if not username_field:
                logger.error("Username field not found!")
                raise Exception("Cannot find username field")

            await username_field.click()
            await username_field.fill('')  # Clear any existing value
            await username_field.type(self.username, delay=50)  # Type with delay

            # Find and fill password field
            logger.info("Filling password field...")
            password_field = await page.query_selector(NJSS_SELECTORS['login']['password'])
            if not password_field:
                logger.error("Password field not found!")
                raise Exception("Cannot find password field")

            await password_field.click()
            await password_field.fill('')  # Clear any existing value
            await password_field.type(self.password, delay=50)  # Type with delay

            # Check for CAPTCHA
            captcha = await page.query_selector(NJSS_SELECTORS['login']['captcha'])
            if captcha:
                logger.warning("CAPTCHA detected - manual intervention may be required")
                if not self.headless:
                    logger.info("Please solve the CAPTCHA manually within 30 seconds")
                    await page.wait_for_timeout(30000)

            # Wait a bit to ensure form is ready
            await page.wait_for_timeout(1000)

            # Check if there's any JavaScript validation we need to trigger
            await page.evaluate("""
                // Trigger any change events on the form fields
                const emailField = document.querySelector('#email, input[type="email"], input[name="email"]');
                const passField = document.querySelector('#password, input[type="password"]');
                if (emailField) {
                    emailField.dispatchEvent(new Event('change', { bubbles: true }));
                    emailField.dispatchEvent(new Event('blur', { bubbles: true }));
                }
                if (passField) {
                    passField.dispatchEvent(new Event('change', { bubbles: true }));
                    passField.dispatchEvent(new Event('blur', { bubbles: true }));
                }
            """)

            # Submit login by clicking the button
            logger.info("Looking for login submit button...")

            # Find submit button
            submit_button = await page.query_selector(NJSS_SELECTORS['login']['submit'])
            if not submit_button:
                # Try alternative selectors
                submit_button = await page.query_selector('button[type="submit"], input[type="submit"], button:has-text("ログイン")')

            if not submit_button:
                logger.error("Submit button not found!")
                raise Exception("Cannot find submit button")

            logger.info("Clicking submit button...")
            await submit_button.click()

            # Wait for navigation
            try:
                await page.wait_for_navigation(timeout=15000)
                logger.info("Navigation detected after form submission")
            except:
                logger.info("No navigation detected, waiting for page to settle...")
                await page.wait_for_timeout(5000)

            # Debug: Log URL after login attempt
            current_url = page.url
            logger.info(f"URL after login attempt: {current_url}")

            # Debug: Take screenshot after login
            if not self.headless:
                screenshot_path = f"/tmp/njss_after_login_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_path)
                logger.info(f"Screenshot saved: {screenshot_path}")

            # Debug: Log page title
            title = await page.title()
            logger.info(f"Page title: {title}")

            # Check for error messages
            error_selectors = ['.error', '.alert-danger', '[class*="error"]', '.flash-message', '.alert']
            for selector in error_selectors:
                error_elems = await page.query_selector_all(selector)
                for error_elem in error_elems:
                    error_text = await error_elem.text_content()
                    if error_text and error_text.strip():
                        logger.error(f"Login error message found ({selector}): {error_text.strip()}")

            # Save page HTML for debugging
            if not self.headless or current_url == self.login_url:
                html_path = f"/tmp/njss_login_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                page_html = await page.content()
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(page_html)
                logger.info(f"Page HTML saved: {html_path}")

            # Wait a bit more for any redirects to complete
            await page.wait_for_timeout(3000)

            # Get final URL after all redirects
            final_url = page.url
            logger.info(f"Final URL after login: {final_url}")

            # Check if login was successful
            # According to user, successful login redirects to /users/home
            if '/users/home' in final_url:
                logger.info("Login successful - redirected to /users/home!")

                # Store cookies for later use
                self.cookies = await self.context.cookies()
                logger.info(f"Stored {len(self.cookies)} cookies after login")

                return True
            elif '/users/' in final_url and '/users/login' not in final_url:
                # We're in the users area but not on login page
                logger.info(f"Login successful - in users area: {final_url}")

                # Store cookies for later use
                self.cookies = await self.context.cookies()
                logger.info(f"Stored {len(self.cookies)} cookies after login")

                return True
            elif 'njss.info' in final_url and '/users/login' not in final_url:
                # We're on NJSS but not in users area - this is wrong according to user
                logger.warning(f"Login redirected to public page instead of /users/home: {final_url}")
                logger.error("Login failed - should redirect to /users/home")
                return False
            else:
                # Debug: Log some page content
                page_text = await page.evaluate('() => document.body.innerText')
                logger.info(f"Page text (first 500 chars): {page_text[:500]}")

                # Check if we can find login form elements to understand the issue
                form_exists = await page.query_selector('form')
                email_field = await page.query_selector(NJSS_SELECTORS['login']['username'])
                password_field = await page.query_selector(NJSS_SELECTORS['login']['password'])

                if form_exists and email_field and password_field:
                    # Check if fields still have values
                    email_value = await email_field.get_attribute('value')
                    password_value = await password_field.get_attribute('value')
                    logger.info(f"Form still exists. Email field has value: {bool(email_value)}, Password field has value: {bool(password_value)}")

                logger.error("Login failed - could not verify successful login")
                return False

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            if self.authenticate:
                raise
            return False

    async def crawl_search_results(self, search_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Crawl search results from NJSS.

        Args:
            search_params: Dictionary with search parameters like:
                - keyword: Search keyword
                - from_date: Start date
                - to_date: End date
                - organization: Organization name

        Returns:
            List of procurement items with their details.
        """
        await self._setup_browser()
        results = []

        try:
            page = await self.context.new_page()

            # Login if authentication is required
            if self.authenticate:
                if not await self._login(page):
                    raise Exception("Authentication failed")

            await page.goto(self.base_url, wait_until='networkidle', timeout=self.timeout)

            # Apply search filters if provided
            if search_params:
                await self._apply_search_filters(page, search_params)

            # Crawl all pages
            has_next = True
            page_num = 1

            while has_next:
                logger.info(f"Crawling page {page_num}")

                # Extract items from current page
                items = await self._extract_items(page)
                results.extend(items)

                # Check for next page
                has_next = await self._go_to_next_page(page)
                page_num += 1

                # Add delay to avoid rate limiting
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error during crawling: {str(e)}")
            raise
        finally:
            await self._cleanup()

        return results

    async def _apply_search_filters(self, page: Page, search_params: Dict[str, Any]):
        """Apply search filters on the page."""
        # The NJSS site uses a search box in the header, not a form
        # We need to fill the search input and click the search button

        if 'keyword' in search_params:
            # Try multiple selectors for the search input
            search_input_selectors = [
                'input[placeholder*="清掃"]',  # Based on placeholder text
                'input[type="text"]:not([name])',  # Text input without name
                'header input[type="text"]',  # Input in header
                '.search-input',
                '#search-keyword'
            ]

            search_input = None
            for selector in search_input_selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=5000)
                    if search_input:
                        logger.debug(f"Found search input with selector: {selector}")
                        break
                except:
                    continue

            if search_input:
                await search_input.fill(search_params['keyword'])

                # Find and click search button
                search_button_selectors = [
                    'button.search-button',
                    'button[type="submit"]',
                    'button:has-text("検索")',
                    '.search-form button',
                    'header button[type="submit"]'
                ]

                for selector in search_button_selectors:
                    try:
                        search_button = await page.query_selector(selector)
                        if search_button:
                            await search_button.click()
                            break
                    except:
                        continue

                # Alternatively, press Enter in the search field
                await search_input.press('Enter')
                await page.wait_for_load_state('networkidle')
            else:
                logger.warning("Could not find search input field")

    async def _extract_items(self, page: Page) -> List[Dict[str, Any]]:
        """Extract procurement items from the current page."""
        items = []

        # Wait for results table to load
        await page.wait_for_selector('table.result-table, div.result-list', timeout=self.timeout)

        # Extract each row/item
        rows = await page.query_selector_all('tr.result-row, div.result-item')

        for row in rows:
            item = {}

            # Extract common fields
            try:
                # Title/Name
                title_elem = await row.query_selector('.title, td.title-column')
                if title_elem:
                    item['title'] = await title_elem.inner_text()

                # Organization
                org_elem = await row.query_selector('.organization, td.org-column')
                if org_elem:
                    item['organization'] = await org_elem.inner_text()

                # Date
                date_elem = await row.query_selector('.date, td.date-column')
                if date_elem:
                    item['date'] = await date_elem.inner_text()

                # Link to details
                link_elem = await row.query_selector('a[href*="detail"]')
                if link_elem:
                    item['detail_url'] = await link_elem.get_attribute('href')
                    if not item['detail_url'].startswith('http'):
                        item['detail_url'] = f"{self.base_url}{item['detail_url']}"

                # ID/Number
                id_elem = await row.query_selector('.id, td.id-column')
                if id_elem:
                    item['procurement_id'] = await id_elem.inner_text()

                items.append(item)

            except Exception as e:
                logger.warning(f"Error extracting item: {str(e)}")
                continue

        return items

    async def _go_to_next_page(self, page: Page) -> bool:
        """Navigate to next page if available."""
        try:
            # Look for next page button/link
            next_button = await page.query_selector('a.next-page, button.next, a:has-text("次へ"), a:has-text("Next")')

            if next_button:
                is_disabled = await next_button.get_attribute('disabled')
                if not is_disabled:
                    await next_button.click()
                    await page.wait_for_load_state('networkidle')
                    return True

            return False

        except Exception as e:
            logger.warning(f"Error navigating to next page: {str(e)}")
            return False

    async def crawl_detail_page(self, detail_url: str) -> Dict[str, Any]:
        """
        Crawl detailed information from a specific procurement page.

        Args:
            detail_url: URL of the detail page

        Returns:
            Dictionary with detailed procurement information.
        """
        await self._setup_browser()

        try:
            page = await self.context.new_page()
            await page.goto(detail_url, wait_until='networkidle', timeout=self.timeout)

            # Extract detailed information
            details = await self._extract_detail_info(page)
            details['url'] = detail_url

            return details

        except Exception as e:
            logger.error(f"Error crawling detail page {detail_url}: {str(e)}")
            raise
        finally:
            await self._cleanup()

    async def _extract_detail_info(self, page: Page) -> Dict[str, Any]:
        """Extract detailed information from a procurement detail page."""
        details = {}

        # Common selectors for detail pages
        field_mapping = {
            'title': ['h1', '.title', '#title'],
            'procurement_id': ['.id', '#procurement-id', 'td:has-text("調達番号") + td'],
            'organization': ['.organization', '#organization', 'td:has-text("機関名") + td'],
            'department': ['.department', '#department', 'td:has-text("部署") + td'],
            'category': ['.category', '#category', 'td:has-text("種別") + td'],
            'announcement_date': ['.announcement-date', 'td:has-text("公告日") + td'],
            'deadline': ['.deadline', 'td:has-text("提出期限") + td'],
            'budget': ['.budget', 'td:has-text("予算") + td'],
            'description': ['.description', '#description', 'td:has-text("概要") + td'],
            'contact': ['.contact', 'td:has-text("連絡先") + td'],
            'documents': ['.documents a', 'a[href$=".pdf"]']
        }

        for field, selectors in field_mapping.items():
            for selector in selectors:
                try:
                    if field == 'documents':
                        # Handle multiple document links
                        elements = await page.query_selector_all(selector)
                        if elements:
                            details[field] = []
                            for elem in elements:
                                doc_info = {
                                    'name': await elem.inner_text(),
                                    'url': await elem.get_attribute('href')
                                }
                                details[field].append(doc_info)
                    else:
                        element = await page.query_selector(selector)
                        if element:
                            details[field] = await element.inner_text()
                            break
                except Exception as e:
                    logger.debug(f"Could not extract {field} with selector {selector}: {str(e)}")

        return details

    def save_to_csv(self, data: List[Dict[str, Any]], output_path: str):
        """Save crawled data to CSV file."""
        if not data:
            logger.warning("No data to save")
            return

        # Get all unique keys
        all_keys = set()
        for item in data:
            all_keys.update(item.keys())

        # Write CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=sorted(all_keys))
            writer.writeheader()
            writer.writerows(data)

        logger.info(f"Saved {len(data)} items to {output_path}")

    def save_to_json(self, data: List[Dict[str, Any]], output_path: str):
        """Save crawled data to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(data)} items to {output_path}")

    async def search_and_download_csv(
        self,
        search_queries: List[str],
        output_filename: Optional[str] = None
    ) -> str:
        """
        Search for items and download results as CSV.

        Args:
            search_queries: List of search queries (e.g., ["衛星", "NOT 工事"])
            output_filename: Custom filename for the CSV (optional)

        Returns:
            str: Path to downloaded CSV file
        """
        await self._setup_browser()

        try:
            # Set up download directory
            download_dir = NJSSAuthConfig.get_download_dir()
            Path(download_dir).mkdir(parents=True, exist_ok=True)

            page = await self.context.new_page()

            # Login if required
            if self.authenticate:
                if not await self._login(page):
                    raise Exception("Authentication failed")

            # Navigate to search page
            await page.goto(self.base_url, wait_until='networkidle')

            # Check if we're on the search conditions page
            if '/users/home' in page.url or '検索条件一覧' in await page.content():
                logger.info("On search conditions page, looking for CSV download option")

                # Look for CSV download toggle
                csv_toggle = await page.query_selector('input[type="checkbox"][id*="csv"], .csv-download-toggle, label:has-text("CSVダウンロード")')
                if csv_toggle:
                    # Check if it's already checked
                    is_checked = await csv_toggle.is_checked()
                    if not is_checked:
                        await csv_toggle.click()
                        logger.info("Enabled CSV download option")
                        await page.wait_for_timeout(1000)

                # Now perform search
                search_text = " ".join(search_queries)
                logger.info(f"Searching for: {search_text}")

                # Look for a search input on this page
                search_input = await page.query_selector('input[name="keyword"], input[placeholder*="キーワード"]')
                if search_input:
                    await search_input.fill(search_text)
                    # Find search button
                    search_button = await page.query_selector('button:has-text("検索"), button[type="submit"]')
                    if search_button:
                        await search_button.click()
                        await page.wait_for_load_state('networkidle')
                else:
                    # Use header search
                    search_params = {'keyword': search_text}
                    await self._apply_search_filters(page, search_params)
            else:
                # Regular search flow
                search_text = " ".join(search_queries)
                logger.info(f"Searching for: {search_text}")

                # Apply search
                search_params = {'keyword': search_text}
                await self._apply_search_filters(page, search_params)

            # Wait for results
            await page.wait_for_selector(NJSS_SELECTORS['search']['results'], timeout=self.timeout)

            # Handle CSV download
            download_path = None

            async def handle_download(download: Download):
                nonlocal download_path
                if output_filename:
                    filename = output_filename
                else:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"njss_search_{timestamp}.csv"

                download_path = os.path.join(download_dir, filename)
                await download.save_as(download_path)
                logger.info(f"Downloaded CSV to: {download_path}")

            # Listen for download
            page.on('download', handle_download)

            # Try multiple CSV download selectors
            csv_button = None
            for selector in NJSS_SELECTORS['search']['csv_download']:
                csv_button = await page.query_selector(selector)
                if csv_button:
                    logger.debug(f"Found CSV button with selector: {selector}")
                    break

            if not csv_button:
                # If no CSV button found, try to extract data and save manually
                logger.warning("CSV download button not found, extracting data manually")
                items = await self._extract_items(page)

                # Save manually
                if output_filename:
                    filename = output_filename
                else:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"njss_search_{timestamp}.csv"

                download_path = os.path.join(download_dir, filename)
                self.save_to_csv(items, download_path)
                return download_path

            # Click CSV download button
            await csv_button.click()

            # Wait for download
            await page.wait_for_timeout(5000)

            if not download_path:
                raise Exception("CSV download failed - no file downloaded")

            return download_path

        except Exception as e:
            logger.error(f"Search and download error: {str(e)}")
            raise
        finally:
            await self._cleanup()


class NJSSHomeCrawler(NJSSCrawler):
    """Crawler for downloading CSV from NJSS home page."""

    async def download_from_home(self) -> List[str]:
        """Download CSV files from NJSS home page after login."""
        downloaded_files = []
        await self._setup_browser()

        try:
            page = await self.context.new_page()

            # Login if authentication is required
            if self.authenticate:
                if not await self._login(page):
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
            screenshot_path = f"/tmp/njss_users_home_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=screenshot_path)
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

            # Log page structure on users/home
            logger.info("Analyzing users/home page structure...")

            # Check page title
            page_title = await page.title()
            logger.info(f"Page title: {page_title}")

            # Check if we're really on the users/home page
            if '/users/home' not in current_url:
                logger.warning(f"Not on users/home page. Current URL: {current_url}")

                # If redirected to login, session was lost
                if '/users/login' in current_url:
                    logger.error("Session lost - redirected back to login page after navigation")

                    # Save page HTML for debugging
                    html_path = f"/tmp/njss_redirect_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                    page_html = await page.content()
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(page_html)
                    logger.info(f"Redirect page HTML saved: {html_path}")

                    raise Exception("Session not maintained - please login correctly")

            # If no download buttons found, let's explore the page
            if len(download_buttons) == 0:
                logger.info("No download buttons found. Exploring page structure...")

                # Log all links on the page
                all_links = await page.query_selector_all('a')
                logger.info(f"Found {len(all_links)} links on page")
                for i, link in enumerate(all_links[:10]):  # First 10 links
                    href = await link.get_attribute('href')
                    text = await link.text_content()
                    logger.info(f"Link {i}: text='{text}', href='{href}'")

                # Log all buttons
                all_buttons = await page.query_selector_all('button')
                logger.info(f"Found {len(all_buttons)} buttons on page")
                for i, button in enumerate(all_buttons[:10]):  # First 10 buttons
                    text = await button.text_content()
                    logger.info(f"Button {i}: text='{text}'")

                # Look for "入札案件の検索条件結果" section and its download button
                logger.info("Looking for '入札案件の検索条件結果' or any '検索条件' sections...")

                # Look for any elements containing search conditions text
                search_condition_texts = [
                    '入札案件の検索条件結果',
                    '検索条件結果',
                    '検索条件',
                    '保存した検索条件',
                    'お気に入り検索条件'
                ]

                # Check for tables with saved search conditions
                tables = await page.query_selector_all('table')
                logger.info(f"Found {len(tables)} tables on page")

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

                # Find all elements that might contain search results
                all_elements = await page.query_selector_all('div, section, article, li, tr')

                for element in all_elements:
                    try:
                        element_text = await element.text_content()
                        if element_text:
                            for search_text in search_condition_texts:
                                if search_text in element_text:
                                    logger.info(f"Found section with '{search_text}'")

                                    # Look for download button within or near this element
                                    # Check within the element
                                    download_btn = await element.query_selector('button:has-text("ダウンロード"), a:has-text("ダウンロード"), button:has-text("CSV"), a:has-text("CSV")')
                                    if download_btn:
                                        logger.info(f"Found download button within '{search_text}' section")
                                        download_buttons.append(download_btn)
                                        break

                                    # Check parent element
                                    parent = await element.evaluate_handle('(el) => el.parentElement')
                                    if parent:
                                        parent_download = await parent.query_selector('button:has-text("ダウンロード"), a:has-text("ダウンロード")')
                                        if parent_download:
                                            logger.info(f"Found download button in parent of '{search_text}' section")
                                            download_buttons.append(parent_download)
                                            break
                    except:
                        continue

                # If still no download buttons, log all elements with "ダウンロード" text
                if len(download_buttons) == 0:
                    logger.info("No download buttons found in search sections. Looking for any download links...")
                    all_download_elements = await page.query_selector_all('*:has-text("ダウンロード")')
                    logger.info(f"Found {len(all_download_elements)} elements with 'ダウンロード' text")

                    for i, elem in enumerate(all_download_elements[:5]):
                        tag_name = await elem.evaluate('el => el.tagName')
                        elem_text = await elem.text_content()
                        logger.info(f"Download element {i}: tag={tag_name}, text='{elem_text[:100]}'")

                        # If it's a clickable element, add it
                        if tag_name.lower() in ['button', 'a']:
                            download_buttons.append(elem)

            for i, btn in enumerate(download_buttons):
                try:
                    if not await btn.is_visible():
                        continue

                    # Set up download handler
                    download_path = None

                    async def handle_download(download: Download):
                        nonlocal download_path
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        download_dir = NJSSAuthConfig.get_download_dir()
                        Path(download_dir).mkdir(parents=True, exist_ok=True)

                        filename = f"njss_home_{i+1}_{timestamp}_{download.suggested_filename or 'download.zip'}"
                        download_path = os.path.join(download_dir, filename)
                        await download.save_as(download_path)
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

                    if download_path and os.path.exists(download_path):
                        downloaded_files.append(download_path)

                    page.remove_listener('download', handle_download)

                except Exception as e:
                    logger.error(f"Error with download button {i+1}: {str(e)}")
                    continue

            # If no files downloaded, save page HTML for debugging
            if not downloaded_files:
                html_path = f"/tmp/njss_home_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                page_html = await page.content()
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(page_html)
                logger.error(f"No files downloaded from NJSS. Page HTML saved for debugging: {html_path}")

                # Take a screenshot for debugging
                screenshot_path = f"/tmp/njss_no_download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.error(f"Screenshot saved: {screenshot_path}")

                # Log all text content on the page
                page_text = await page.evaluate('() => document.body.innerText')
                logger.info(f"Page text (first 1000 chars): {page_text[:1000]}")

                raise Exception("Failed to download CSV from NJSS. No download buttons found or download failed.")

            return downloaded_files

        except Exception as e:
            logger.error(f"Home download error: {str(e)}")
            raise
        finally:
            await self._cleanup()


def main(**context):
    """
    Main function for Airflow PythonOperator to download NJSS CSV data.
    Downloads CSV from NJSS home page and saves to /data/search_result.csv

    Args:
        **context: Airflow context (optional)

    Returns:
        str: Path to the downloaded CSV file
    """
    import zipfile
    import shutil

    logger.info("Starting NJSS CSV download...")

    # Set up output paths
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    final_csv_path = CSV_FILE_PATH

    try:
        # Create crawler with authentication
        crawler = NJSSHomeCrawlerSync(
            authenticate=True,
            headless=True,
            timeout=60000
        )

        # Download files from home page
        downloaded_files = crawler.download_from_home()

        if not downloaded_files:
            logger.warning("No files were downloaded from NJSS")
            return None

        logger.info(f"Downloaded {len(downloaded_files)} files")

        # Process downloaded files
        all_csv_files = []

        for file_path in downloaded_files:
            logger.info(f"Processing: {file_path}")

            if file_path.endswith('.zip'):
                # Extract ZIP file
                extract_dir = file_path.replace('.zip', '_extracted')

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
            return None

        # If we have CSV files, use them
        if all_csv_files:
            # If the test file is among them, use it
            test_file_path = os.path.join(DATA_DIR, "njss", "search_result.csv")
            if test_file_path in all_csv_files and len(all_csv_files) == 1:
                # This is our test file, copy it to the expected location
                shutil.copy2(test_file_path, final_csv_path)
                logger.info(f"Using test CSV file at {final_csv_path}")
            elif len(all_csv_files) == 1:
                # Single CSV file, just copy it
                shutil.copy2(all_csv_files[0], final_csv_path)
                logger.info(f"Copied single CSV to {final_csv_path}")
            else:
                # Multiple CSV files - merge them
                import pandas as pd

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

        # Push result to XCom if in Airflow context
        if context and 'task_instance' in context:
            # Convert Path to string for JSON serialization
            csv_path_str = str(final_csv_path)
            context['task_instance'].xcom_push(key='csv_path', value=csv_path_str)
            context['task_instance'].xcom_push(key='download_status', value='success')

        logger.info(f"Successfully saved CSV to {final_csv_path}")
        return str(final_csv_path)

    except Exception as e:
        logger.error(f"Failed to download NJSS CSV: {str(e)}")

        # Push error to XCom if in Airflow context
        if context and 'task_instance' in context:
            context['task_instance'].xcom_push(key='download_status', value='failed')
            context['task_instance'].xcom_push(key='error_message', value=str(e))

        raise


class TempCrawler:
    """Temporary crawler for backward compatibility."""

    def crawl_njss_csv(self):
        print("Crawling NJSS CSV data...")
        # Use the main function
        return main()


# Synchronous wrapper for Airflow compatibility
class NJSSCrawlerSync:
    """Synchronous wrapper for NJSSCrawler to use with Airflow."""

    def __init__(self, **kwargs):
        self.crawler = NJSSCrawler(**kwargs)

    def crawl_search_results(self, search_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Synchronous version of crawl_search_results."""
        return asyncio.run(self.crawler.crawl_search_results(search_params))

    def crawl_detail_page(self, detail_url: str) -> Dict[str, Any]:
        """Synchronous version of crawl_detail_page."""
        return asyncio.run(self.crawler.crawl_detail_page(detail_url))

    def search_and_download_csv(
        self,
        search_queries: List[str],
        output_filename: Optional[str] = None
    ) -> str:
        """Synchronous version of search_and_download_csv."""
        return asyncio.run(
            self.crawler.search_and_download_csv(search_queries, output_filename)
        )

    def save_to_csv(self, data: List[Dict[str, Any]], output_path: str):
        """Save data to CSV."""
        self.crawler.save_to_csv(data, output_path)

    def save_to_json(self, data: List[Dict[str, Any]], output_path: str):
        """Save data to JSON."""
        self.crawler.save_to_json(data, output_path)


class NJSSHomeCrawlerSync:
    """Synchronous wrapper for NJSSHomeCrawler to use with Airflow."""

    def __init__(self, **kwargs):
        self.crawler = NJSSHomeCrawler(**kwargs)

    def download_from_home(self) -> List[str]:
        """Download from home page synchronously."""
        return asyncio.run(self.crawler.download_from_home())
