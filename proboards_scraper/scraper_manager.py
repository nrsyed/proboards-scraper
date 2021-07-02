import asyncio
import logging
import pathlib

import aiohttp
import selenium.webdriver

from proboards_scraper.database import Database


logger = logging.getLogger(__name__)


class ScraperManager:
    def __init__(
        self,
        db: Database,
        client_session: aiohttp.ClientSession,
        content_queue: asyncio.Queue = None,
        driver: selenium.webdriver.Chrome = None,
        image_dir: pathlib.Path = None,
        user_queue: asyncio.Queue = None
    ):
        """
        Args:
            db:
            client_session:
            content_queue:
            driver:
            image_dir:
            user_queue:
        """
        self.db = db
        self.client_session = client_session

        if driver is None:
            logger.warning(
                "Polls cannot be scraped without setting a Chrome webdriver"
            )
        self.driver = driver

        if image_dir is None:
            image_dir = pathlib.Path("./images").expanduser().resolve()
        image_dir.mkdir(exist_ok=True)
        self.image_dir = image_dir

        if content_queue is None:
            content_queue = asyncio.Queue()
        self.content_queue = content_queue

        if user_queue is None:
            user_queue = asyncio.Queue()
        self.user_queue = user_queue

    async def run(self):
        """
        TODO
        """
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
                    "poll_option": self.db.insert_poll_option,
                    "poll_voter": self.db.insert_poll_voter,
                    "post": self.db.insert_post,
                    "shoutbox_post": self.db.insert_shoutbox_post,
                    "thread": self.db.insert_thread,
                }

                insert_func = type_to_insert_func[type_]
                insert_func(content)

        await self.client_session.close()
