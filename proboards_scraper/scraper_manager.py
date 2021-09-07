import asyncio
import logging
import pathlib
import time

import aiohttp
import bs4
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
        request_threshold: int = 15,
        short_delay_time: float = 1.5,
        long_delay_time: float = 20.0
    ):
        """
        This class has three purposes: 1) to store references to objects that
        will be used in the process of scraping, 2) to serve as an abstraction
        layer between the scraper functionality and the database, and 3) to
        handle HTTP requests (adding delays between requests as needed to
        avoid throttling) and process the queues (popping items from the queues
        in the necessary order and inserting them into the database).

        Args:
            db: Database handle.
            client_session: ``aiohttp`` session.
            content_queue: Queue to which all content (excluding users) should
                be added for insertion into the database.
            driver: Selenium Chrome driver.
            image_dir: Directory to which downloaded images should be saved.
            user_queue: Queue to which users should be added for insertion
                into the database.
            request_threshold: After every :attr:`request_threshold` calls to
                :meth:`ScraperManager.get_source`, wait :attr:`long_delay_time`
                seconds before continuing. This is to prevent request
                throttling due to a large number of consecutive requests.
            short_delay_time: Number of seconds to wait after each call to
                :meth:`ScraperManager.get_source` (to help prevent request
                throttling).
            long_delay_time: See :attr:`request_threshold`.
        """
        self.db = db
        self.client_session = client_session

        if driver is None:
            # Selenium is required to scrape poll content (and, by corollary,
            # a Selenium driver).
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

    async def _delay(self) -> None:
        """
        Asynchronously sleep for an amount of time based on the number of
        requests, the request threshold, and the short/long delay times.
        """
        if not self.short_delay_time and not self.long_delay_time:
            return

        delay = self.short_delay_time

        if self.request_threshold is not None and self.long_delay_time:
            mod = self.request_threshold - 1
            if self.request_count % self.request_threshold == mod:
                delay = self.long_delay_time
                logger.debug(
                    f"Request count = {self.request_count + 1}, "
                    f"sleeping {delay} s"
                )
        await asyncio.sleep(delay)

    async def download_image(self, url: str) -> dict:
        """
        Download an image to :attr:`image_dir`.

        Args:
            url: URL of the image to be downloaded.

        Returns:
            Image download status and metadata; see
            :func:`proboards_scraper.download_image`.
        """
        if "proboards.com" in url:
            await self._delay()
            self.request_count += 1
        return await download_image(url, self.client_session, self.image_dir)

    async def get_source(self, url: str) -> bs4.BeautifulSoup:
        """
        Wrapper around :func:`proboards_scraper.scraper.get_source` with an
        added short delay via call to :func:`time.sleep` before each
        request, and a longer delay after every ``self.request_threshold``
        calls to :meth:`ScraperManager.get_source`. This rate-limiting is
        performed to help avoid request throttling by the server, which may
        result from a large number of requests in a short period of time.

        Args:
            url: URL whose page source to retrieve.

        Returns: BeautifulSoup page source object.
        """
        await self._delay()
        self.request_count += 1
        return await get_source(url, self.client_session)

    def insert_guest(self, name: str) -> int:
        """
        Insert a guest user into the database.

        Args:
            name: The guest's username.

        Returns:
            The user ID of the guest returned by
            :meth:`proboards_scraper.database.Database.insert_guest`.
        """
        guest = {
            "id": -1,
            "name": name,
        }

        # Get guest user id.
        guest_db_obj = self.db.insert_guest(guest)
        guest_id = guest_db_obj.id
        return guest_id

    def insert_image(self, image: dict) -> int:
        """
        Insert an image entry into the database.

        Args:
            image: A dict representing the image entry.

        Returns:
            The image ID of the image returned by
            :meth:`proboards_scraper.database.Database.insert_image`.
        """
        image_db_obj = self.db.insert_image(image)
        image_id = image_db_obj.id
        return image_id

    async def run(self) -> None:
        """
        Run the scraper, first processing the user queue and then processing
        the content queue, calling the appropriate database insert/query
        methods as needed, and closing the Selenium and aiohttp sessions upon
        completion.

        Because all content (threads, posts, etc.) is associated with users,
        the content queue is not processed until all users have been added
        from the user queue (the end of which is marked by a sentinel value).
        Guest users are an exception, since they are not present in the site's
        member list; instead, guests are added/queried as they are encountered
        by calling :meth:`ScraperManager.insert_guest`.
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
