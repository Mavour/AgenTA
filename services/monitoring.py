import logging
import time
import traceback
from datetime import datetime
from functools import wraps
from typing import Callable

logger = logging.getLogger(__name__)

class ErrorTracker:
    def __init__(self):
        self.errors = []
        self.error_counts = {}
        self.start_time = time.time()
    
    def log_error(self, error_type: str, error_msg: str, details: str = ""):
        now = datetime.now().isoformat()
        entry = {
            "timestamp": now,
            "type": error_type,
            "message": error_msg,
            "details": details
        }
        self.errors.append(entry)
        
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        if len(self.errors) > 100:
            self.errors = self.errors[-100:]
        
        logger.error(f"[{error_type}] {error_msg} - {details}")
    
    def get_error_summary(self):
        uptime = time.time() - self.start_time
        return {
            "uptime_seconds": uptime,
            "total_errors": len(self.errors),
            "error_counts": self.error_counts,
            "recent_errors": self.errors[-5:]
        }
    
    def clear_old_errors(self, hours=24):
        cutoff = time.time() - (hours * 3600)
        self.errors = [e for e in self.errors if e.get("timestamp", "") > cutoff]

error_tracker = ErrorTracker()

def track_error(error_type: str):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_details = traceback.format_exc()
                error_tracker.log_error(error_type, str(e), error_details[:200])
                raise
        return wrapper
    return decorator

def log_execution_time(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{func.__name__} executed in {duration:.2f}s")
        return result
    return wrapper

class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window = window_seconds
        self.calls = []
    
    def is_allowed(self) -> bool:
        now = time.time()
        self.calls = [t for t in self.calls if now - t < self.window]
        
        if len(self.calls) >= self.max_calls:
            return False
        
        self.calls.append(now)
        return True
    
    def get_remaining(self) -> int:
        now = time.time()
        self.calls = [t for t in self.calls if now - t < self.window]
        return max(0, self.max_calls - len(self.calls))

price_limiter = RateLimiter(max_calls=10, window_seconds=60)
llm_limiter = RateLimiter(max_calls=5, window_seconds=60)

def check_health():
    from services.news_fetcher import _price_cache
    import requests
    
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_age": time.time() - _price_cache.get("timestamp", 0),
        "errors": error_tracker.get_error_summary()
    }
    
    try:
        r = requests.get("https://api.coingecko.com/api/v3/ping", timeout=3)
        health["coingecko"] = "ok" if r.status_code == 200 else "error"
    except:
        health["coingecko"] = "offline"
    
    return health