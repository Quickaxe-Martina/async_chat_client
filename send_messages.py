import argparse
import asyncio
import json
import logging
import sys
from logging import config as logging_config

from logging_config import LOGGING
from tools import open_connection

logging_config.dictConfig(LOGGING)


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


async def read_line(
    reader: asyncio.StreamReader,
) -> str:
    data = await reader.readline()
    return data.decode().strip()


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


async def main(
    host: str,
    port: int,
    token: str,
    nickname: str,
    messages: list[str],
) -> None:
    async with open_connection(host=host, port=port) as (reader, writer):
        line: str = await read_line(reader=reader)
        logging.debug(f"{line=}")
        if (
            "Enter your personal hash"
            in line  # "Hello %username%! Enter your personal hash or leave it empty to create new account."
        ):
            if nickname:
                data = await register(writer=writer, reader=reader, nickname=nickname)
            elif token:
                data = await authorise(writer=writer, reader=reader, token=f"{token}\n")
            logging.debug(data)

            pending = []
            for m in messages:
                task = asyncio.create_task(submit_message(writer, f"{m}\n"))
                pending.append(task)
            while pending:
                done, pending = await asyncio.wait(pending, timeout=5)
                logging.info(f"Число завершившихся задач: {len(done)}")
                logging.info(f"Число ожидающих задач: {len(pending)}")
                for done_task in done:
                    if done_task.exception() is None:
                        logging.debug(done_task.result())
                    else:
                        logging.error(
                            "При выполнении запроса возникло исключение",
                            exc_info=done_task.exception(),
                        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        required=True,
        help="Хост",
    )
    parser.add_argument(
        "--port",
        required=True,
        type=int,
        help="Порт",
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
    parser.add_argument(
        "--messages",
        nargs="+",
        required=True,
        type=str,
        help="Сообщения бля отправки",
    )

    args = parser.parse_args()
    if not args.token and not args.nickname:
        logging.error("Должен быть указан либо токен либо никнейм")
        sys.exit(1)

    asyncio.run(
        main(
            host=args.host,
            port=args.port,
            token=args.token,
            nickname=args.nickname,
            messages=args.messages,
        )
    )
