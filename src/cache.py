import logging
import sys
import typing

import structlog

from . import telemetry

_telemetry = telemetry.Telemetry()
cache: typing.Dict[str, any] = {}
logger = structlog.get_logger()
logging.basicConfig(stream=sys.stdout)


def get_or_return_cache(prefix: str, suffix: str, func: typing.Callable) -> typing.Any:
    key = f"{prefix}-{suffix}"
    with _telemetry.tracer.start_as_current_span("get-or-return-cache") as span:
        span.set_attribute("key", key)
        span.set_attribute("prefix", prefix)
        span.set_attribute("suffix", suffix)

        if key in cache:
            span.set_attribute("adjective", "hit")
            logger.info("cache", adjective="hit", prefix=prefix, suffix=suffix, key=key)
            return cache[key]
        else:
            span.set_attribute("adjective", "miss")
            logger.info("cache", adjective="miss", prefix=prefix, suffix=suffix, key=key)
            result = func()
            cache[key] = result
            return result
