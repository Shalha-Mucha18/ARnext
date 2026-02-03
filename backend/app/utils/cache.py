import json
import hashlib
from functools import wraps
from typing import Callable
import redis.asyncio as redis
from core.config import settings

# Initialize Redis client
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def cache_response(expire: int = 300):
    """
    Cache decorator for FastAPI endpoints.
    
    Args:
        expire: Cache expiration in seconds (default 5 minutes)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = _generate_cache_key(func.__name__, args, kwargs)
            
            # Try to get from cache
            try:
                cached = await redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                # If Redis fails, silently continue to DB (fail-safe)
                pass
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            try:
                if hasattr(result, "model_dump_json"):
                    data_to_store = result.model_dump_json()
                    pass 
                
                # Simple serialization for standard dicts/lists
                await redis_client.setex(
                    cache_key,
                    expire,
                    json.dumps(result, default=str)
                )
            except Exception:
                pass
                
            return result
        return wrapper
    return decorator

def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate unique cache key based on function and arguments"""
    # Sort kwargs to ensure consistent keys
    key_part = f"{func_name}:{args}:{sorted(kwargs.items())}"
    return f"cache:{hashlib.md5(key_part.encode()).hexdigest()}"

async def invalidate_cache(pattern: str):
    """Invalidate cache entries matching a pattern"""
    try:
        keys = await redis_client.keys(f"cache:{pattern}*")
        if keys:
            await redis_client.delete(*keys)
    except Exception:
        pass
