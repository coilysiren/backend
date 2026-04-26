import asyncio
import dataclasses
import enum
import json
import logging
import sys
import time
import typing

import requests  # type: ignore
import structlog

from . import telemetry

_telemetry = telemetry.Telemetry()
logger = structlog.get_logger()
logging.basicConfig(stream=sys.stdout)


_store: dict[str, tuple[float, str]] = {}


def _get(key: str) -> str | None:
    entry = _store.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if expires_at < time.time():
        _store.pop(key, None)
        return None
    return value


def _set(key: str, value: str, ex: int) -> None:
    _store[key] = (time.time() + ex, value)


class TaskDataStatus(enum.Enum):
    in_progress = "in_progress"
    failed = "failed"
    completed = "completed"


@dataclasses.dataclass
class AsyncTaskData:
    task_id: str
    task_status: TaskDataStatus
    task_data: typing.Any | None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_status": self.task_status.value,
            "task_data": self.task_data,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AsyncTaskData":
        return cls(
            task_id=data["task_id"],
            task_status=TaskDataStatus(data["task_status"]),
            task_data=data["task_data"],
        )


def delete_keys(suffix: str) -> None:
    for key in [k for k in _store if k.endswith(suffix)]:
        _store.pop(key, None)
        logger.info("cache", adjective="delete", key=key)


async def get_or_return_cached_request(
    prefix: str, suffix: str, func: typing.Callable[[], requests.Response]
) -> dict:
    key = f"{prefix}-{suffix}"
    expiry = 86400  # 1 day
    with _telemetry.tracer.start_as_current_span("get-or-return-cached-request") as span:
        span.set_attribute("key", key)
        span.set_attribute("prefix", prefix)
        span.set_attribute("suffix", suffix)

        output = _get(key)

        if output is not None:
            span.set_attribute("adjective", "hit")
            logger.info("cache", adjective="hit", prefix=prefix, suffix=suffix, key=key)
            return json.loads(output)
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
                raise requests.RequestException(
                    f"Request failed with status code {response.status_code}"
                )
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

            _set(key, json.dumps(output_json), ex=expiry)

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

        output = _get(key)

        if output is not None:
            span.set_attribute("adjective", "hit")
            logger.info("cache", adjective="hit", prefix=prefix, suffix=suffix, key=key)
            return json.loads(output)
        else:
            span.set_attribute("adjective", "miss")
            output = await asyncio.to_thread(func)
            _set(key, json.dumps(output), ex=expiry)
            logger.info("cache", adjective="miss", prefix=prefix, suffix=suffix, key=key)
            return output


def create_or_return_async_task_data(prefix: str, suffix: str) -> AsyncTaskData:
    key = f"{prefix}-{suffix}"
    expiry = 86400  # 1 day

    raw = _get(key)

    if raw is None:
        task_data = AsyncTaskData(
            task_id=key, task_status=TaskDataStatus.in_progress, task_data=None
        )
        _set(key, json.dumps(task_data.to_dict()), ex=expiry)
        return task_data

    return AsyncTaskData.from_dict(json.loads(raw))


def get_async_task_data(prefix: str, suffix: str) -> AsyncTaskData:
    key = f"{prefix}-{suffix}"
    raw = _get(key)
    if raw is None:
        raise KeyError(key)
    return AsyncTaskData.from_dict(json.loads(raw))


def set_async_task_data(prefix: str, suffix: str, task_data: AsyncTaskData) -> None:
    key = f"{prefix}-{suffix}"
    expiry = 86400  # 1 day
    _set(key, json.dumps(task_data.to_dict()), ex=expiry)
