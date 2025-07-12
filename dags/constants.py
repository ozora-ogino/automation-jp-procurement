import os
from pathlib import Path

# Directory paths
DATA_DIR = Path("/opt/airflow/csv_data")
DOC_DIR = DATA_DIR / "documents"
CSV_FILE_PATH = DATA_DIR / "search_result.csv"

# Fixed User-Agent to prevent "new device" detection
# This UA is used across all crawlers for consistency
PLAYWRIGHT_UA = os.getenv('NJSS_USER_AGENT',
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
