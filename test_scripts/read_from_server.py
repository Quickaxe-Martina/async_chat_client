import argparse
import asyncio
import datetime
import logging
import sys
from contextlib import asynccontextmanager
from typing import ContextManager

import aiofiles


@asynccontextmanager
async def open_connection(host: str, port: int) -> ContextManager:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


async def open_and_read_from_connection(host: str, port: int, file: str):
    async with open_connection(host=host, port=port) as (reader, writer):
        async with aiofiles.open(file, mode="a", encoding="UTF8") as f:
            data = await reader.readline()
            while data:
                line = f'[{datetime.datetime.now().strftime("%d-%m-%Y %H:%M")}] {data.decode()}'
                logging.debug(line)
                await f.write(line)
                data = await reader.readline()


async def open_and_read_from_connection_with_retry(
    host: str, port: int, file: str, delay: int = 5
):
    while True:
        try:
            await open_and_read_from_connection(host, port, file)
            break
        except Exception as e:
            logging.error(f"Error: {e}. Retrying in {delay} seconds...")
            await asyncio.sleep(delay)


def parse_args() -> tuple:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--hosts",
        nargs="+",
        required=True,
        help="Список хостов",
    )
    parser.add_argument(
        "--ports",
        nargs="+",
        required=True,
        type=int,
        help="Список портов",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        required=True,
        help="Список файлов куда будут писаться сообщения",
    )

    args = parser.parse_args()
    if len(args.hosts) != len(args.ports) or len(args.hosts) != len(args.files):
        logging.error(
            "Ошибка: количество хостов, портов и токенов должно быть одинаковым."
        )
        sys.exit(1)
    return args.hosts, args.ports, args.files


async def main():
    logging.basicConfig(level=logging.DEBUG)
    hosts, ports, files = parse_args()
    pending = []
    for host, port, file in zip(hosts, ports, files):
        task = asyncio.create_task(
            open_and_read_from_connection(
                host=host,
                port=port,
                file=file,
            )
        )
        pending.append(task)

    while pending:
        done, pending = await asyncio.wait(pending, timeout=5)
        logging.debug(f"Число завершившихся задач: {len(done)}")
        logging.debug(f"Число ожидающих задач: {len(pending)}")
        for done_task in done:
            if done_task.exception() is None:
                logging.debug(done_task.result())
            else:
                logging.error(
                    "При выполнении запроса возникло исключение",
                    exc_info=done_task.exception(),
                )


if __name__ == "__main__":
    asyncio.run(main())
