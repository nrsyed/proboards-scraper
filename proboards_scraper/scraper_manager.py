import asyncio
import logging
import pathlib
import time

import aiohttp
import selenium.webdriver

from proboards_scraper.database import Database
from .http_requests import get_source, download_image


logger = logging.getLogger(__name__)


class ScraperManager:
    def __init__(
        self,
        db: Database,
        client_session: aiohttp.ClientSession,
        content_queue: asyncio.Queue = None,
        driver: selenium.webdriver.Chrome = None,
        image_dir: pathlib.Path = None,
        user_queue: asyncio.Queue = None,
        request_threshold: int = 20,
        short_delay_time: float = 1.0,
        long_delay_time: float = 15.0
    ):
        """
        Args:
            db:
            client_session:
            content_queue:
            driver:
            image_dir:
            user_queue:
            request_threshold: After every ``request_threshold`` calls to
                :meth:`ScraperManager.get_source`, wait ``long_delay_time``
                seconds before continuing. This is to prevent request
                throttling due to a large number of consecutive requests.
            short_delay_time: Number of seconds to wait after each call to
                :meth:`ScraperManager.get_source` (to help prevent request
                throttling).
            long_delay_time: See ``request_threshold``.
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

        # TODO: include selenium webdriver in request count?
        self.request_threshold = request_threshold
        self.short_delay_time = short_delay_time
        self.long_delay_time = long_delay_time
        self.request_count = 0

    def _delay(self):
        delay = self.short_delay_time

        mod = self.request_threshold - 1
        if self.request_count % self.request_threshold == mod:
            delay = self.long_delay_time
            logger.debug(
                f"Request count = {self.request_count + 1}, sleeping {delay} s"
            )
        time.sleep(delay)

    async def download_image(self, url):
        """
        TODO
        """
        if "proboards.com" in url:
            self._delay()
            self.request_count += 1
        return await download_image(url, self.client_session, self.image_dir)

    async def get_source(self, url):
        """
        Wrapper around :func:`proboards_scraper.scraper.get_source` with an
        added short delay via call to :func:`time.sleep` before each
        request, and a longer delay after every ``self.request_threshold``
        calls to :meth:`ScraperManager.get_source`. This rate-limiting is
        performed to help avoid request throttling by the server, which may
        result from a large number of requests in a short period of time.
        """
        self._delay()
        self.request_count += 1
        return await get_source(url, self.client_session)

    def insert_guest(self, name):
        """
        TODO
        """
        guest = {
            "id": -1,
            "name": name,
        }

        # Get guest user id.
        guest_db_obj = self.db.insert_guest(guest)
        guest_id = guest_db_obj.id
        return guest_id

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
                    "image": self.db.insert_image,
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
        self.driver.quit()
