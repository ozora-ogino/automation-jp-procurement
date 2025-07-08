"""Secure configuration for NJSS authentication."""

import os
from typing import Optional
from airflow.models import Variable
from airflow.hooks.base import BaseHook


class NJSSAuthConfig:
    """Secure configuration handler for NJSS credentials."""

    @staticmethod
    def get_credentials() -> tuple[str, str]:
        """
        Get NJSS credentials from various sources in order of preference:
        1. Airflow Connections
        2. Airflow Variables
        3. Environment variables
        4. .env file (for local development)

        Returns:
            tuple: (username, password)
        """
        username = None
        password = None

        # Try Airflow Connection first (most secure)
        try:
            conn = BaseHook.get_connection('njss_default')
            username = conn.login
            password = conn.password
            if username and password:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Got credentials from Airflow connection: {username}")
                return username, password
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Could not get Airflow connection: {e}")
            pass

        # Try Airflow Variables
        try:
            username = Variable.get('njss_username', default_var=None)
            password = Variable.get('njss_password', default_var=None)
            if username and password:
                return username, password
        except Exception:
            pass

        # Try environment variables
        username = os.getenv('NJSS_USERNAME')
        password = os.getenv('NJSS_PASSWORD')
        if username and password:
            return username, password

        # Try .env file for local development
        try:
            from dotenv import load_dotenv
            load_dotenv()
            username = os.getenv('NJSS_USERNAME')
            password = os.getenv('NJSS_PASSWORD')
            if username and password:
                return username, password
        except ImportError:
            pass

        raise ValueError(
            "NJSS credentials not found. Please set them using one of:\n"
            "1. Airflow Connection named 'njss_default'\n"
            "2. Airflow Variables 'njss_username' and 'njss_password'\n"
            "3. Environment variables NJSS_USERNAME and NJSS_PASSWORD\n"
            "4. .env file with NJSS_USERNAME and NJSS_PASSWORD"
        )

    @staticmethod
    def get_download_dir() -> str:
        """Get download directory from configuration."""
        # Try Airflow Variable first
        try:
            return Variable.get('njss_download_dir', default_var='/opt/airflow/data/njss')
        except Exception:
            pass

        # Fall back to environment variable
        return os.getenv('NJSS_DOWNLOAD_DIR', '/opt/airflow/data/njss')

    @staticmethod
    def get_browser_config() -> dict:
        """Get browser configuration."""
        config = {
            'headless': True,
            'timeout': 30000,
        }

        # Check for debug mode
        try:
            debug_mode = Variable.get('njss_debug_mode', default_var='false')
            if debug_mode.lower() == 'true':
                config['headless'] = False
        except Exception:
            if os.getenv('NJSS_DEBUG_MODE', '').lower() == 'true':
                config['headless'] = False

        return config


# Selectors configuration based on NJSS website structure
NJSS_SELECTORS = {
    'login': {
        'form': 'form#login-form, form[action*="login"], form',
        'username': '#email, input[type="email"], input[name="email"], input[name="username"]',
        'password': '#password, input[type="password"], input[name="password"]',
        'submit': 'button[type="submit"], input[type="submit"], button:has-text("ログイン")',
        'captcha': 'img[alt*="captcha"], .captcha-image, img[src*="captcha"]',
        'logout': 'a[href*="logout"], button:has-text("ログアウト"), .logout-link'
    },
    'search': {
        'keyword': 'input[name="keyword"], input[name="search"], #search-keyword, .search-input',
        'submit': 'button[type="submit"], button:has-text("検索"), .search-button',
        'results': '.result-table, .search-results, table.results',
        'csv_download': [
            'button:has-text("CSV")',
            'a:has-text("CSVダウンロード")',
            'button:has-text("エクスポート")',
            'a:has-text("CSV出力")',
            '.csv-download',
            'a[href*=".csv"]',
            'button[onclick*="csv"]'
        ],
        'next_page': 'a:has-text("次へ"), a:has-text("Next"), .next-page, a.next'
    }
}

# Example .env file content (create this file for local development)
ENV_TEMPLATE = """# NJSS Credentials
NJSS_USERNAME=your_username
NJSS_PASSWORD=your_password

# Optional settings
NJSS_DOWNLOAD_DIR=/opt/airflow/downloads
NJSS_DEBUG_MODE=false
"""

# Instructions for setting up Airflow Connection
AIRFLOW_CONNECTION_SETUP = """
To set up NJSS credentials in Airflow:

1. Via Airflow UI:
   - Go to Admin -> Connections
   - Click "Create"
   - Set:
     - Connection Id: njss_default
     - Connection Type: Generic
     - Login: your_njss_username
     - Password: your_njss_password

2. Via Airflow CLI:
   airflow connections add njss_default \\
     --conn-type generic \\
     --conn-login your_username \\
     --conn-password your_password

3. Via environment variable:
   export AIRFLOW_CONN_NJSS_DEFAULT='{"conn_type":"generic","login":"your_username","password":"your_password"}'
"""
