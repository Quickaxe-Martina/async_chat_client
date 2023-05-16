import asyncio
import logging
import tkinter as tk
from asyncio import Queue
from enum import Enum
from tkinter.scrolledtext import ScrolledText


class TkAppClosed(Exception):
    pass


class ReadConnectionStateChanged(str, Enum):
    INITIATED = "устанавливаем соединение"
    ESTABLISHED = "соединение установлено"
    CLOSED = "соединение закрыто"

    def __str__(self):
        return str(self.value)


class SendingConnectionStateChanged(str, Enum):
    INITIATED = "устанавливаем соединение"
    ESTABLISHED = "соединение установлено"
    CLOSED = "соединение закрыто"

    def __str__(self):
        return str(self.value)


class NicknameReceived:
    def __init__(self, nickname: str):
        self.nickname = nickname


def process_new_message(input_field: tk.Entry, sending_queue: Queue) -> None:
    text = input_field.get()
    sending_queue.put_nowait(text)
    input_field.delete(0, tk.END)


async def update_tk(root_frame: tk.Frame, interval: float = 1 / 120) -> None:
    while True:
        try:
            root_frame.update()
        except tk.TclError:
            # if application has been destroyed/closed
            raise TkAppClosed()
        await asyncio.sleep(interval)


async def update_conversation_history(
    panel: ScrolledText, messages_queue: Queue
) -> None:
    while True:
        msg = await messages_queue.get()

        panel["state"] = "normal"
        if panel.index("end-1c") != "1.0":
            panel.insert("end", "\n")

        logging.debug(f"{panel.yview()[1]=} >= 0.98")
        is_scroll_end = panel.yview()[1] >= 0.98
        panel.insert("end", msg)
        if is_scroll_end:
            panel.yview(tk.END)
        panel["state"] = "disabled"


async def update_status_panel(
    status_labels: tuple, status_updates_queue: Queue
) -> None:
    nickname_label, read_label, write_label = status_labels

    read_label["text"] = f"Чтение: нет соединения"
    write_label["text"] = f"Отправка: нет соединения"
    nickname_label["text"] = f"Имя пользователя: неизвестно"

    while True:
        msg = await status_updates_queue.get()
        if isinstance(msg, ReadConnectionStateChanged):
            read_label["text"] = f"Чтение: {msg}"

        if isinstance(msg, SendingConnectionStateChanged):
            write_label["text"] = f"Отправка: {msg}"

        if isinstance(msg, NicknameReceived):
            nickname_label["text"] = f"Имя пользователя: {msg.nickname}"


def create_status_panel(root_frame: tk.Frame) -> tuple:
    status_frame = tk.Frame(root_frame)
    status_frame.pack(side="bottom", fill=tk.X)

    connections_frame = tk.Frame(status_frame)
    connections_frame.pack(side="left")

    nickname_label = tk.Label(
        connections_frame, height=1, fg="grey", font="arial 10", anchor="w"
    )
    nickname_label.pack(side="top", fill=tk.X)

    status_read_label = tk.Label(
        connections_frame, height=1, fg="grey", font="arial 10", anchor="w"
    )
    status_read_label.pack(side="top", fill=tk.X)

    status_write_label = tk.Label(
        connections_frame, height=1, fg="grey", font="arial 10", anchor="w"
    )
    status_write_label.pack(side="top", fill=tk.X)

    return nickname_label, status_read_label, status_write_label


async def draw(
    messages_queue: Queue, sending_queue: Queue, status_updates_queue: Queue
) -> None:
    root = tk.Tk()

    root.title("Чат Майнкрафтера")

    root_frame = tk.Frame()
    root_frame.pack(fill="both", expand=True)

    status_labels = create_status_panel(root_frame)

    input_frame = tk.Frame(root_frame)
    input_frame.pack(side="bottom", fill=tk.X)

    input_field = tk.Entry(input_frame)
    input_field.pack(side="left", fill=tk.X, expand=True)

    input_field.bind(
        "<Return>", lambda event: process_new_message(input_field, sending_queue)
    )

    send_button = tk.Button(input_frame)
    send_button["text"] = "Отправить"
    send_button["command"] = lambda: process_new_message(input_field, sending_queue)
    send_button.pack(side="left")

    conversation_panel = ScrolledText(root_frame, wrap="none")
    conversation_panel.pack(side="top", fill="both", expand=True)

    await asyncio.gather(
        update_tk(root_frame),
        update_conversation_history(conversation_panel, messages_queue),
        update_status_panel(status_labels, status_updates_queue),
    )
