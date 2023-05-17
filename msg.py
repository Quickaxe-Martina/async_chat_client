import asyncio
import datetime
import json
import logging
import sys
from tkinter import messagebox

from async_timeout import timeout

from gui import gui
from gui.gui import NicknameReceived, TokenReceived
from tools import open_connection, read_line


class MessagesManager:
    def __init__(
        self,
        messages_queue: asyncio.Queue,
        save_messages_queue: asyncio.Queue,
        sending_queue: asyncio.Queue,
        status_updates_queue: asyncio.Queue,
        watchdog_queue: asyncio.Queue,
        user_queue: asyncio.Queue,
        read_host: str,
        read_port: int,
        write_host: str,
        write_port: int,
    ):
        self.messages_queue = messages_queue
        self.save_messages_queue = save_messages_queue
        self.sending_queue = sending_queue
        self.status_updates_queue = status_updates_queue
        self.watchdog_queue = watchdog_queue
        self.user_queue = user_queue
        self.read_host = read_host
        self.read_port = read_port
        self.write_host = write_host
        self.write_port = write_port
        self.token = None
        self.nickname = None

    @staticmethod
    async def submit_message(
        writer: asyncio.StreamWriter,
        text: str,
    ) -> None:
        logging.debug(f"{text=}")
        writer.write(f"{text}\n".encode())
        await writer.drain()

    async def run(self):
        delay = 5
        while True:
            try:
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.read_msgs())
                    tg.create_task(self.send_msgs())
                    tg.create_task(self.watch_for_connection())
                    tg.create_task(self.ping_pong())
                    tg.create_task(self.checking_user_credentials_changes())
            except ExceptionGroup:
                logging.error("Connection error")
                self.status_updates_queue.put_nowait(
                    gui.ReadConnectionStateChanged.INITIATED
                )
                self.status_updates_queue.put_nowait(
                    gui.SendingConnectionStateChanged.INITIATED
                )
                await asyncio.sleep(delay)

    async def read_msgs(self):
        async with open_connection(host=self.read_host, port=self.read_port) as (
            reader,
            writer,
        ):
            self.status_updates_queue.put_nowait(
                gui.ReadConnectionStateChanged.ESTABLISHED
            )
            data = await read_line(reader=reader)
            while data:
                self.watchdog_queue.put_nowait("New message in chat")
                dt = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
                line = f"[{dt}] {data}"
                logging.debug(line)
                self.messages_queue.put_nowait(line)
                self.save_messages_queue.put_nowait((dt, data))
                data = await read_line(reader=reader)

    async def send_msgs(self):
        async with open_connection(host=self.write_host, port=self.write_port) as (
            reader,
            writer,
        ):
            line: str = await read_line(reader=reader)
            logging.debug(f"{line=}")
            if (
                "Enter your personal hash"
                in line  # "Hello %username%! Enter your personal hash or leave it empty to create new account."
            ):
                while self.token is None and self.nickname is None:
                    await asyncio.sleep(3)

                if self.token:
                    data = await self.authorise(
                        writer=writer,
                        reader=reader,
                    )
                elif self.nickname:
                    data = await self.register(
                        writer=writer,
                        reader=reader,
                    )
                logging.debug(f"{data=}")
                self.status_updates_queue.put_nowait(
                    gui.SendingConnectionStateChanged.ESTABLISHED
                )
                self.status_updates_queue.put_nowait(
                    gui.NicknameReceived(data["nickname"])
                )
                self.status_updates_queue.put_nowait(
                    gui.TokenReceived(data["account_hash"])
                )
            while True:
                text = await self.sending_queue.get()
                await self.submit_message(writer, f"{text}\n")
                self.watchdog_queue.put_nowait("Message sent")

    async def watch_for_connection(self):
        timeout_seconds = 3
        while True:
            try:
                async with timeout(timeout_seconds):
                    msg = await self.watchdog_queue.get()
                    logging.info(f"Connection is alive. {msg}")
            except TimeoutError:
                logging.warning(f"{timeout_seconds}s timeout is elapsed")
                raise ConnectionError

    async def ping_pong(self):
        timeout_seconds = 3
        while True:
            self.sending_queue.put_nowait("")
            await asyncio.sleep(timeout_seconds)

    async def checking_user_credentials_changes(self):
        while True:
            msg = await self.user_queue.get()
            if isinstance(msg, NicknameReceived):
                self.nickname = msg.nickname

            if isinstance(msg, TokenReceived):
                self.token = msg.token

            raise ConnectionError

    async def process_message(
        self,
        writer: asyncio.StreamWriter,
        reader: asyncio.StreamReader,
        message: str,
        error_message: str,
    ) -> dict:
        await self.submit_message(writer, message)
        try:
            data = json.loads(await reader.readline())
        except json.JSONDecodeError:
            logging.error("Received malformed data during processing.")
            sys.exit(1)
        logging.debug(f"{data=}")
        if data is None:
            messagebox.showinfo("ERROR", error_message)
            logging.error(f"Failed to process: {error_message}")
            raise ValueError(error_message)
        return data

    async def authorise(
        self,
        writer: asyncio.StreamWriter,
        reader: asyncio.StreamReader,
    ) -> dict:
        return await self.process_message(
            writer=writer,
            reader=reader,
            message=f"{self.token}",
            error_message="Failed to authorise: Broken token.",
        )

    async def register(
        self,
        writer: asyncio.StreamWriter,
        reader: asyncio.StreamReader,
    ) -> dict:
        await self.submit_message(writer, "")
        logging.debug(await reader.readline())
        return await self.process_message(
            writer=writer,
            reader=reader,
            message=self.nickname,
            error_message="Failed to register: Register error.",
        )
