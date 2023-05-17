import asyncio
from contextlib import asynccontextmanager
from typing import ContextManager


@asynccontextmanager
async def open_connection(host: str, port: int) -> ContextManager:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


async def read_line(
    reader: asyncio.StreamReader,
) -> str:
    data = await reader.readline()
    return data.decode().strip()
