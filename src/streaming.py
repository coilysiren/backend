import asyncio
import typing


async def testing() -> typing.AsyncGenerator[str, None]:
    for i in range(100):
        await asyncio.sleep(1)
        yield f"Hello, world! {i}\n"
