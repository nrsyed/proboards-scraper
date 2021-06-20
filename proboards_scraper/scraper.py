# TODO: announcement thread (avoid visiting in every board)
import argparse
import asyncio
import concurrent.futures
import http
import logging
import os
import pathlib
import re
import sys
import time
from typing import Any, List, Tuple, Union

import aiohttp

import bs4
import selenium.webdriver
import sqlalchemy
import sqlalchemy.orm

import proboards_scraper.database
from proboards_scraper.database import (
    Base, Board, Category, Moderator, Post, Thread, User,
)


logger = logging.getLogger(__name__)


def add_to_database(db: sqlalchemy.orm.Session, item: dict) -> dict:
    """
    TODO
    """
    type_ = item["type"]
    del item["type"]

    retval = {}

    item_type_to_db_table_metaclass = {
        "board": Board,
        "category": Category,
        "guest": User,
        "moderator": Moderator,
        "poll": None, # TODO
        "post": Post,
        "user": User,
        "thread": Thread,
    }

    # Instantiate a database object from the database table metaclass.
    DBTableMetaclass = item_type_to_db_table_metaclass[type_]
    obj = DBTableMetaclass(**item)

    if type_ == "moderator":
        filters = {
            "user_id": obj.user_id,
            "board_id": obj.board_id,
        }
        item_desc = f"(user {obj.user_id}, board {obj.board_id})"
    elif type_ == "guest":
        # Guest users (which includes deleted users) do not have an actual
        # user id or profile page, so we simply assign them negative ids
        # in the database.
        guests_query = db.query(DBTableMetaclass).filter(User.id < 0)
        this_guest = guests_query.filter_by(name=obj.name).first()

        if this_guest:
            # This guest user already exists in the database.
            obj.id = this_guest.id
        else:
            # Otherwise, this particular guest user does not exist in the
            # database. Iterate through all guests and assign a new negative
            # user id by decrementing the smallest guest user id already in
            # the database.
            lowest_id = 0
            for guest in guests_query.all():
                lowest_id = min(guest.id, lowest_id)
            new_guest_id = lowest_id - 1
            obj.id = new_guest_id

        filters = {"id": obj.id}
        item_desc = f"{item['name']}"
        retval = {"guest_id": obj.id}
    else:
        filters = {"id": obj.id}
        item_desc = f"{item['name']}"

    result = db.query(DBTableMetaclass).filter_by(**filters).first()
    if result is None:
        db.add(obj)
        db.commit()
        logger.info(f"{type_} {item_desc} added to database")
    else:
        # TODO: update an existing object or just skip?
        logger.info(
            f"{type_} {item_desc} already exists in database; skipping"
        )

    return retval


async def process_queues(
    db: sqlalchemy.orm.Session, user_queue: Union[asyncio.Queue, None],
    content_queue: asyncio.Queue, sess: aiohttp.ClientSession
):
    """
    Add all users followed by all content (boards, threads, posts) to the
    given database. This function first adds all users to the database (since
    users are referenced by all other content). Content is heirarchical (a
    given board is added to the queue before the threads it contains, a given
    thread is added to the queue before the posts it contains, etc.). Thus,
    the parent of each piece of content (if any) will have been added to the
    database earlier in the queue.

    Args:
        sess: This is provided so the session can be closed after all content
            has been processed from the queues.
    """
    if user_queue is not None:
        all_users_added = False
        while not all_users_added:
            user = await user_queue.get()

            if user is None:
                all_users_added = True
            else:
                # TODO: success/failure
                success = add_to_database(db, user)

    all_content_added = False
    while not all_content_added:
        content = await content_queue.get()

        if content is None:
            all_content_added = True
        else:
            success = add_to_database(db, content)

    await sess.close()


