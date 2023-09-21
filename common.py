import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

executor = ThreadPoolExecutor()
# todo: use nicegui.run.io_bound when it's released
async def io_bound(func, *args, **kwargs):
    return await asyncio.get_running_loop().run_in_executor(executor, partial(func, *args, **kwargs))