"""Research engine API connectors.

13 data sources:
  US:    FRED, BLS, BEA, Census, EDGAR, Yahoo Finance, Google Trends, O*NET
  Intl:  World Bank, OECD, Eurostat
  Meta:  Web Search, Counter-Signals
"""

from .fred import FredConnector
from .bls import BLSConnector
from .edgar import EdgarConnector
from .websearch import WebSearchConnector
from .bea import BEAConnector
from .census import CensusConnector
from .worldbank import WorldBankConnector
from .oecd import OECDConnector
from .eurostat import EurostatConnector
from .yfinance import YFinanceConnector
from .google_trends import GoogleTrendsConnector
from .onet import ONetConnector
from .cache import DataCache, DEFAULT_TTLS
from .counter_signals import CounterSignalSearcher
from .sector_screener import SectorScreener

__all__ = [
    # US economic
    'FredConnector', 'BLSConnector', 'BEAConnector', 'CensusConnector',
    # US labor/occupation
    'ONetConnector',
    # US market/filing
    'EdgarConnector', 'YFinanceConnector', 'GoogleTrendsConnector',
    # International
    'WorldBankConnector', 'OECDConnector', 'EurostatConnector',
    # Meta
    'WebSearchConnector', 'CounterSignalSearcher',
    # Data-driven sector discovery
    'SectorScreener',
    # Infrastructure
    'DataCache', 'DEFAULT_TTLS',
]