def get_login_cookies(
    home_url: str, username: str, password: str, page_load_wait: int = 1
) -> dict:
    """
    TODO
    """
    chrome_opts = selenium.webdriver.ChromeOptions()
    chrome_opts.headless = True
    driver = selenium.webdriver.Chrome(options=chrome_opts)
    driver.get(home_url)
    time.sleep(page_load_wait)

    links = driver.find_elements_by_tag_name("a")
    login_url = None

    for link in links:
        href = link.get_attribute("href")
        if href.startswith("https://login.proboards.com/login"):
            login_url = href
            break

    # Navigate to login page and fill in username/password fields.
    driver.get(login_url)
    time.sleep(page_load_wait)

    email_input = None
    password_input = None
    submit_input = None

    inputs = driver.find_elements_by_tag_name("input")
    for input_ in inputs:
        try:
            input_name = input_.get_attribute("name")
            if input_name == "email":
                email_input = input_
            elif input_name == "password":
                password_input = input_
            elif input_name == "continue":
                submit_input = input_
        except:
            # TODO
            pass

    email_input.send_keys(username)
    password_input.send_keys(password)
    submit_input.click()
    time.sleep(page_load_wait)

    cookies = driver.get_cookies()
    return cookies


def get_login_session(cookies: List[dict]) -> aiohttp.ClientSession:
    """
    TODO
    """
    logger.debug("Creating aiohttp login session from cookies")
    sess = aiohttp.ClientSession()

    morsels = {}
    for cookie in cookies:
        # https://docs.python.org/3/library/http.cookies.html#morsel-objects
        morsel = http.cookies.Morsel()
        morsel.set(cookie["name"], cookie["value"], cookie["value"])
        morsel["domain"] = cookie["domain"]
        morsel["httponly"] = cookie["httpOnly"]
        morsel["path"] = cookie["path"]
        morsel["secure"] = cookie["secure"]

        # NOTE: ignore expires field; if it's absent, the cookie remains
        # valid for the duration of the session.
        #if "expiry" in cookie:
        #    morsel["expires"] = cookie["expiry"]

        morsels[cookie["name"]] = morsel

    sess.cookie_jar.update_cookies(morsels)

    logger.debug("Added cookies to aiohttp session")
    return sess


async def get_source(
    url: str, sess: aiohttp.ClientSession
) -> bs4.BeautifulSoup:
    """
    TODO
    """
    logger.debug(f"Getting page source for {url}")
    # TODO: check response HTTP status code
    resp = await sess.get(url)
    text = await resp.text()
    return bs4.BeautifulSoup(text, "html.parser")


def _get_user_urls(source: bs4.BeautifulSoup) -> Tuple[list, str]:
    member_hrefs = []
    next_href = None

    members_container = source.find("div", class_="container members")
    members_table_rows = members_container.find("tbody").findAll("tr")
    for row in members_table_rows:
        # NOTE: the href attribute is relative and must be appended to the
        # site's base URL to construct the full user URL for a user.
        href = row.find("a")["href"]
        member_hrefs.append(href)

    # Get the URL for the next page button if it's enabled.
    next_ = source.find("li", {"class": "next"}).find("a")
    if next_.has_attr("href"):
        next_href = next_["href"]

    return member_hrefs, next_href


