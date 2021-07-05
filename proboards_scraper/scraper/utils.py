import re
from typing import Tuple


def int_(num: str) -> int:
    """
    Take an integer in the form of a string, remove any commas from it,
    then return it as an ``int``.
    """
    return int(num.replace(",", ""))


def split_url(url: str) -> Tuple[str, str]:
    """
    Take a forum page URL and return the base URL (e.g.,
    `https://yoursite.proboards.com`) and resource path component (e.g.,
    `board/3/boardname`).

    Site/page URLs take the following forms:
    Homepage: https://yoursite.proboards.com/
    Board: https://yoursite.proboards.com/board/3/boardname
    Thread: https://yoursite.proboards.com/thread/123/threadname
    Users: https://yoursite.proboards.com/members
    User: https://yoursite.proboards.com/user/10

    Args:
        url: URL to a forum page.

    Returns:
        The base URL and resource path URL component (or ``None`` if ``url``
        is just the base/homepage URL).
    """
    url = url.rstrip("/")
    expr = r"(^.*\.com)(/.*)?$"
    match = re.match(expr, url)
    base_url, path = match.groups()
    return base_url, path
