import asyncio
import logging
import pathlib
from typing import Callable, Literal

import aiohttp

from .http_requests import (
    get_chrome_driver, get_login_cookies, get_login_session
)
from .scraper_manager import ScraperManager
from proboards_scraper.database import Database
from proboards_scraper.scraper import (
    split_url, scrape_board, scrape_forum, scrape_thread, scrape_user,
    scrape_users,
)


logger = logging.getLogger(__name__)


async def _task_wrapper(
    func: Callable,
    queue_name: Literal["user", "content", "both"],
    url: str,
    manager: ScraperManager
):
    """
    Args:
        func: The async function to be called for scraping user(s) or content.
        queue_name: The queue(s) in which ``None`` should be put after ``func``
            completes, signaling to :meth:`ScraperManager.run` that that
            queue's task is complete.
        url: The URL to be passed to ``func``.
        manager: The ``ScraperManager`` instance to be passed to ``func``.
    """
    await func(url, manager)

    if queue_name == "both" or queue_name == "user":
        await manager.user_queue.put(None)

    if queue_name == "both" or queue_name == "content":
        await manager.content_queue.put(None)


def run_scraper(
    url: str,
    dst_dir: pathlib.Path = "site",
    username: str = None,
    password: str = None,
    skip_users: bool = False,
    no_delay: bool = False
) -> None:
    """
    Main function that runs the scraper and calls the appropriate `async`
    functions/methods. This is the only function that needs to be called to
    actually run the scraper (with all the default settings).

    Args:
        url: URL of the the page to scrape. If the URL is that of the forum
            homepage (e.g., `https://yoursite.proboards.com/`), the entire site
            (including users, shoutbox, category/board/thread/post content,
            etc.) will be scraped; if it is the URL for the members page
            (e.g., `https://yoursite.proboards.com/members`), only the users
            will be scraped; if it is the URL for a specific user profile
            (e.g., `https://yoursite.proboards.com/user/10`), only that
            particular user will be scraped; if it is the URL for a board
            (e.g., `https://yoursite.proboards.com/board/3/board-name`),
            only that particular board and its threads/posts will be
            scraped; if it is the URL for a thread
            (e.g., `https://yoursite.proboards.com/thread/1234/thread-title`)
            only that particular thread and its posts will be scraped.
        dst_dir: Directory in which to place the resulting files. The database
            file is written to ``<dst_dir>/forum.db`` and image files are
            saved to ``<dst_dir>/images``.
        username: Username for login.
        password: Password for login.
        skip_users: Skip scraping/adding users from the forum members page
            (only applies if the forum homepage is provided for ``url``.
        no_delay: Do not add a delay between subsequent requests (see
            :class:`ScraperManager` for more information). Note that this may
            result in request throttling.
    """
    dst_dir = dst_dir.expanduser().resolve()
    dst_dir.mkdir(parents=True, exist_ok=True)

    image_dir = dst_dir / "images"
    image_dir.mkdir(exist_ok=True)

    db_path = dst_dir / "forum.db"
    db = Database(db_path)

    chrome_driver = get_chrome_driver()

    base_url, url_path = split_url(url)

    # Get cookies for parts of the site requiring login authentication.
    if username and password:
        logger.info(f"Logging in to {base_url}")
        cookies = get_login_cookies(
            base_url, username, password, chrome_driver
        )

        # Create a persistent aiohttp login session from the cookies.
        client_session = get_login_session(cookies)
        logger.info("Login successful")
    else:
        logger.info(
            "Username and/or password not provided; proceeding without login"
        )
        client_session = aiohttp.ClientSession()

    manager_kwargs = {
        "driver": chrome_driver,
        "image_dir": image_dir,
    }

    if no_delay:
        manager_kwargs["request_threshold"] = None
        manager_kwargs["short_delay_time"] = None
        manager_kwargs["long_delay_time"] = None

    manager = ScraperManager(
        db, client_session, **manager_kwargs
    )

    tasks = []

    users_task = None
    content_task = None

    if url_path is None:
        # This represents the case where the forum homepage URL was provided,
        # i.e., we scrape the entire site.
        logger.info("Scraping entire forum")

        content_task = _task_wrapper(
            scrape_forum, "content", base_url, manager
        )

        if skip_users:
            logger.info("Skipping user profiles")
        else:
            users_page_url = f"{base_url}/members"
            users_task = _task_wrapper(
                scrape_users, "user", users_page_url, manager
            )
    elif url_path.startswith("/members"):
        users_task = _task_wrapper(scrape_users, "both", url, manager)
    elif url_path.startswith("/user"):
        users_task = _task_wrapper(scrape_user, "both", url, manager)
    elif url_path.startswith("/board"):
        content_task = _task_wrapper(
            scrape_board, "content", url, manager
        )
    elif url_path.startswith("/thread"):
        content_task = _task_wrapper(
            scrape_thread, "content", url, manager
        )

    if users_task is not None:
        tasks.append(users_task)
    else:
        manager.user_queue = None

    if content_task is not None:
        tasks.append(content_task)

    database_task = manager.run()
    tasks.append(database_task)

    task_group = asyncio.gather(*tasks)
    asyncio.get_event_loop().run_until_complete(task_group)
