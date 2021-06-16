# TODO: close aiohttp client session
# TODO: logging
import argparse
import asyncio
import concurrent.futures
import http
import logging
import os
import pathlib
import sys
import time
from typing import Any, List, Tuple, Union

import aiohttp

import bs4
import selenium.webdriver
import sqlalchemy
import sqlalchemy.orm

#from .schema import Base, Board, Category, Poll, Post, Thread, User
from .schema import Base, Board, Category, Post, Thread, User


logger = logging.getLogger(__name__)


def _add_to_database(db: sqlalchemy.orm.Session, item: dict):
    """
    Helper function for :func:`add_to_database`. Because SQLite objects
    created in a thread can only be used in that same thread, this function
    (callable in a separate thread by `loop.run_in_executor` from
    :func:`add_to_database`) handles everything related to creating, querying,
    and/or adding a given database item.
    """
    type_ = item["type"]
    del item["type"]

    item_type_to_db_table_metaclass = {
        "user": User,
        "category": Category,
        "board": Board,
        "thread": Thread,
        "post": Post,
        "poll": None # TODO
    }

    # Instantiate a database object from the database table metaclass.
    DBTableMetaclass = item_type_to_db_table_metaclass[type_]
    obj = DBTableMetaclass(**item)

    if type_ != "poll":
        query = db.query(DBTableMetaclass).filter_by(number=obj.number).first()
    else:
        pass

    # TODO: update an existing object or just skip?
    if query is None:
        db.add(obj)
        db.commit()


async def add_to_database(db: sqlalchemy.orm.Session, item: dict):
    """
    TODO
    """
    # TODO: use a custom threadpool with a single worker to avoid SQLite
    # multiple simultaneous writes?
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _add_to_database, db, item)


async def process_queues(
    db: sqlalchemy.orm.Session, user_queue: asyncio.Queue,
    content_queue: asyncio.Queue
):
    """
    Add all users followed by all content (boards, threads, posts) to the
    given database. This function first adds all users to the database (since
    users are referenced by all other content). Content is heirarchical (a
    given board is added to the queue before the threads it contains, a given
    thread is added to the queue before the posts it contains, etc.). Thus,
    the parent of each piece of content (if any) will have been added to the
    database earlier in the queue.
    """
    all_users_added = False
    while not all_users_added:
        user = await user_queue.get()

        if user is None:
            all_users_added = True
        else:
            success = await add_to_database(db, user)


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

    return sess


async def get_source(
    url: str, sess: aiohttp.ClientSession
) -> bs4.BeautifulSoup:
    """
    TODO
    """
    # TODO: check response HTTP status code
    resp = await sess.get(url)
    text = await resp.text()
    return bs4.BeautifulSoup(text, "html.parser")


def scrape_board(board: bs4.element.Tag):
    subboards = board.find("div", class_="container boards")
    if subboards:
        # TODO
        pass


def scrape_category(category: bs4.element.Tag):
    title_bar = category.find("div", class_="title_wrapper")
    title = title_bar.text
    boards = category.find("tbody").findAll("tr")

    for board in boards:
        # TODO
        #scrape_board(board)
        pass


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
    # Get user number from URL, eg, "https://xyz.proboards.com/user/42" has
    # user number 42. We can exploit os.path.split() to grab everything right
    # of the last backslash.
    user = {
        "type": "user",
        "url": url,
        "number": int(os.path.split(url)[1])
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
    return user


async def get_users(
    url: str, sess: aiohttp.ClientSession, user_queue: asyncio.Queue
):
    """
    url: Site base URL.
    sess: Login session.
    user_queue:
    """
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

    loop = asyncio.get_running_loop()
    tasks = []

    for member_url in member_urls:
        task = loop.create_task(_get_user(member_url, sess, user_queue))
        tasks.append(task)

    await asyncio.wait(tasks)
    await user_queue.put(None)
    users = [task.result() for task in tasks]
    return users


async def get_content(url: str, cookies: dict, content_queue: asyncio.Queue):
    """
    Scrape all categories/boards from the main page.
    """
    source = get_source(url)
    categories = source.findAll("div", class_="container boards")

    for category in categories:
        pass


def scrape_site(url: str, username: str, password: str, db_path: str):
    """
    TODO
    """
    # Open database connection and initialize database.
    engine = sqlalchemy.create_engine(f"sqlite:///{db_path}")
    Session = sqlalchemy.orm.sessionmaker(engine)
    db = Session()
    Base.metadata.create_all(engine)

    # Queues from which elements will be consumed to populate the database.
    # Users will be added before other site content.
    user_queue = asyncio.Queue()
    content_queue = asyncio.Queue()

    # Get cookies for parts of the site requiring login authentication.
    cookies = get_login_cookies(url, username, password)

    # Create a persistent aiohttp login session from the cookies.
    sess = get_login_session(cookies)

    # TODO: use asyncio *.join instead of run_until_complete?
    # TODO: use asyncio.run instead of asyncio.run_until_complete?
    get_users_task = get_users(url, sess, user_queue)
    #get_content_task = get_content(url, sess, content_queue)
    database_task = process_queues(db, user_queue, content_queue)

    task_group = asyncio.gather(get_users_task, database_task)
    
    # TODO: use async.run instead of loop.run_until_complete?
    loop = asyncio.get_event_loop()

    # Use a single-worker thread pool for performing database queries/calls.
    # Limiting the pool to a single worker allows us to run otherwise blocking
    # sqlite database calls in a separate thread (with `loop.run_in_executor`)
    # while avoiding concurrent write attempts from multiple threads, which
    # sqlite does not support.
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    loop.set_default_executor(pool)

    loop.run_until_complete(task_group)