async def _get_user(
    url: str, sess: aiohttp.ClientSession, user_queue: asyncio.Queue
):
    """
    TODO
    """
    # Get user id from URL, eg, "https://xyz.proboards.com/user/42" has
    # user id 42. We can exploit os.path.split() to grab everything right
    # of the last backslash.
    user = {
        "type": "user",
        "url": url,
        "id": int(os.path.split(url)[1])
    }

    source = await get_source(url, sess)
    user_container = source.find("div", {"class": "show-user"})

    # Get display name and group.
    name_and_group = user_container.find(
        "div", class_="name_and_group float-right"
    )
    user["name"] = name_and_group.find("span", class_="big_username").text

    # The group name is contained between two <br> tags and is the element's
    # fourth child.
    children = [child for child in name_and_group.children]
    user["group"] = children[3].strip()

    # Get username and last online datetime.
    controls = user_container.find("div", class_="float-right controls")
    user_datetime = controls.find("div", class_="float-right clear pad-top")
    children = [child for child in user_datetime.children]
    for i, child in enumerate(children):
        if isinstance(child, bs4.element.NavigableString):
            if child.strip() == "Username:":
                user["username"] = children[i+1].text
            elif child.strip() == "Last Online:":
                # Get Unix timestamp string from <abbr> tag.
                lastonline_block = children[i+1]
                unix_ts = lastonline_block.find("abbr")["data-timestamp"]
                user["last_online"] = unix_ts
            elif child.strip() == "Member is Online":
                # This will be the case for the aiohttp session's logged-in
                # user (and for any other user that happens to be logged in).
                unix_ts = str(int(time.time()))
                user["last_online"] = unix_ts

    # Get rest of user info from the table in the user status form.
    status_form = user_container.find(
        "div", class_="pad-all-double ui-helper-clearfix clear"
    )
    main_table = status_form.find(id="center-column")

    # Extract "content boxes" (<div> elements containing different classes of
    # info) from the "main table".
    content_boxes = main_table.find_all("div", class_="content-box")

    # The first row ("content box") of the main table is always present and
    # contains another table, where each row contains two columns: the first
    # is a heading specifying the type of info (eg, "Email:"), and the second
    # contains its value.

    # NOTE: for the session's logged-in user, the first row contains a
    # "status update" form input, which we identify and delete if necessary.
    status_input = content_boxes[0].find("td", class_="status-input")
    if status_input:
        content_boxes.pop(0)

    for row in content_boxes[0].find_all("tr"):
        row_data = row.find_all("td")
        heading = row_data[0].text.strip().rstrip(":")
        val = row_data[1]

        if heading == "Age":
            user["age"] = int(val.text)
        elif heading == "Birthday":
            user["birthdate"] = val.text
        elif heading == "Date Registered":
            user["date_registered"] = val.find("abbr")["data-timestamp"]
        elif heading == "Email":
            user["email"] = val.text
        elif heading == "Gender":
            user["gender"] = val.text
        elif heading == "Latest Status":
            user["latest_status"] = val.find("span").text
        elif heading == "Location":
            user["location"] = val.text
        elif heading == "Posts":
            # Remove commas from post count (eg, "1,500" to "1500").
            user["post_count"] = int(val.text.replace(",", ""))
        elif heading == "Web Site":
            website_anchor = val.find("a")
            user["website_url"] = website_anchor.get("href")
            user["website"] = website_anchor.text

    # The rest of the relevant content boxes may or not be present.
    for content_box in content_boxes[1:]:
        # We use the first child to determine the content type, ignoring
        # any unnecessary newlines.
        children = [
            child for child in content_box.children if str(child) != "\n"
        ]
        first_child = children[0]

        if (
            isinstance(first_child, bs4.element.NavigableString)
            and first_child.strip() == "Signature"
        ):
            # Grab the entire signature HTML as a string; the signature starts
            # after a horizontal line <hr>, ie, the box's 3rd child and ends
            # before the last element
            signature = "".join([str(child) for child in children[2:]])
            user["signature"] = signature
        elif (
            isinstance(first_child, bs4.element.Tag)
            and "social" in first_child.get("class", [])
            and "messengers" in first_child.get("class", [])
        ):
            # Construct the instant messenger string that will be inserted
            # into the database. Each messenger label has the form
            # "{messenger}:", eg, "AIM:", and the next tag (sibling) is the
            # messenger screen name. The constructed string is of the form
            # "{messenger1}:{screenname1};{messenger2}:{screenname2}:..."
            # where each messenger type is delimited by a semicolon, eg:
            # "AIM:ssj_goku12;ICQ:12345;YIM:duffman20"
            messenger_str_list = []

            messenger_labels = first_child.find_all("span", class_="label")
            for messenger_label in messenger_labels:
                messenger = messenger_label.text
                screen_name = messenger_label.next_sibling.text
                messenger_str_list.append(f"{messenger}{screen_name}")

            messenger_str = ";".join(messenger_str_list)
            user["instant_messengers"] = messenger_str

    await user_queue.put(user)
    logger.debug(f"Got user profile info for user {user['name']}")
    return user


