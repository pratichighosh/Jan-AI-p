import redis.asyncio as redis
import os
import json
import structlog
from typing import Optional, Any

log = structlog.get_logger()

# Redis connection
redis_client: Optional[redis.Redis] = None

# Cache TTLs
TRANSLATION_CACHE_TTL = 86400  # 24 hours
SESSION_TTL = 3600  # 1 hour
OCR_CACHE_TTL = 3600  # 1 hour


async def connect_to_redis():
    """Initialize Redis connection on app startup."""
    global redis_client
    
    redis_uri = os.getenv("REDIS_URI", "redis://localhost:6379")
    
    try:
        redis_client = redis.from_url(
            redis_uri,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Test connection
        await redis_client.ping()
        log.info("redis.connected", uri=redis_uri.split('@')[-1])
    except Exception as e:
        log.exception("redis.connection_failed", error=str(e))
        raise


async def close_redis_connection():
    """Close Redis connection on app shutdown."""
    global redis_client
    if redis_client:
        await redis_client.close()
        log.info("redis.disconnected")


# ============================================================================
# Translation Cache
# ============================================================================

async def get_cached_translation(
    text: str,
    source_lang: str,
    target_lang: str
) -> Optional[str]:
    """Get cached translation if exists."""
    cache_key = f"trans:{source_lang}:{target_lang}:{hash(text)}"
    
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            log.info("redis.translation_cache_hit", key=cache_key)
            return cached
    except Exception as e:
        log.warning("redis.get_failed", error=str(e))
    
    return None


async def cache_translation(
    text: str,
    source_lang: str,
    target_lang: str,
    translated_text: str
) -> bool:
    """Cache translation result."""
    cache_key = f"trans:{source_lang}:{target_lang}:{hash(text)}"
    
    try:
        await redis_client.setex(
            cache_key,
            TRANSLATION_CACHE_TTL,
            translated_text
        )
        log.info("redis.translation_cached", key=cache_key)
        return True
    except Exception as e:
        log.warning("redis.cache_failed", error=str(e))
        return False


# ============================================================================
# Session Management
# ============================================================================

async def save_session(session_id: str, session_data: dict) -> bool:
    """Save user session data."""
    cache_key = f"session:{session_id}"
    
    try:
        await redis_client.setex(
            cache_key,
            SESSION_TTL,
            json.dumps(session_data)
        )
        return True
    except Exception as e:
        log.warning("redis.session_save_failed", error=str(e))
        return False


async def get_session(session_id: str) -> Optional[dict]:
    """Retrieve session data."""
    cache_key = f"session:{session_id}"
    
    try:
        data = await redis_client.get(cache_key)
        if data:
            return json.loads(data)
    except Exception as e:
        log.warning("redis.session_get_failed", error=str(e))
    
    return None


async def delete_session(session_id: str) -> bool:
    """Delete session data."""
    cache_key = f"session:{session_id}"
    
    try:
        await redis_client.delete(cache_key)
        return True
    except Exception as e:
        log.warning("redis.session_delete_failed", error=str(e))
        return False


# ============================================================================
# Generic Cache Operations
# ============================================================================

async def set_cache(key: str, value: Any, ttl: int = 3600) -> bool:
    """Set cache value with TTL."""
    try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        await redis_client.setex(key, ttl, value)
        return True
    except Exception as e:
        log.warning("redis.set_cache_failed", key=key, error=str(e))
        return False


async def get_cache(key: str) -> Optional[Any]:
    """Get cache value."""
    try:
        value = await redis_client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
    except Exception as e:
        log.warning("redis.get_cache_failed", key=key, error=str(e))
    
    return None


async def delete_cache(key: str) -> bool:
    """Delete cache entry."""
    try:
        await redis_client.delete(key)
        return True
    except Exception as e:
        log.warning("redis.delete_cache_failed", key=key, error=str(e))
        return False


async def increment_counter(key: str, amount: int = 1) -> int:
    """Increment counter (useful for rate limiting)."""
    try:
        return await redis_client.incrby(key, amount)
    except Exception as e:
        log.warning("redis.increment_failed", key=key, error=str(e))
        return 0