# TODO: announcement thread (avoid visiting in every board)
import asyncio
import logging
import os
import pathlib
import re
import time
from typing import List, Tuple

import aiohttp
import bs4

from .http_requests import (
    download_image, get_login_cookies, get_login_session, get_source
)
from .scraper_manager import ScraperManager
from proboards_scraper.database import Database


logger = logging.getLogger(__name__)


def scrape_user_urls(source: bs4.BeautifulSoup) -> Tuple[list, str]:
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


async def scrape_user(url: str, manager: ScraperManager):
    """
    TODO
    """
    # Get user id from URL, eg, "https://xyz.proboards.com/user/42" has
    # user id 42. We can exploit os.path.split() to grab everything right
    # of the last backslash.
    user = {
        "url": url,
        "id": int(os.path.split(url)[1])
    }

    source = await get_source(url, manager.client_session)
    user_container = source.find("div", {"class": "show-user"})

    # Get display name and group.
    name_and_group = user_container.find(
        "div", class_="name_and_group float-right"
    )
    user["name"] = name_and_group.find("span", class_="big_username").text

    # Download avatar.
    avatar_wrapper = user_container.find("div", class_="avatar-wrapper")
    avatar_url = avatar_wrapper.find("img")["src"]

    avatar_ret = await download_image(
        avatar_url, manager.client_session, manager.image_dir
    )

    image = avatar_ret["image"]

    # We need an image id to associate this image with a user as an avatar;
    # thus, we must interact with the database directly to retrieve the
    # image id (if it already exists in the database) or add then retrieve
    # the id of the newly added image (if it doesn't already exist).
    # NOTE: even if the image wasn't obtained successfully or is invalid, we
    # still store an Image in the database that contains the original avatar
    # URL (and an Avatar linking that Image to the current user).
    image_db_obj = manager.db.insert_image(image)
    image_id = image_db_obj.id

    avatar = {
        "user_id": user["id"],
        "image_id": image_id,
    }
    manager.db.insert_avatar(avatar)

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
                # Multiply time.time() value by 1000 for milliseconds.
                unix_ts = str(int(time.time()) * 1000)
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

    await manager.user_queue.put(user)
    logger.debug(f"Got user profile info for user {user['name']}")
    return user


async def scrape_users(url: str, manager: ScraperManager):
    """
    url: Site base URL.
    manager:
    """
    logger.info(f"Getting user profile URLs from {url}")

    members_page_url = f"{url}/members"
    member_hrefs = []

    source = await get_source(members_page_url, manager.client_session)
    _member_hrefs, next_href = scrape_user_urls(source)
    member_hrefs.extend(_member_hrefs)

    while next_href:
        next_url = f"{url}{next_href}"
        source = await get_source(next_url, manager.client_session)
        _member_hrefs, next_href = scrape_user_urls(source)
        member_hrefs.extend(_member_hrefs)

    member_urls = [f"{url}{member_href}" for member_href in member_hrefs]
    logger.info(f"Found {len(member_urls)} user profile URLs")

    loop = asyncio.get_running_loop()
    tasks = []

    for member_url in member_urls:
        task = loop.create_task(scrape_user(member_url, manager))
        tasks.append(task)

    await asyncio.wait(tasks)
    await manager.user_queue.put(None)
    users = [task.result() for task in tasks]
    return users


