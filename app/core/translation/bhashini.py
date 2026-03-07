import httpx
import asyncio
import os
import structlog
from dotenv import load_dotenv
import json

from app.db.redis import get_redis_client


load_dotenv()
log = structlog.get_logger()

BHASHINI_INFERENCE_URL = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
API_KEY = os.getenv("BHASHINI_API_KEY")
USER_ID = os.getenv("BHASHINI_USER_ID")
PIPELINE_ID = os.getenv("BHASHINI_PIPELINE_ID", "64392f96daac500b55c543cd")

MAX_RETRIES = 3
BACKOFF_SECONDS = [1, 2, 4]


async def _call_bhashini_translate(
    text: str,
    source_lang: str,
    target_lang: str,
) -> dict:
    """
    Low-level call to Bhashini translation API with retries.
    """
    payload = {
        "pipelineTasks": [
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": source_lang,
                        "targetLanguage": target_lang,
                    },
                    "serviceId": "",
                },
            }
        ],
        "inputData": {
            "input": [{"source": text}],
            "audio": [],
        },
    }

    headers = {
        "Authorization": API_KEY,
        "userID": USER_ID,
        "ulcaApiKey": API_KEY,
        "Content-Type": "application/json",
    }

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            log.info(
                "bhashini.translate.attempt",
                attempt=attempt + 1,
                source=source_lang,
                target=target_lang,
            )

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    BHASHINI_INFERENCE_URL,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

                translated = data["pipelineResponse"][0]["output"][0]["target"]

                log.info("bhashini.translate.success", attempt=attempt + 1)
                return {
                    "original_text": text,
                    "translated_text": translated,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "attempts": attempt + 1,
                }

        except (httpx.HTTPError, KeyError, IndexError) as e:
            last_error = e
            log.warning(
                "bhashini.translate.failed",
                attempt=attempt + 1,
                error=str(e),
            )

            if attempt < MAX_RETRIES - 1:
                wait = BACKOFF_SECONDS[attempt]
                log.info("bhashini.translate.retry", wait_seconds=wait)
                await asyncio.sleep(wait)

    log.error(
        "bhashini.translate.all_retries_failed",
        error=str(last_error),
    )
    raise Exception(
        f"Bhashini translation failed after {MAX_RETRIES} attempts: {last_error}"
    )


async def translate(text: str, source_lang: str, target_lang: str) -> dict:
    """
    Translate text using Bhashini API with Redis caching.
    """
    redis_client = get_redis_client()

    # Build stable cache key from parameters + text
    key_payload = {
        "src": source_lang,
        "tgt": target_lang,
        "text": text,
    }
    cache_key = f"bhashini:trans:{hash(json.dumps(key_payload, sort_keys=True))}"

    # Try cache first
    cached = redis_client.get(cache_key)
    if cached:
        try:
            result = json.loads(cached)
            log.info(
                "bhashini.translate.cache_hit",
                source=source_lang,
                target=target_lang,
            )
            return result
        except json.JSONDecodeError:
            log.warning("bhashini.translate.cache_corrupt")
            # fall through to API call

    # Cache miss → call Bhashini
    result = await _call_bhashini_translate(text, source_lang, target_lang)

    # Store in Redis for 24 hours
    try:
        redis_client.setex(
            cache_key,
            86400,  # 24h
            json.dumps(result, ensure_ascii=False),
        )
        log.info(
            "bhashini.translate.cache_store",
            source=source_lang,
            target=target_lang,
        )
    except Exception as e:
        log.warning("bhashini.translate.cache_store_failed", error=str(e))

    return result


async def simplify_bureaucratic(text: str, language: str) -> str:
    """
    Use Bhashini to simplify bureaucratic language.

    For now, this calls translate() with same source and target language,
    but benefits from Redis caching so repeated simplifications of the
    same text are fast.
    """
    simplified = await translate(
        text=text,
        source_lang=language,
        target_lang=language,
    )
    return simplified["translated_text"]