async def get_users(
    url: str, sess: aiohttp.ClientSession, user_queue: asyncio.Queue
):
    """
    url: Site base URL.
    sess: Login session.
    user_queue:
    """
    logger.info(f"Getting user profile URLs from {url}")

    members_page_url = f"{url}/members"
    member_hrefs = []

    source = await get_source(members_page_url, sess)
    _member_hrefs, next_href = _get_user_urls(source)
    member_hrefs.extend(_member_hrefs)

    while next_href:
        next_url = f"{url}{next_href}"
        source = await get_source(next_url, sess)
        _member_hrefs, next_href = _get_user_urls(source)
        member_hrefs.extend(_member_hrefs)

    member_urls = [f"{url}{member_href}" for member_href in member_hrefs]
    logger.info(f"Found {len(member_urls)} user profile URLs")

    loop = asyncio.get_running_loop()
    tasks = []

    for member_url in member_urls:
        task = loop.create_task(_get_user(member_url, sess, user_queue))
        tasks.append(task)

    await asyncio.wait(tasks)
    await user_queue.put(None)
    users = [task.result() for task in tasks]
    return users


async def scrape_thread(
    url: str, sess: aiohttp.ClientSession, content_queue: asyncio.Queue,
    board_id: int = None, user_id: int = None, locked: bool = False,
    sticky: bool = False, announcement: bool = False
):
    """
    """
    # TODO: get thread title, thread id, add thread to queue before
    # scraping all posts.
    pass


async def scrape_board(
    url: str, sess: aiohttp.ClientSession, content_queue: asyncio.Queue,
    category_id: int = None, moderators: List[int] = None,
    parent_id: int = None
):
    """
    Args:
        moderators: Optional list of moderator ids for the board (this is
            available on the main page).
    """
    # Board URLs take the form
    # https://{subdomain}.proboards.com/board/{id}/{name}
    expr = r"(.*)/board/(\d+)/.*"
    match = re.match(expr, url)

    # We get the site_url to construct sub-board URLs (if any) later.
    site_url = match.groups()[0]
    board_id = int(match.groups()[1])

    source = await get_source(url, sess)

    # Get board name and description from Information/Statistics container.
    stats_container = source.find("div", class_="container stats")
    
    description = None
    password_protected = None
    if (
        (not stats_container)
        and ("This board is password protected" in str(source))
    ):
        container = source.find("div", class_="container")
        title_heading = container.find("div", class_="title-bar").find("h2")
        board_name = title_heading.text
        password_protected = True
    else:
        board_name = stats_container.find("div", class_="board-name").text
        description = stats_container.find("div", class_="board-description").text

    board = {
        "type": "board",
        "category_id": category_id,
        "description": description,
        "id": board_id,
        "name": board_name,
        "parent_id": parent_id,
        "password_protected": password_protected,
        "url": url,
    }
    await content_queue.put(board)

    if moderators:
        for user_id in moderators:
            moderator = {
                "type": "moderator",
                "user_id": user_id,
                "board_id": board_id,
            }
            await content_queue.put(moderator)

    # Add any sub-boards to the queue.
    subboard_container = source.find("div", class_="container boards")
    if subboard_container:
        subboards = subboard_container.find("tbody").findAll("tr")

        for subboard in subboards:
            clickable = subboard.find("td", class_="main clickable")
            link = clickable.find("span", class_="link").find("a")
            href = link["href"]
            subboard_url = site_url + href

            await scrape_board(
                subboard_url, sess, content_queue, category_id=category_id,
                parent_id=board_id
            )

    # Iterate over all board pages and add threads on each page to queue.
    thread_container = source.find("div", class_="container threads")

    if thread_container:
        pages_remaining = True
        while pages_remaining:
            thread_tbody = thread_container.find("tbody")
            threads = thread_tbody.findAll("tr", class_="thread")

            for thread_ in threads:
                announcement = "announcement" in thread_["class"]
                sticky = "sticky" in thread_["class"]
                locked = "locked" in thread_["class"]

                created_by_tag = thread_.find("td", class_="created-by")

                if guest_ := created_by_tag.find("span", class_="user-guest"):
                    # This case occurs if the user is a guest or deleted user.
                    # We assign the guest a user id of -1, add them to the
                    # content queue (not user queue, which is intended for
                    # registered users), and let :func:`add_to_database`
                    # determine if this guest is already in the database (and
                    # assign a new negative id if not).
                    guest_user_name = guest_.text
                    guest = {
                        "type": "guest",
                        "id": -1,
                        "name": guest_user_name,
                    }

                    # Get new guest user id.
                    retval = await content_queue.put(guest)
                    create_user_id = retval["guest_id"]
                else:
                    # The href attribute is of the form "/user/12".
                    #created_by_anchor = created_by_tag.find("a")
                    created_by_href = created_by_tag.find("a")["href"]
                    create_user_id = int(created_by_href.split("/")[-1])

                clickable = thread_.find("td", class_="main clickable")
                anchor = clickable.find("span", class_="link target").find("a")
                thread_href = anchor["href"]
                thread_url = site_url + thread_href
                await scrape_thread(
                    thread_url, sess, content_queue, board_id=board_id,
                    user_id=create_user_id, locked=locked, sticky=sticky,
                    announcement=announcement
                )

            # control-bar contains pagination/navigation buttons.
            control_bar = thread_container.find("ul", class_="ui-pagination")
            next_btn = control_bar.find("li", class_="next")

            if "state-disabled" in next_btn["class"]:
                pages_remaining = False
            else:
                next_page_href = next_btn.find("a")["href"]
                next_page_url = site_url + next_page_href
                logger.info(f"Getting source for {next_page_url}")
                source = await get_source(next_page_url, sess)
                thread_container = source.find(
                    "div", class_="container threads"
                )


