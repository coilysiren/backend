import asyncio
import dataclasses
import enum
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
cache: dict[str, typing.Any] = {}
logger = structlog.get_logger()
logging.basicConfig(stream=sys.stdout)

redis_env = os.environ.get("REDISCLOUD_URL")
redis_url = urllib.parse.urlparse(redis_env)
redis = _redis.Redis(
    host=redis_url.hostname,
    port=redis_url.port,
    password=redis_url.password,
    socket_timeout=3,
)


class TaskDataStatus(enum.Enum):
    in_progress = "in_progress"
    failed = "failed"
    completed = "completed"


@dataclasses.dataclass
class AsyncTaskData:
    task_id: str
    task_status: TaskDataStatus
    task_data: typing.Optional[typing.Any]

    def to_dict(self) -> dict:
        return {"task_id": self.task_id, "task_status": self.task_status.value, "task_data": self.task_data}

    @classmethod
    def from_dict(cls, data: dict) -> "AsyncTaskData":
        return cls(
            task_id=data["task_id"], task_status=TaskDataStatus(data["task_status"]), task_data=data["task_data"]
        )


def delete_keys(suffix: str) -> None:
    # Delete keys matching a pattern
    for key in redis.scan_iter(f"*{suffix}"):
        redis.delete(key)
        logger.info("cache", adjective="delete", key=key.decode("utf-8"))


async def get_or_return_cached_request(prefix: str, suffix: str, func: typing.Callable[[], requests.Response]) -> dict:
    key = f"{prefix}-{suffix}"
    expiry = 86400  # 1 day
    with _telemetry.tracer.start_as_current_span("get-or-return-cached-request") as span:
        span.set_attribute("key", key)
        span.set_attribute("prefix", prefix)
        span.set_attribute("suffix", suffix)

        output = None
        try:
            output = redis.get(key)
        except Exception as exc:
            logger.exception(
                "cache",
                adjective="error",
                prefix=prefix,
                suffix=suffix,
                key=key,
                exc=exc,
            )

        if output is not None:
            span.set_attribute("adjective", "hit")
            logger.info("cache", adjective="hit", prefix=prefix, suffix=suffix, key=key)
            output = json.loads(output)
            return output
        else:
            span.set_attribute("adjective", "miss")
            response = await asyncio.to_thread(func)
            span.set_attribute("http.status_code", "response.status_code")
            if response.status_code >= 500:
                logger.error(
                    "cache",
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

            try:
                redis.set(key, output_str, ex=expiry)
            except Exception as exc:
                pass

            logger.info(
                "request-cache",
                adjective="miss",
                prefix=prefix,
                suffix=suffix,
                key=key,
                status_code=response.status_code,
            )
            return output_json


async def get_or_return_cached(prefix: str, suffix: str, func: typing.Callable) -> typing.Any:
    key = f"{prefix}-{suffix}"
    expiry = 86400  # 1 day
    with _telemetry.tracer.start_as_current_span("get-or-return-cached") as span:
        span.set_attribute("key", key)
        span.set_attribute("prefix", prefix)
        span.set_attribute("suffix", suffix)

        output = None

        try:
            output = redis.get(key)
        except Exception as exc:
            logger.exception(
                "cache",
                adjective="error",
                prefix=prefix,
                suffix=suffix,
                key=key,
                exc=exc,
            )

        if output is not None:
            span.set_attribute("adjective", "hit")
            logger.info("cache", adjective="hit", prefix=prefix, suffix=suffix, key=key)
            output = json.loads(output)
            return output
        else:
            span.set_attribute("adjective", "miss")
            output = await asyncio.to_thread(func)
            output_json = json.dumps(output)

            try:
                redis.set(key, output_json, ex=expiry)
            except Exception as exc:
                pass

            logger.info("cache", adjective="miss", prefix=prefix, suffix=suffix, key=key)
            return output


def create_or_return_async_task_data(prefix: str, suffix: str) -> AsyncTaskData:
    key = f"{prefix}-{suffix}"
    expiry = 86400  # 1 day

    try:
        task_data = redis.get(key)

        if task_data is None:
            task_data = AsyncTaskData(task_id=key, task_status=TaskDataStatus.in_progress, task_data=None)
            redis.set(key, json.dumps(task_data.to_dict()), ex=expiry)
            return task_data

        else:
            task_data = json.loads(task_data)
            return AsyncTaskData.from_dict(task_data)

    except Exception as exc:
        logger.exception(
            "cache",
            adjective="error",
            prefix=prefix,
            suffix=suffix,
        )
        raise exc


def get_async_task_data(prefix: str, suffix: str) -> AsyncTaskData:
    key = f"{prefix}-{suffix}"
    task_data = redis.get(key)
    return AsyncTaskData.from_dict(json.loads(task_data))


def set_async_task_data(prefix: str, suffix: str, task_data: AsyncTaskData) -> None:
    key = f"{prefix}-{suffix}"
    expiry = 86400  # 1 day
    redis.set(key, json.dumps(task_data.to_dict()), ex=expiry)
