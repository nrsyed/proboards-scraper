import hashlib
import http
import imghdr
import logging
import pathlib
import time
from typing import List

import aiofiles
import aiohttp
import bs4
import selenium.webdriver


logger = logging.getLogger(__name__)


def test_ico(h: bytes, f):
    """
    Test for .ico files to be added to the ``imghdr`` module tests.
    See `ICO file format`_ and `imghdr.tests`_.

    .. _`ICO file format`: https://en.wikipedia.org/wiki/ICO_(file_format)
    .. _`imghdr.tests`:
        https://docs.python.org/3/library/imghdr.html#imghdr.tests
    """
    if h.startswith(b"\x00\x00") and (h[2:4] in (b"\x01\x00", b"\x02\x00")):
        return "ico"
imghdr.tests.append(test_ico)


def get_chrome_driver() -> selenium.webdriver.Chrome:
    """
    Returns an instance of a Selenium Chrome driver with the headless
    option set to ``True``.

    Returns: headless Chrome driver.
    """
    chrome_opts = selenium.webdriver.ChromeOptions()
    chrome_opts.headless = True
    driver = selenium.webdriver.Chrome(options=chrome_opts)
    return driver


def get_login_cookies(
    home_url: str, username: str, password: str,
    driver: selenium.webdriver.Chrome = None, page_load_wait: int = 1
) -> List[dict]:
    """
    Logs in to a Proboards account using Selenium and returns the cookies from
    the authenticated login session.

    Args:
        home_url: URL for the Proboards forum homepage.
        username: Login username.
        password: Login password.
        driver: Selenium Chrome driver (optional).
        page_load_wait: Time (in seconds) to wait to allow the page to load.

    Returns:
        A list of dicts, where each dict corresponds to a cookie, from the
        Selenium Chrome driver.
    """
    if driver is None:
        driver = get_chrome_driver()

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
        except Exception:
            pass

    email_input.send_keys(username)
    password_input.send_keys(password)
    submit_input.click()
    time.sleep(page_load_wait)

    cookies = driver.get_cookies()
    return cookies


def get_login_session(cookies: List[dict]) -> aiohttp.ClientSession:
    """
    Get an authenticated ``aiohttp`` session using the cookies provided.

    This is achieved by converting cookies from a Selenium driver session
    to ``http`` module Morsels (see `http.cookies.Morsel`_), which can be
    added to the ``aiohttp`` session's cookie jar.

    Args:
        cookies: A list of dicts as returned by :func:`get_login_cookies`,
            i.e., from a Selenium driver session.

    Returns: An ``aiohttp`` session with the given cookies in its cookie jar.

    .. _`http.cookies.Morsel`:
        https://docs.python.org/3/library/http.cookies.html#morsel-objects
    """
    logger.debug("Creating aiohttp login session from cookies")
    session = aiohttp.ClientSession()

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
        # if "expiry" in cookie:
        #     morsel["expires"] = cookie["expiry"]

        morsels[cookie["name"]] = morsel

    session.cookie_jar.update_cookies(morsels)

    logger.debug("Added cookies to aiohttp session")
    return session


async def get_source(
    url: str, session: aiohttp.ClientSession
) -> bs4.BeautifulSoup:
    """
    Get page source of a URL.

    Args:
        url: URL to visit.
        session: ``aiohttp`` session.

    Returns: Page source.
    """
    logger.debug(f"Getting page source for {url}")
    # TODO: check response HTTP status code
    resp = await session.get(url)
    text = await resp.text()
    return bs4.BeautifulSoup(text, "html.parser")


async def download_image(
    url: str, session: aiohttp.ClientSession, dst_dir: pathlib.Path
) -> dict:
    """
    Attempt to download the image at ``url`` to the directory specified by
    ``dst_dir``. The downloaded file is named after its MD5 hash to ensure
    uniqueness. If a file already exists on disk (i.e., has been previously
    downloaded), it is not rewritten.

    Args:
        url: Image URL.
        session: ``aiohttp`` session.
        dst_dir: Directory to which the image should be downloaded.

    Returns:
        A dict containing information on the download attempt and, if download
        was successful, image metadata::

            {
                "status": {
                    "get": HTTP response code,
                    "exists": whether the image already exists on disk (bool),
                    "valid": whether the file is a valid image file,
                },
                "image": {
                    "url": image download URL,
                    "filename": downloaded image filename,
                    "md5_hash": file MD5 hash,
                    "size": filesize on disk,
                },
            }
    """
    if url.startswith("//"):
        url = f"https:{url}"

    logger.debug(f"Downloading image: {url}")

    ret = {
        "status": {
            "get": None,
            "exists": None,
            "valid": None
        },
        "image": {
            "url": url,
            "filename": None,
            "md5_hash": None,
            "size": None,
        },
    }

    try:
        response = await session.get(url, timeout=45)
    except aiohttp.client_exceptions.ClientConnectorError as e:
        logger.warning(
            f"Failed to download image at {url}: {str(e)} "
            "(it is likely the image or server no longer exists)"
        )
    else:
        ret["status"]["get"] = response.status

        if response.status == 200:
            img = await response.read()

            # The file extension doesn't necessarily match the filetype, so we
            # manually check the file header and set the correct extension. If
            # the file doesn't correspond to a supported image filetype, we
            # assume the downloaded file is invalid and skip it.
            ret["status"]["valid"] = False

            filetype = imghdr.what(None, h=img)

            if filetype == "jpeg":
                filetype = "jpg"

            if filetype is not None:
                ret["status"]["valid"] = True

                # Set the filestem to the md5 hash of the image.
                img_md5 = hashlib.md5(img).hexdigest()

                new_fname = f"{img_md5}.{filetype}"

                ret["image"]["filename"] = new_fname
                ret["image"]["size"] = len(img)
                ret["image"]["md5_hash"] = img_md5

                img_fpath = dst_dir / new_fname

                if not img_fpath.exists():
                    ret["status"]["exists"] = False
                    async with aiofiles.open(img_fpath, "wb") as f:
                        await f.write(img)
                else:
                    ret["status"]["exists"] = True
    finally:
        return ret
