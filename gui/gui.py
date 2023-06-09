import asyncio
import logging
import tkinter as tk
from asyncio import Queue
from enum import Enum
from tkinter.scrolledtext import ScrolledText
from typing import Callable


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


class TokenReceived:
    def __init__(self, token: str):
        self.token = token


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

        # logging.debug(f"{panel.yview()[1]=} >= 0.98")
        is_scroll_end = panel.yview()[1] >= 0.98
        panel.insert("end", msg)
        if is_scroll_end:
            panel.yview(tk.END)
        panel["state"] = "disabled"


async def update_status_panel(
    status_labels: tuple,
    status_updates_queue: Queue,
    credentials_user_labels: tuple,
) -> None:
    nickname_label, read_label, write_label = status_labels
    token_input_field, nickname_input_field = credentials_user_labels

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
            nickname_input_field.delete(0, tk.END)
            nickname_input_field.insert(0, msg.nickname)

        if isinstance(msg, TokenReceived):
            token_input_field.delete(0, tk.END)
            token_input_field.insert(0, msg.token)


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


def create_input_frame(
    root_frame: tk.Frame,
    func: Callable,
    queue: asyncio.Queue,
    text_button: str,
    text: str = "",
) -> tk.Entry:
    frame = tk.Frame(root_frame)
    frame.pack(side="bottom", fill=tk.X)

    input_field = tk.Entry(frame)
    input_field.pack(side="left", fill=tk.X, expand=True)
    if text:
        input_field.insert(0, text)

    input_field.bind("<Return>", lambda event: func(input_field, queue))
    send_button = tk.Button(frame)
    send_button["text"] = text_button
    send_button["command"] = lambda: func(input_field, queue)
    send_button.pack(side="left")
    return input_field


def process_new_token(input_field: tk.Entry, queue: Queue) -> None:
    text = input_field.get()
    queue.put_nowait(TokenReceived(token=text))


def process_new_nickname(input_field: tk.Entry, queue: Queue) -> None:
    text = input_field.get()
    queue.put_nowait(NicknameReceived(nickname=text))


async def draw(
    messages_queue: Queue,
    sending_queue: Queue,
    status_updates_queue: Queue,
    user_queue: Queue,
) -> None:
    root = tk.Tk()

    root.title("Чат Майнкрафтера")

    root_frame = tk.Frame()
    root_frame.pack(fill="both", expand=True)

    # Token
    token_input_field = create_input_frame(
        root_frame=root_frame,
        text_button="Сохранить токен",
        func=process_new_token,
        queue=user_queue,
        text="test",
    )

    # Nickname
    nickname_input_field = create_input_frame(
        root_frame=root_frame,
        text_button="Сохранить никнейм",
        func=process_new_nickname,
        queue=user_queue,
        text="test",
    )

    # Statuses

    status_labels = create_status_panel(root_frame)

    # Input
    create_input_frame(
        root_frame=root_frame,
        text_button="Отправить",
        func=process_new_message,
        queue=sending_queue,
    )

    # Scroll
    conversation_panel = ScrolledText(root_frame, wrap="none")
    conversation_panel.pack(side="top", fill="both", expand=True)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(update_tk(root_frame))
        tg.create_task(update_conversation_history(conversation_panel, messages_queue))
        tg.create_task(
            update_status_panel(
                status_labels,
                status_updates_queue,
                (token_input_field, nickname_input_field),
            )
        )
