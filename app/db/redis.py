import os
import json
import structlog
import redis
import redis.asyncio as aioredis
from typing import Optional, Any

log = structlog.get_logger()

# ── Config ────────────────────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB   = int(os.getenv("REDIS_DB", "0"))
REDIS_URI  = os.getenv("REDIS_URI", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

# ── TTLs ──────────────────────────────────────────────────────────────────────
TRANSLATION_CACHE_TTL = 86400   # 24 hours
SESSION_TTL           = 3600    # 1 hour
OCR_CACHE_TTL         = 3600    # 1 hour

# ── Sync client (used by bhashini.py) ────────────────────────────────────────
_sync_client: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    """Sync Redis client — used by bhashini translate cache."""
    global _sync_client
    if _sync_client is None:
        _sync_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True,
        )
    return _sync_client


# ── Async client (used by session / progress / cache helpers) ─────────────────
_async_client: Optional[aioredis.Redis] = None

async def get_async_redis_client() -> aioredis.Redis:
    """Async Redis client — used by async route handlers."""
    global _async_client
    if _async_client is None:
        _async_client = aioredis.from_url(
            REDIS_URI,
            encoding="utf-8",
            decode_responses=True,
        )
    return _async_client


async def connect_to_redis():
    """Test Redis connection on app startup."""
    try:
        client = await get_async_redis_client()
        await client.ping()
        log.info("redis.connected", host=REDIS_HOST, port=REDIS_PORT)
    except Exception as e:
        log.exception("redis.connection_failed", error=str(e))
        raise


async def close_redis_connection():
    """Close async Redis connection on app shutdown."""
    global _async_client
    if _async_client:
        await _async_client.close()
        log.info("redis.disconnected")


# ── Translation cache ─────────────────────────────────────────────────────────
async def get_cached_translation(
    text: str,
    source_lang: str,
    target_lang: str,
) -> Optional[str]:
    cache_key = f"trans:{source_lang}:{target_lang}:{hash(text)}"
    try:
        client = await get_async_redis_client()
        cached = await client.get(cache_key)
        if cached:
            log.info("redis.translation_cache_hit")
            return cached
    except Exception as e:
        log.warning("redis.get_failed", error=str(e))
    return None


async def cache_translation(
    text: str,
    source_lang: str,
    target_lang: str,
    translated_text: str,
) -> bool:
    cache_key = f"trans:{source_lang}:{target_lang}:{hash(text)}"
    try:
        client = await get_async_redis_client()
        await client.setex(cache_key, TRANSLATION_CACHE_TTL, translated_text)
        log.info("redis.translation_cached")
        return True
    except Exception as e:
        log.warning("redis.cache_failed", error=str(e))
        return False


# ── Session management ────────────────────────────────────────────────────────
async def save_session(session_id: str, session_data: dict) -> bool:
    try:
        client = await get_async_redis_client()
        await client.setex(
            f"session:{session_id}",
            SESSION_TTL,
            json.dumps(session_data),
        )
        return True
    except Exception as e:
        log.warning("redis.session_save_failed", error=str(e))
        return False


async def get_session(session_id: str) -> Optional[dict]:
    try:
        client = await get_async_redis_client()
        data = await client.get(f"session:{session_id}")
        if data:
            return json.loads(data)
    except Exception as e:
        log.warning("redis.session_get_failed", error=str(e))
    return None


async def delete_session(session_id: str) -> bool:
    try:
        client = await get_async_redis_client()
        await client.delete(f"session:{session_id}")
        return True
    except Exception as e:
        log.warning("redis.session_delete_failed", error=str(e))
        return False


# ── Generic cache operations ──────────────────────────────────────────────────
async def set_cache(key: str, value: Any, ttl: int = 3600) -> bool:
    try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        client = await get_async_redis_client()
        await client.setex(key, ttl, value)
        return True
    except Exception as e:
        log.warning("redis.set_cache_failed", key=key, error=str(e))
        return False


async def get_cache(key: str) -> Optional[Any]:
    try:
        client = await get_async_redis_client()
        value = await client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
    except Exception as e:
        log.warning("redis.get_cache_failed", key=key, error=str(e))
    return None


async def delete_cache(key: str) -> bool:
    try:
        client = await get_async_redis_client()
        await client.delete(key)
        return True
    except Exception as e:
        log.warning("redis.delete_cache_failed", key=key, error=str(e))
        return False


async def increment_counter(key: str, amount: int = 1) -> int:
    try:
        client = await get_async_redis_client()
        return await client.incrby(key, amount)
    except Exception as e:
        log.warning("redis.increment_failed", key=key, error=str(e))
        return 0
