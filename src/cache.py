import json
import logging
import os
import sys
import typing
import urllib.parse

import redis as _redis
import requests  # type: ignore
import structlog

from . import telemetry

_telemetry = telemetry.Telemetry()
cache: typing.Dict[str, any] = {}
logger = structlog.get_logger()
logging.basicConfig(stream=sys.stdout)

redis_env = os.environ.get("REDISCLOUD_URL")
redis_url = urllib.parse.urlparse(redis_env)
redis = _redis.Redis(host=redis_url.hostname, port=redis_url.port, password=redis_url.password)


def get_or_return_cached_request(prefix: str, suffix: str, func: typing.Callable[[], requests.Response]) -> dict:
    key = f"{prefix}-{suffix}"
    expiry = 86400  # 1 day
    with _telemetry.tracer.start_as_current_span("get-or-return-cached-request") as span:
        span.set_attribute("key", key)
        span.set_attribute("prefix", prefix)
        span.set_attribute("suffix", suffix)

        output = redis.get(key)
        if output is not None:
            span.set_attribute("adjective", "hit")
            logger.info("request-cache", adjective="hit", prefix=prefix, suffix=suffix, key=key)
            output = json.loads(output)
            return output
        else:
            span.set_attribute("adjective", "miss")
            response = func()
            span.set_attribute("http.status_code", "response.status_code")
            if response.status_code >= 500:
                logger.error(
                    "request-cache",
                    adjective="error",
                    prefix=prefix,
                    suffix=suffix,
                    key=key,
                    status_code=response.status_code,
                )
                raise requests.RequestException(f"Request failed with status code {response.status_code}")
            try:
                output_json = response.json()
            except requests.exceptions.JSONDecodeError as exc:
                logger.exception(
                    "request-cache",
                    adjective="error",
                    prefix=prefix,
                    suffix=suffix,
                    key=key,
                    status_code=response.status_code,
                    exc=exc,
                )
                raise exc
            output_str = json.dumps(output_json)
            redis.set(key, output_str, ex=expiry)
            logger.info(
                "request-cache",
                adjective="miss",
                prefix=prefix,
                suffix=suffix,
                key=key,
                status_code=response.status_code,
            )
            return output_json


def get_or_return_cached(prefix: str, suffix: str, func: typing.Callable) -> typing.Any:
    key = f"{prefix}-{suffix}"
    expiry = 86400  # 1 day
    with _telemetry.tracer.start_as_current_span("get-or-return-cached") as span:
        span.set_attribute("key", key)
        span.set_attribute("prefix", prefix)
        span.set_attribute("suffix", suffix)

        output = redis.get(key)
        if output is not None:
            span.set_attribute("adjective", "hit")
            logger.info("cache", adjective="hit", prefix=prefix, suffix=suffix, key=key)
            output = json.loads(output)
            return output
        else:
            span.set_attribute("adjective", "miss")
            output = func()
            output_json = json.dumps(output)
            redis.set(key, output_json, ex=expiry)
            logger.info("cache", adjective="miss", prefix=prefix, suffix=suffix, key=key)
            return output