async def get_content(
    url: str, sess: aiohttp.ClientSession, content_queue: asyncio.Queue
):
    """
    Scrape all categories/boards from the main page.

    Args:
        url: Homepage URL.
    """
    source = await get_source(url, sess)
    categories = source.findAll("div", class_="container boards")

    for category_ in categories:
        # The category id is found among the tag's previous siblings and looks
        # like <a name="category-2"></a>. We want the number in the name attr.
        category_id_tag = list(category_.previous_siblings)[1]
        category_id = int(category_id_tag["name"].split("-")[1])

        title_bar = category_.find("div", class_="title_wrapper")
        category_name = title_bar.text

        # Add category to database queue.
        category = {
            "type": "category",
            "id": category_id,
            "name": category_name,
        }
        await content_queue.put(category)

        boards = category_.findAll(
            "tr",
            {"class": ["o-board", "board", "item"]}
        )

        for board_ in boards:
            clickable = board_.find("td", class_="main clickable")
            link = clickable.find("span", class_="link").find("a")
            href = link["href"]
            board_url = url + href

            # Get list of moderators, if any.
            mods_tag = clickable.find("p", class_="moderators")

            moderator_ids = None
            if mods_tag is not None:
                moderator_ids = [
                    int(a_tag["data-id"]) for a_tag in mods_tag.findAll("a")
                ]

            await scrape_board(
                board_url, sess, content_queue, category_id=category_id,
                moderators=moderator_ids
            )

    await content_queue.put(None)


def scrape_site(
    url: str, db_path: str, username: str = None, password: str = None,
    skip_users: bool = False,
):
    """
    Args:
        url:
        username:
        password:
        db_path:
        skip_users:
    """
    url = url.rstrip("/")

    # Get cookies for parts of the site requiring login authentication.
    if username and password:
        logger.info(f"Logging in to {url}")
        cookies = get_login_cookies(url, username, password)

        # Create a persistent aiohttp login session from the cookies.
        sess = get_login_session(cookies)
        logger.info("Login successful")
    else:
        logger.info(
            "Username and/or password not provided; proceeding without login"
        )
        sess = aiohttp.ClientSession()

    tasks = []

    if not skip_users:
        user_queue = asyncio.Queue()
        users_task = get_users(url, sess, user_queue)
        tasks.append(users_task)
    else:
        user_queue = None
        logger.info("Skipping user profiles")

    content_queue = asyncio.Queue()
    content_task = get_content(url, sess, content_queue)
    tasks.append(content_task)

    db = proboards_scraper.database.get_session(db_path)
    database_task = process_queues(db, user_queue, content_queue, sess)
    tasks.append(database_task)

    task_group = asyncio.gather(*tasks)
    asyncio.get_event_loop().run_until_complete(task_group)

    #pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    #loop.set_default_executor(pool)
