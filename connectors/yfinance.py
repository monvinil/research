"""Yahoo Finance connector — market data for sector tracking.

NO API key needed (uses yfinance library or direct API).

Purpose: Stock prices and financials for publicly traded companies
are high-frequency signals of sector health. When an entire sector
is declining in market cap while the broader market rises, that's
a strong P2 liquidation cascade signal.

Also: sector ETFs give instant read on market sentiment for industries.
"""

import requests
from datetime import datetime, timedelta

# Using Yahoo Finance v8 API directly (no library dependency)
BASE_URL = 'https://query1.finance.yahoo.com/v8/finance'

# Sector ETFs for quick sector health reads
SECTOR_ETFS = {
    'XLK': 'Technology',
    'XLF': 'Financials',
    'XLV': 'Healthcare',
    'XLI': 'Industrials',
    'XLE': 'Energy',
    'XLRE': 'Real Estate',
    'XLC': 'Communications',
    'XLY': 'Consumer Discretionary',
    'XLP': 'Consumer Staples',
    'XLU': 'Utilities',
    'XLB': 'Materials',
}

# Key individual stocks for monitoring
WATCHLIST = {
    # Professional services incumbents
    'ACN': 'Accenture (consulting/outsourcing)',
    'INFY': 'Infosys (IT services)',
    'WIT': 'Wipro (IT services)',

    # AI/automation leaders
    'NVDA': 'NVIDIA (AI infrastructure)',
    'MSFT': 'Microsoft (Azure AI)',
    'GOOG': 'Google (AI/Cloud)',

    # Staffing/HR (P2 canaries)
    'RHI': 'Robert Half (professional staffing)',
    'HAYS.L': 'Hays (UK staffing)',
    'MAN': 'ManpowerGroup',
    'KELYA': 'Kelly Services',

    # Legal/compliance tech
    'LEGN': 'Legend Biotech (for legal sector baseline)',

    # Healthcare services
    'HCA': 'HCA Healthcare',
    'UHS': 'Universal Health Services',
    'AMN': 'AMN Healthcare (staffing)',

    # Construction tech
    'PCOR': 'Procore Technologies',
    'ADSK': 'Autodesk',

    # Insurance
    'TRV': 'Travelers',
    'SPGI': 'S&P Global',
}


class YFinanceConnector:
    """Pull market data from Yahoo Finance."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        })

    def _get_chart(self, symbol, period='6mo', interval='1d'):
        """Get price history for a symbol."""
        url = f'{BASE_URL}/chart/{symbol}'
        params = {
            'range': period,
            'interval': interval,
            'includePrePost': 'false',
        }

        try:
            r = self.session.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()

            result = data.get('chart', {}).get('result', [{}])[0]
            timestamps = result.get('timestamp', [])
            indicators = result.get('indicators', {})
            quote = indicators.get('quote', [{}])[0]
            closes = quote.get('close', [])
            volumes = quote.get('volume', [])

            observations = []
            for i, ts in enumerate(timestamps):
                if i < len(closes) and closes[i] is not None:
                    date = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                    observations.append({
                        'date': date,
                        'close': round(closes[i], 2),
                        'volume': volumes[i] if i < len(volumes) else None,
                    })

            return {
                'symbol': symbol,
                'observations': observations,
            }
        except Exception as e:
            return {'symbol': symbol, 'error': str(e)}

    def get_sector_etf_performance(self, period='6mo'):
        """Get performance of all sector ETFs.

        Sectors declining relative to SPY = under stress.
        Sectors outperforming = attracting capital.
        """
        results = {}
        for symbol, name in SECTOR_ETFS.items():
            data = self._get_chart(symbol, period)
            if 'error' not in data and data.get('observations'):
                obs = data['observations']
                if len(obs) >= 2:
                    first = obs[0]['close']
                    last = obs[-1]['close']
                    if first > 0:
                        performance = round((last - first) / first * 100, 2)
                    else:
                        performance = 0
                    results[symbol] = {
                        'name': name,
                        'performance_pct': performance,
                        'latest_close': last,
                        'period_start': obs[0]['date'],
                        'period_end': obs[-1]['date'],
                    }

        # Sort by performance
        sorted_sectors = sorted(results.items(), key=lambda x: x[1]['performance_pct'])

        return {
            'signal_type': 'sector_performance',
            'principle': 'P2,capital_modeling',
            'data': results,
            'ranked': [(s, d['name'], d['performance_pct']) for s, d in sorted_sectors],
            'interpretation': (
                'Bottom-performing sectors are under the most stress — '
                'potential liquidation cascade targets. Top performers are '
                'where capital is flowing. Divergence between sectors confirms '
                'structural rotation, not just cyclical.'
            ),
        }

    def get_staffing_canary(self, period='1y'):
        """Track staffing company stocks — P2 leading indicator.

        Staffing companies are the canary in the coal mine for labor
        markets. When they decline, employers are cutting flexible
        labor first (before permanent layoffs show up in BLS data).
        """
        canaries = ['RHI', 'MAN', 'KELYA']
        results = {}

        for symbol in canaries:
            data = self._get_chart(symbol, period)
            if 'error' not in data and data.get('observations'):
                obs = data['observations']
                if len(obs) >= 2:
                    first = obs[0]['close']
                    last = obs[-1]['close']
                    performance = round((last - first) / first * 100, 2) if first > 0 else 0
                    results[symbol] = {
                        'name': WATCHLIST.get(symbol, symbol),
                        'performance_pct': performance,
                        'latest_close': last,
                    }

        return {
            'signal_type': 'staffing_canary',
            'principle': 'P2',
            'data': results,
            'interpretation': (
                'Staffing companies declining = employers cutting flexible '
                'labor. This leads BLS employment data by 1-3 months. '
                'All three declining together = broad-based labor market '
                'softening, not sector-specific.'
            ),
        }

    def get_ai_infrastructure_momentum(self, period='6mo'):
        """Track AI infrastructure stocks — P1 adoption speed signal."""
        ai_stocks = ['NVDA', 'MSFT', 'GOOG']
        results = {}

        for symbol in ai_stocks:
            data = self._get_chart(symbol, period)
            if 'error' not in data and data.get('observations'):
                obs = data['observations']
                if len(obs) >= 2:
                    first = obs[0]['close']
                    last = obs[-1]['close']
                    performance = round((last - first) / first * 100, 2) if first > 0 else 0
                    results[symbol] = {
                        'name': WATCHLIST.get(symbol, symbol),
                        'performance_pct': performance,
                        'latest_close': last,
                    }

        return {
            'signal_type': 'ai_infrastructure',
            'principle': 'P1',
            'data': results,
            'interpretation': (
                'AI infrastructure stocks rising = capital flowing into AI '
                'buildout. Confirms P1 infrastructure overshoot. When these '
                'stocks eventually decline, it signals AI capex pullback '
                'which is GOOD for application-layer startups (cheaper compute).'
            ),
        }

    def get_full_scan(self):
        """Run all market analyses."""
        return {
            'sector_performance': self.get_sector_etf_performance(),
            'staffing_canary': self.get_staffing_canary(),
            'ai_infrastructure': self.get_ai_infrastructure_momentum(),
        }

    def test_connection(self):
        """Verify Yahoo Finance access."""
        try:
            data = self._get_chart('SPY', period='5d')
            count = len(data.get('observations', []))
            return {
                'status': 'ok',
                'source': 'Yahoo Finance',
                'test': f'SPY data points: {count}',
            }
        except Exception as e:
            return {'status': 'error', 'source': 'Yahoo Finance', 'error': str(e)}