async def scrape_thread(
    url: str,
    manager: ScraperManager,
    board_id: int = None,
    user_id: int = None,
    views: int = None,
    announcement: bool = False,
    locked: bool = False,
    sticky: bool = False
):
    """
    TODO
    """
    # Get thread id from URL.
    expr = r"(.*)/thread/(\d+)/.*"
    match = re.match(expr, url)
    site_url = match.groups()[0]
    thread_id = int(match.groups()[1])

    source = await get_source(url, manager.client_session)

    post_container = source.find("div", class_="container posts")
    title_bar = post_container.find("div", class_="title-bar")
    thread_title = title_bar.find("h1").text

    thread = {
        "type": "thread",
        "announcement": announcement,
        "board_id": board_id,
        "id": thread_id,
        "locked": locked,
        "sticky": sticky,
        "title": thread_title,
        "url": url,
        "user_id": user_id,
        "views": views,
    }
    await manager.content_queue.put(thread)

    pages_remaining = True
    while pages_remaining:
        posts = post_container.findAll("tr", class_="post")

        for post_ in posts:
            # Each post <tr> tag has an id attribute of the form:
            # <tr id="post-1234">
            # where 1234 would be the post id.
            post_id = int(post_["id"].split("-")[1])

            # "left panel" contains info about the user who made the post.
            left_panel = post_.find("td", class_="left-panel")

            if guest_ := left_panel.find("span", class_="user-guest"):
                guest_user_name = guest_.text
                guest = {
                    "id": -1,
                    "name": guest_user_name,
                }

                # Get new guest user id.
                guest_db_obj = manager.db.insert_guest(guest)
                user_id = guest_db_obj.id
            else:
                # <a> tag href attribute is of the form "/user/5".
                user_link = left_panel.find("a", class_="user-link")
                user_id = int(user_link["href"].split("/")[-1])

            post_content = post_.find("td", class_="content")
            post_info = post_content.find("div", class_="info")

            date_abbr = post_info.find("span", class_="date").find("abbr")
            date = date_abbr["data-timestamp"]

            article = post_content.find("article")
            message_ = article.find("div", class_="message")
            message = "".join(str(child) for child in message_.children)

            last_edited = None
            edit_user_id = None

            edited_by = post_.find("div", class_="edited_by")
            if edited_by is not None:
                last_edited = edited_by.find("abbr")["data-timestamp"]
                edit_user_href = edited_by.find("a")["href"]
                edit_user_id = int(edit_user_href.split("/")[-1])

            post = {
                "type": "post",
                "id": post_id,
                "date": date,
                "edit_user_id": edit_user_id,
                "last_edited": last_edited,
                "message": message,
                "thread_id": thread_id,
                "url": f"{site_url}/post/{post_id}",
                "user_id": user_id,
            }
            await manager.content_queue.put(post)

            # Continue to next page, if any.
            control_bar = post_container.find("div", class_="control-bar")
            next_btn = control_bar.find("li", class_="next")

            if "state-disabled" in next_btn["class"]:
                pages_remaining = False
            else:
                next_href = next_btn.find("a")["href"]
                next_url = f"{site_url}{next_href}"
                source = await get_source(next_url, manager.client_session)
                post_container = source.find("div", class_="container posts")


async def scrape_board(
    url: str,
    manager: ScraperManager,
    category_id: int = None,
    moderators: List[int] = None,
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

    source = await get_source(url, manager.client_session)

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
        description = stats_container.find(
            "div", class_="board-description"
        ).text

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
    await manager.content_queue.put(board)

    if moderators:
        for user_id in moderators:
            moderator = {
                "type": "moderator",
                "user_id": user_id,
                "board_id": board_id,
            }
            await manager.content_queue.put(moderator)

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
                subboard_url, manager, category_id=category_id,
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

                views = int(thread_.find("td", class_="views").text)

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
                        "id": -1,
                        "name": guest_user_name,
                    }

                    # Get new guest user id.
                    guest_db_obj = manager.db.insert_guest(guest)
                    create_user_id = guest_db_obj.id
                else:
                    # The href attribute is of the form "/user/12".
                    created_by_href = created_by_tag.find("a")["href"]
                    create_user_id = int(created_by_href.split("/")[-1])

                clickable = thread_.find("td", class_="main clickable")
                anchor = clickable.find("span", class_="link target").find("a")
                thread_href = anchor["href"]
                thread_url = site_url + thread_href
                await scrape_thread(
                    thread_url, manager, board_id=board_id,
                    user_id=create_user_id, views=views,
                    announcement=announcement, locked=locked, sticky=sticky,
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
                source = await get_source(
                    next_page_url, manager.client_session
                )
                thread_container = source.find(
                    "div", class_="container threads"
                )


async def scrape_content(url: str, manager: ScraperManager):
    """
    Scrape all categories/boards from the main page.

    Args:
        url: Homepage URL.
    """
    source = await get_source(url, manager.client_session)
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

        await manager.content_queue.put(category)

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
                board_url, manager, category_id=category_id,
                moderators=moderator_ids
            )

    await manager.content_queue.put(None)


def scrape_site(
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

    # Get cookies for parts of the site requiring login authentication.
    url = url.rstrip("/")
    if username and password:
        logger.info(f"Logging in to {url}")
        cookies = get_login_cookies(url, username, password)

        # Create a persistent aiohttp login session from the cookies.
        client_session = get_login_session(cookies)
        logger.info("Login successful")
    else:
        logger.info(
            "Username and/or password not provided; proceeding without login"
        )
        client_session = aiohttp.ClientSession()

    tasks = []

    manager = ScraperManager(db, client_session, image_dir=image_dir)

    if skip_users:
        manager.user_queue = None
        logger.info("Skipping user profiles")
    else:
        users_task = scrape_users(url, manager)
        tasks.append(users_task)

    content_task = scrape_content(url, manager)
    tasks.append(content_task)

    database_task = manager.run()
    tasks.append(database_task)

    task_group = asyncio.gather(*tasks)
    asyncio.get_event_loop().run_until_complete(task_group)
