import asyncio
import logging
import pathlib
from typing import Callable, Literal

import aiohttp

from .scraper_manager import ScraperManager
from proboards_scraper.database import Database
from proboards_scraper.scraper import (
    get_chrome_driver, get_login_cookies, get_login_session, split_url,
    scrape_board, scrape_forum, scrape_thread, scrape_user, scrape_users,
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
    skip_users: bool = False
):
    """
    Args:
        url:
        dst_dir:
        username:
        password:
        skip_users:
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

    manager = ScraperManager(
        db, client_session, driver=chrome_driver, image_dir=image_dir
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
