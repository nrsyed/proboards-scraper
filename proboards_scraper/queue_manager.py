import asyncio
from typing import Union

import aiohttp

from proboards_scraper.database import Database


class QueueManager:
    def __init__(
        self, db: Database, user_queue: Union[asyncio.Queue, None],
        content_queue: asyncio.Queue, sess: aiohttp.ClientSession
    ):
        self.db = db
        self.content_queue = content_queue
        self.user_queue = user_queue
        self.sess = sess


    async def run(self):
        if self.user_queue is not None:
            all_users_added = False
            while not all_users_added:
                user = await self.user_queue.get()

                if user is None:
                    all_users_added = True
                else:
                    self.db.insert_user(user)

        all_content_added = False
        while not all_content_added:
            content = await self.content_queue.get()

            if content is None:
                all_content_added = True
            else:
                type_ = content["type"]
                del content["type"]

                type_to_insert_func = {
                    "board": self.db.insert_board,
                    "category": self.db.insert_category,
                    "moderator": self.db.insert_moderator,
                    "poll": self.db.insert_poll,
                    "post": self.db.insert_post,
                    "thread": self.db.insert_thread,
                }

                insert_func = type_to_insert_func[type_]
                insert_func(content)

        await sess.close()
