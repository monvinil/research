"""API connector configuration. Loads keys from .env file."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass  # dotenv not installed, rely on environment variables

FRED_API_KEY = os.getenv('FRED_API_KEY', '')
BLS_API_KEY = os.getenv('BLS_API_KEY', '')
EDGAR_CONTACT_EMAIL = os.getenv('EDGAR_CONTACT_EMAIL', 'research@example.com')
SERPER_API_KEY = os.getenv('SERPER_API_KEY', '')
