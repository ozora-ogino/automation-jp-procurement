#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from typing import List, Dict, Optional
from playwright.async_api import Page, BrowserContext

from utils.file_naming import FileNaming

logger = logging.getLogger(__name__)


class NJSSAuthenticationService:
    """Centralized authentication service for NJSS"""
    
    # Selectors for login form (matching the original NJSS_SELECTORS)
    LOGIN_SELECTORS = {
        'form': 'form#login-form, form[action*="login"], form',
        'username': '#email, input[type="email"], input[name="email"], input[name="username"]',
        'password': '#password, input[type="password"], input[name="password"]',
        'captcha': 'img[alt*="captcha"], .captcha-image, img[src*="captcha"]',
        'submit': 'button[type="submit"], input[type="submit"], button:has-text("ログイン")',
        'error': '.error, .alert-danger, [class*="error"], .flash-message, .alert'
    }
    
    def __init__(self, username: str, password: str, headless: bool = True, timeout: int = 30000):
        self.username = username
        self.password = password
        self.headless = headless
        self.timeout = timeout
        self.cookies: List[Dict] = []
    
    async def login(self, page: Page, login_url: str) -> bool:
        """
        Unified login method for NJSS.
        Returns True if login successful, False otherwise.
        """
        try:
            # Check if already logged in
            current_url = page.url
            if self._is_logged_in(current_url):
                logger.info("Already logged in")
                return True
            
            logger.info("Attempting to login to NJSS")
            
            # Navigate to login page if not already there
            if login_url not in current_url:
                await page.goto(login_url, wait_until='networkidle', timeout=self.timeout)
                # Wait a bit for any redirects
                await page.wait_for_timeout(2000)
            
            # Check again if we were redirected to home (already logged in)
            current_url = page.url
            if self._is_logged_in(current_url):
                logger.info("Already logged in after navigation")
                return True
            
            logger.info(f"Current URL: {page.url}")
            
            # Wait for login form - with a shorter timeout and more specific error handling
            try:
                await page.wait_for_selector(self.LOGIN_SELECTORS['form'], timeout=5000)
            except:
                # If form not found, check if we're logged in
                if self._is_logged_in(page.url):
                    logger.info("Login form not found but already logged in")
                    return True
                # Try alternative login selectors
                logger.warning("Default form selector not found, trying alternatives...")
                form_found = False
                for selector in ['form', '#loginForm', '.login-form', 'form[method="post"]']:
                    if await page.query_selector(selector):
                        form_found = True
                        break
                if not form_found:
                    raise Exception("Login form not found on page")
            
            # Take screenshot before login (debug mode)
            if not self.headless:
                screenshot_path = f"/tmp/{FileNaming.get_njss_screenshot_name('before_login')}"
                await page.screenshot(path=screenshot_path)
                logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Fill credentials
            success = await self._fill_credentials(page)
            if not success:
                return False
            
            # Check for CAPTCHA
            await self._handle_captcha(page)
            
            # Submit form
            await self._submit_login_form(page)
            
            # Wait for navigation
            await self._wait_for_login_completion(page)
            
            # Verify login success
            final_url = page.url
            if self._is_logged_in(final_url):
                logger.info(f"Login successful - redirected to: {final_url}")
                
                # Store cookies for session persistence
                context = page.context
                self.cookies = await context.cookies()
                logger.info(f"Stored {len(self.cookies)} cookies after login")
                
                return True
            else:
                logger.error(f"Login failed - still on: {final_url}")
                await self._log_login_errors(page)
                return False
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            raise
    
    async def _fill_credentials(self, page: Page) -> bool:
        """Fill username and password fields"""
        try:
            # Fill username
            logger.info(f"Filling username field with: {self.username}")
            username_field = await page.query_selector(self.LOGIN_SELECTORS['username'])
            if not username_field:
                logger.error("Username field not found!")
                return False
            
            await username_field.click()
            await username_field.fill('')  # Clear existing value
            await username_field.type(self.username, delay=50)
            
            # Fill password
            logger.info("Filling password field...")
            password_field = await page.query_selector(self.LOGIN_SELECTORS['password'])
            if not password_field:
                logger.error("Password field not found!")
                return False
            
            await password_field.click()
            await password_field.fill('')  # Clear existing value
            await password_field.type(self.password, delay=50)
            
            # Trigger JavaScript validation events
            await page.evaluate("""
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
            
            return True
            
        except Exception as e:
            logger.error(f"Error filling credentials: {str(e)}")
            return False
    
    async def _handle_captcha(self, page: Page) -> None:
        """Check and handle CAPTCHA if present"""
        captcha = await page.query_selector(self.LOGIN_SELECTORS['captcha'])
        if captcha:
            logger.warning("CAPTCHA detected - manual intervention may be required")
            if not self.headless:
                logger.info("Please solve the CAPTCHA manually within 30 seconds")
                await page.wait_for_timeout(30000)
    
    async def _submit_login_form(self, page: Page) -> None:
        """Submit the login form"""
        logger.info("Looking for login submit button...")
        
        submit_button = await page.query_selector(self.LOGIN_SELECTORS['submit'])
        if not submit_button:
            raise Exception("Cannot find submit button")
        
        logger.info("Clicking submit button...")
        await submit_button.click()
    
    async def _wait_for_login_completion(self, page: Page) -> None:
        """Wait for login process to complete"""
        try:
            await page.wait_for_navigation(timeout=15000)
            logger.info("Navigation detected after form submission")
        except:
            logger.info("No navigation detected, waiting for page to settle...")
            await page.wait_for_timeout(5000)
    
    async def _log_login_errors(self, page: Page) -> None:
        """Log any error messages on the page"""
        error_selectors = self.LOGIN_SELECTORS['error'].split(', ')
        for selector in error_selectors:
            error_elems = await page.query_selector_all(selector)
            for error_elem in error_elems:
                error_text = await error_elem.text_content()
                if error_text and error_text.strip():
                    logger.error(f"Login error message found ({selector}): {error_text.strip()}")
        
        # Save page HTML for debugging
        if not self.headless:
            html_path = f"/tmp/njss_login_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            page_html = await page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(page_html)
            logger.info(f"Error page HTML saved: {html_path}")
    
    def _is_logged_in(self, url: str) -> bool:
        """Check if URL indicates successful login"""
        # Various patterns that indicate we're logged in
        logged_in_patterns = [
            '/users/home',
            '/mypage',
            '/dashboard',
            '/offers/view',  # Case detail pages
            '/offers/search',  # Search pages
        ]
        
        # Check if we're on a logged-in page
        for pattern in logged_in_patterns:
            if pattern in url:
                return True
        
        # Also check if we're NOT on login/signup pages
        if ('/users/' in url and '/users/login' not in url and '/users/signup' not in url):
            return True
            
        # Check if we're on the main site but not on login
        if 'njss.info' in url and '/login' not in url and url != 'https://www2.njss.info/':
            # If we're on a specific page (not just the root), we're likely logged in
            if len(url.replace('https://www2.njss.info/', '').strip('/')) > 0:
                return True
        
        return False
    
    async def restore_cookies(self, context: BrowserContext) -> None:
        """Restore saved cookies to browser context"""
        if self.cookies:
            await context.add_cookies(self.cookies)
            logger.info(f"Restored {len(self.cookies)} cookies to context")