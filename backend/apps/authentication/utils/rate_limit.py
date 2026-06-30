import logging
from typing import Optional
from django.core.cache import cache

logger = logging.getLogger(__name__)

class RateLimitException(Exception):
    pass

class RateLimiter:
    """
    Enterprise Redis-backed rate limiter to prevent brute-force and credential stuffing.
    """
    
    @classmethod
    def check_rate_limit(cls, action: str, identifier: str, max_attempts: int = 5, lockout_minutes: int = 15) -> None:
        """
        Checks if the action has exceeded the maximum attempts.
        Raises RateLimitException if locked out.
        """
        key = f"ratelimit:{action}:{identifier}"
        attempts = cache.get(key, 0)
        
        if attempts >= max_attempts:
            logger.warning(f"Rate limit exceeded for {action} on {identifier}")
            raise RateLimitException(f"Too many attempts. Please try again in {lockout_minutes} minutes.")
            
    @classmethod
    def record_attempt(cls, action: str, identifier: str, lockout_minutes: int = 15) -> None:
        """
        Records a failed attempt and increments the counter.
        """
        key = f"ratelimit:{action}:{identifier}"
        try:
            cache.incr(key)
        except ValueError:
            # If key does not exist
            cache.set(key, 1, timeout=lockout_minutes * 60)
            
    @classmethod
    def clear_attempts(cls, action: str, identifier: str) -> None:
        """
        Clears attempts upon successful completion of the action.
        """
        key = f"ratelimit:{action}:{identifier}"
        cache.delete(key)
