"""Exact-match answer cache in Upstash Redis. Key = SHA-256 of the normalised question."""
import hashlib
import json

import logfire
import redis

from querymesh import config

_client = (redis.Redis.from_url(config.REDIS_URL, decode_responses=True, socket_timeout=5)
           if config.REDIS_URL.startswith(("redis://", "rediss://")) else None)  # no URL = no cache


def cache_key(question: str) -> str:
    normalised = " ".join(question.lower().split())  # "What is RAG? " == "what  is rag?"
    digest = hashlib.sha256(f"{config.LLM_MODEL}|{normalised}".encode("utf-8")).hexdigest()
    return f"querymesh:answer:{digest}"


def get(question: str) -> dict | None:
    if _client is None:
        return None
    try:
        raw = _client.get(cache_key(question))
    except redis.RedisError as error:  # the cache must never break the app
        logfire.warn("cache read failed: {error}", error=str(error))
        return None
    return json.loads(raw) if raw else None


def put(question: str, result: dict) -> None:
    if _client is None:
        return
    try:
        _client.set(cache_key(question), json.dumps(result), ex=config.CACHE_TTL_SECONDS)
    except redis.RedisError as error:
        logfire.warn("cache write failed: {error}", error=str(error))
