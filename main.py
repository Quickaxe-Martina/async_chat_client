import argparse
import asyncio
import datetime
import json
import logging
import sys
from logging import config as logging_config

from db import create_table, put_all_messages_in_queue, save_msgs_to_db
from gui import gui
from logging_config import LOGGING
from tools import open_connection, read_line

logging_config.dictConfig(LOGGING)


async def read_msgs(
    host: str,
    port: int,
    messages_queue: asyncio.Queue,
    save_messages_queue: asyncio.Queue,
):
    async with open_connection(host=host, port=port) as (reader, writer):
        data = await read_line(reader=reader)
        while data:
            dt = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
            line = f"[{dt}] {data}"
            logging.debug(line)
            messages_queue.put_nowait(line)
            save_messages_queue.put_nowait((dt, data))
            data = await read_line(reader=reader)


async def submit_message(
    writer: asyncio.StreamWriter,
    text: str,
) -> None:
    logging.debug(f"{text=}")
    writer.write(f"{text}\n".encode())
    await writer.drain()


async def process_message(
    writer: asyncio.StreamWriter,
    reader: asyncio.StreamReader,
    message: str,
    error_message: str,
) -> dict:
    await submit_message(writer, message)
    try:
        data = json.loads(await reader.readline())
    except json.JSONDecodeError:
        logging.error("Received malformed data during processing.")
        sys.exit(1)
    logging.debug(f"{data=}")
    if data is None:
        logging.error(f"Failed to process: {error_message}")
        raise ValueError(error_message)
    return data


async def authorise(
    writer: asyncio.StreamWriter,
    reader: asyncio.StreamReader,
    token: str,
) -> dict:
    return await process_message(
        writer=writer,
        reader=reader,
        message=f"{token}",
        error_message="Failed to authorise: Broken token.",
    )


async def register(
    writer: asyncio.StreamWriter,
    reader: asyncio.StreamReader,
    nickname: str,
) -> dict:
    await submit_message(writer, "")
    logging.debug(await reader.readline())
    return await process_message(
        writer=writer,
        reader=reader,
        message=nickname,
        error_message="Failed to register: Register error.",
    )


async def send_msgs(
    host: str,
    port: int,
    nickname: str,
    token: str,
    sending_queue: asyncio.Queue,
):
    async with open_connection(host=host, port=port) as (reader, writer):
        line: str = await read_line(reader=reader)
        logging.debug(f"{line=}")
        if (
            "Enter your personal hash"
            in line  # "Hello %username%! Enter your personal hash or leave it empty to create new account."
        ):
            if token:
                data = await authorise(writer=writer, reader=reader, token=f"{token}\n")
            elif nickname:
                data = await register(writer=writer, reader=reader, nickname=nickname)
            logging.debug(f"{data=}")
        while True:
            text = await sending_queue.get()
            await submit_message(writer, f"{text}\n")


def parse_args() -> tuple:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--read_host",
        required=True,
        help="Хост для чтения сообщений",
    )
    parser.add_argument(
        "--read_port",
        required=True,
        type=int,
        help="Порт для чтения сообщений",
    )

    parser.add_argument(
        "--write_host",
        required=True,
        help="Хост для отправки сообщений",
    )
    parser.add_argument(
        "--write_port",
        required=True,
        type=int,
        help="Порт для отправки сообщений",
    )

    parser.add_argument(
        "--token",
        required=False,
        type=str,
        help="Токен для авторизации",
    )
    parser.add_argument(
        "--nickname",
        required=False,
        type=str,
        help="Никнейм для регистрации",
    )

    args = parser.parse_args()
    if not args.token and not args.nickname:
        logging.error("Должен быть указан либо токен либо никнейм")
        sys.exit(1)

    return (
        args.read_host,
        args.read_port,
        args.write_host,
        args.write_port,
        args.token,
        args.nickname,
    )


async def main():
    read_host, read_port, write_host, write_port, token, nickname = parse_args()

    messages_queue = asyncio.Queue()
    save_messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    await create_table()
    await put_all_messages_in_queue(queue=messages_queue)

    await asyncio.gather(
        gui.draw(messages_queue, sending_queue, status_updates_queue),
        read_msgs(
            host=read_host,
            port=read_port,
            messages_queue=messages_queue,
            save_messages_queue=save_messages_queue,
        ),
        save_msgs_to_db(queue=save_messages_queue),
        send_msgs(
            host=write_host,
            port=write_port,
            token=token,
            nickname=nickname,
            sending_queue=sending_queue,
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())
