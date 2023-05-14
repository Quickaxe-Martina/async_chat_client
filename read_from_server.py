import argparse
import asyncio
import datetime
import sys

import aiofiles

from tools import open_connection


async def open_and_read_from_connection(host: str, port: int, file: str):
    async with open_connection(host=host, port=port) as (reader, writer):
        async with aiofiles.open(file, mode="a", encoding="UTF8") as f:
            data = await reader.readline()
            while data:
                line = f'[{datetime.datetime.now().strftime("%d-%m-%Y %H:%M")}] {data.decode()}'
                print(line)
                await f.write(line)
                data = await reader.readline()


async def main(hosts: list[str], ports: list[int], files: list[str]):
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
        print(f"Число завершившихся задач: {len(done)}")
        print(f"Число ожидающих задач: {len(pending)}")
        for done_task in done:
            print(await done_task)


if __name__ == "__main__":
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
        print("Ошибка: количество хостов, портов и токенов должно быть одинаковым.")
        sys.exit(1)

    asyncio.run(
        main(
            hosts=args.hosts,
            ports=args.ports,
            files=args.files,
        )
    )
