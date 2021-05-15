from concurrent.futures import ThreadPoolExecutor
import pathlib
import queue
import requests
import sys
import threading
import time
import urllib.request

import bs4
import selenium.webdriver


#https://stackoverflow.com/questions/51682341/how-to-send-cookies-with-urllib

def process_queues(
    db_path: pathlib.Path, user_queue: queue.Queue, content_queue: queue.Queue
):
    """
    Add all users followed by all content (boards, threads, posts) to the
    given database. This function first consumes all users to the database,
    since users are referenced in all content. Subsequently, it adds all
    content to the database.

    Because content is heirarchical, each content type (board, thread, post)
    need not be given its own queue, i.e., a board will be added to the
    ``content_queue`` before any of its threads, and a thread will be added
    to the queue before any of its posts; therefore, we don't have to worry
    about a post being added before the thread it belongs to has been added,
    for example.
    """
    pass


def get_login_session(
    home_url: str, username: str, password: str, page_load_wait: int = 1
) -> requests.sessions.Session:
    chrome_opts = selenium.webdriver.ChromeOptions()
    chrome_opts.headless = True
    driver = selenium.webdriver.Chrome(options=chrome_opts)
    driver.get(home_url)
    time.sleep(page_load_wait)

    #home_source = bs4.BeautifulSoup(driver.page_source, "html.parser")
    #links = home_source.findAll("a")
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
            pass

    email_input.send_keys(username)
    password_input.send_keys(password)
    submit_input.click()
    time.sleep(1)

    # Get cookies from selenium driver and add to requests session.
    cookies = driver.get_cookies()
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


def get_source(url):
    with urllib.request.urlopen(url) as response:
        source = response.read()
    return bs4.BeautifulSoup(source, "html.parser")

def scrape_board(board: bs4.element.Tag):
    subboards = board.find("div", class_="container boards")
    if subboards:
        breakpoint()

def scrape_category(category: bs4.element.Tag):
    title_bar = category.find("div", class_="title_wrapper")
    title = title_bar.text
    boards = category.find("tbody").findAll("tr")

    for board in boards:
        #scrape_board(board)
        breakpoint()

def _get_user_urls(source: bs4.BeautifulSoup):
    members_container = source.find("div", class_="container members")
    x = members_container
    breakpoint()
    members_table = members_container.find("tbody").findAll("tr")
    x = members_table

def scrape_users(url: str):
    source = get_source(url)
    user_urls = _get_user_urls(source)

def scrape_site(url: str):
    members_url = f"{url}/members"
    scrape_users(members_url)

    #source = get_source(url)
    #categories = source.findAll("div", class_="container boards")

    #for category in categories:
    #    scrape_category(category)
