import argparse
import asyncio
import logging
import os
import pathlib
import requests
import sys
import time
from typing import Tuple

import bs4
import selenium.webdriver


class MockDatabase:
    def __init__(self):
        self.users = []


async def add_user_to_database(db: MockDatabase, user: dict):
    """
    TODO
    """
    db.users.append(user)
    await asyncio.sleep(0.2)
    return True


async def process_queues(
    db_path: pathlib.Path, user_queue: asyncio.Queue, content_queue: asyncio.Queue
):
    """
    Add all users followed by all content (boards, threads, posts) to the
    given database. This function first adds all users to the database (since
    users are referenced by all other content). Content is heirarchical (boards
    are added to the queue before threads, threads before posts, etc.); thus,
    each content piece's parent will have been added to the database earlier in
    the queue.
    """
    db = MockDatabase()

    all_users_added = False
    while not all_users_added:
        user = await user_queue.get()

        if user is None:
            all_users_added = True
        else:
            success = await add_user_to_database(db, user)


def get_login_cookies(
    home_url: str, username: str, password: str, page_load_wait: int = 1
) -> dict:
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

    # Get cookies from selenium driver and add to requests session.
    cookies = driver.get_cookies()
    return cookies


def get_login_session(cookies: dict) -> requests.sessions.Session:
    sess = requests.Session()

    for cookie in cookies:
        # https://docs.python-requests.org/en/latest/_modules/requests/cookies/#RequestsCookieJar
        cookie_dict = {
            "name": cookie["name"],
            "value": cookie["value"],
            "domain": cookie["domain"],
            "rest": {
                "HttpOnly": cookie["httpOnly"]
            },
            "path": cookie["path"],
            "secure": cookie["secure"],
        }

        if "expiry" in cookie:
            cookie_dict["expires"] = cookie["expiry"]
        sess.cookies.set(**cookie_dict)

    return sess


async def get_source(url: str, cookies: dict = None) -> bs4.BeautifulSoup:
    loop = asyncio.get_running_loop()

    if cookies:
        # Create a login session with the provided authentication cookies
        # before getting the page at `url`.
        sess = get_login_session(cookies)
        future = loop.run_in_executor(None, sess.get, url)
    else:
        future = loop.run_in_executor(None, requests.get, url)

    response = await future

    # TODO: check response HTTP status code
    return bs4.BeautifulSoup(response.text, "html.parser")


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


async def _get_user(url: str, cookies: dict, user_queue: asyncio.Queue):
    """
    TODO
    """
    # Get user number from URL, eg, "https://xyz.proboards.com/user/42" has
    # user number 42. We can exploit os.path.split() to grab everything right
    # of the last backslash.
    user = {
        "url": url,
        "user_number": int(os.path.split(url)[1])
    }

    source = await get_source(url, cookies=cookies)
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
            #"{messenger}:", eg, "AIM:" and the next tag (sibling) is the
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


async def get_users(url: str, cookies: dict, user_queue: asyncio.Queue):
    """
    url: Site base URL.
    cookies: Cookies dict for login authentication.
    """
    members_page_url = f"{url}/members"
    member_hrefs = []

    source = await get_source(members_page_url, cookies=cookies)
    _member_hrefs, next_href = _get_user_urls(source)
    member_hrefs.extend(_member_hrefs)

    while next_href:
        next_url = f"{url}{next_href}"
        source = await get_source(next_url, cookies=cookies)
        _member_hrefs, next_href = _get_user_urls(source)
        member_hrefs.extend(_member_hrefs)

    member_urls = [f"{url}{member_href}" for member_href in member_hrefs]

    loop = asyncio.get_running_loop()
    tasks = []

    for member_url in member_urls:
        task = loop.create_task(_get_user(member_url, cookies, user_queue))
        tasks.append(task)

    await asyncio.wait(tasks)
    await user_queue.put(None)
    users = [task.result() for task in tasks]
    return users


def scrape_site(url: str, username: str, password: str):
    """
    TODO
    """
    loop = asyncio.get_event_loop()

    # Queues from which elements will be consumed to populate the database.
    # Users will be added before other site content.
    user_queue = asyncio.Queue()
    content_queue = asyncio.Queue()

    # Get cookies for parts of the site requiring login authentication.
    cookies = get_login_cookies(url, username, password)

    get_users_task = get_users(url, cookies, user_queue)
    #get_content_task = 
    database_task = process_queues(None, user_queue, content_queue)

    task_group = asyncio.gather(get_users_task, database_task)
    loop.run_until_complete(task_group)

    # TODO: move this to dedicated function
    #source = get_source(url)
    #categories = source.findAll("div", class_="container boards")

    #for category in categories:
    #    scrape_category(category)
