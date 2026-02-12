"""
File-based caching layer with TTL for API responses.
Prevents re-fetching data that hasn't changed (FRED publishes monthly, BLS quarterly).
"""
import json
import os
import time
import hashlib

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cache')


class DataCache:
    def __init__(self, cache_dir=CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _cache_key(self, source: str, method: str, params: dict = None) -> str:
        """Generate cache filename from source + method + params."""
        key_str = f"{source}:{method}:{json.dumps(params or {}, sort_keys=True)}"
        key_hash = hashlib.md5(key_str.encode()).hexdigest()[:12]
        return f"{source}_{method}_{key_hash}.json"

    def get(self, source: str, method: str, params: dict = None, ttl_hours: float = 24):
        """Get cached data if it exists and is within TTL."""
        cache_file = os.path.join(self.cache_dir, self._cache_key(source, method, params))
        if not os.path.exists(cache_file):
            return None
        try:
            age_hours = (time.time() - os.path.getmtime(cache_file)) / 3600
            if age_hours > ttl_hours:
                return None
            with open(cache_file, 'r') as f:
                cached = json.load(f)
            cached['_cache_age_hours'] = round(age_hours, 1)
            return cached
        except (json.JSONDecodeError, OSError):
            return None

    def set(self, source: str, method: str, params: dict = None, data: dict = None):
        """Store data in cache. Params must match those used in get()."""
        cache_file = os.path.join(self.cache_dir, self._cache_key(source, method, params))
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except OSError:
            pass  # Cache write failure is non-fatal

    def clear(self, source: str = None):
        """Clear cache, optionally for a specific source."""
        for f in os.listdir(self.cache_dir):
            if source is None or f.startswith(source):
                try:
                    os.remove(os.path.join(self.cache_dir, f))
                except OSError:
                    pass

    def stats(self) -> dict:
        """Return cache statistics."""
        files = os.listdir(self.cache_dir)
        total_size = sum(os.path.getsize(os.path.join(self.cache_dir, f)) for f in files if f.endswith('.json'))
        return {
            'entries': len([f for f in files if f.endswith('.json')]),
            'total_size_kb': round(total_size / 1024, 1),
            'sources': list(set(f.split('_')[0] for f in files if f.endswith('.json')))
        }


# Default TTLs by source (hours)
DEFAULT_TTLS = {
    'fred': 168,      # 7 days -- publishes monthly
    'bls': 168,       # 7 days -- publishes monthly/quarterly
    'census_cbp': 168,  # 7 days -- annual dataset, rarely changes
    'qcew': 168,      # 7 days -- quarterly releases (QCEW manages its own CSV cache)
    'edgar': 12,      # 12 hours -- filings arrive continuously
    'websearch': 6,   # 6 hours -- news changes fast
}
