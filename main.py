import argparse
import asyncio
from logging import config as logging_config
from tkinter import TclError

from db import create_table, put_all_messages_in_queue, save_msgs_to_db
from gui import gui
from logging_config import LOGGING
from msg import MessagesManager

logging_config.dictConfig(LOGGING)


def parse_args() -> dict:
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

    args = parser.parse_args()

    return {
        "read_host": args.read_host,
        "read_port": args.read_port,
        "write_host": args.write_host,
        "write_port": args.write_port,
    }


async def main():
    messages_queue = asyncio.Queue()
    save_messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()
    user_queue = asyncio.Queue()

    msg_manager = MessagesManager(
        messages_queue=messages_queue,
        save_messages_queue=save_messages_queue,
        sending_queue=sending_queue,
        status_updates_queue=status_updates_queue,
        watchdog_queue=watchdog_queue,
        user_queue=user_queue,
        **parse_args(),
    )

    await create_table()
    await put_all_messages_in_queue(queue=messages_queue)

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(
                gui.draw(
                    messages_queue=messages_queue,
                    sending_queue=sending_queue,
                    status_updates_queue=status_updates_queue,
                    user_queue=user_queue,
                )
            )
            tg.create_task(save_msgs_to_db(queue=save_messages_queue))
            tg.create_task(msg_manager.run())
    except (KeyboardInterrupt, gui.TkAppClosed, TclError, ExceptionGroup):
        pass


if __name__ == "__main__":
    asyncio.run(main())
