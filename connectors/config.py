"""API connector configuration. Loads keys from .env file."""

import os
from pathlib import Path

_env_path = Path(__file__).parent.parent / '.env'

try:
    from dotenv import load_dotenv
    load_dotenv(_env_path)
except ImportError:
    # Manual .env loader — no dependency needed
    if _env_path.exists():
        with open(_env_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _key, _val = _line.split('=', 1)
                    os.environ.setdefault(_key.strip(), _val.strip())

# US Economic Data
FRED_API_KEY = os.getenv('FRED_API_KEY', '')
BLS_API_KEY = os.getenv('BLS_API_KEY', '')
BEA_API_KEY = os.getenv('BEA_API_KEY', '')
CENSUS_API_KEY = os.getenv('CENSUS_API_KEY', '')

# SEC EDGAR
EDGAR_CONTACT_EMAIL = os.getenv('EDGAR_CONTACT_EMAIL', 'research@example.com')

# Web Search
SERPER_API_KEY = os.getenv('SERPER_API_KEY', '')
