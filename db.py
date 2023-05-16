import asyncio
import logging

import aiosqlite

DB_FILE_NAME = "my_database.db"


async def save_msgs_to_db(queue: asyncio.Queue):
    async with aiosqlite.connect(DB_FILE_NAME) as db:
        while True:
            item = await queue.get()
            if item is None:
                break

            dt, text = item

            logging.debug(f"{dt=} {text=}")
            await db.execute(
                f"""
                INSERT INTO main.messages (dt, text) VALUES (?, ?)
            """,
                (dt, text),
            )
            await db.commit()


async def put_all_messages_in_queue(queue: asyncio.Queue):
    async with aiosqlite.connect("my_database.db") as db:
        cursor = await db.execute("SELECT dt, text  FROM main.messages")
        rows = await cursor.fetchall()
        for msg in rows:
            dt, text = msg
            line = f"[{dt}] {text}"
            logging.debug(line)
            queue.put_nowait(line)


async def create_table():
    async with aiosqlite.connect(DB_FILE_NAME) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS main.messages (
                id INTEGER  PRIMARY KEY,
                dt TEXT NOT NULL,
                text TEXT NOT NULL
            );
        """
        )
        await db.commit()


# if __name__ == "__main__":
#     asyncio.run(create_table())
