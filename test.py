import asyncio
import time


async def say_hello():
    await asyncio.sleep(1)
    print("Hello")


async def say_world():
    await asyncio.sleep(2)
    print("World")


async def main():
    await asyncio.gather(say_world(), say_hello())


asyncio.run(main())  # Python 3.7+
