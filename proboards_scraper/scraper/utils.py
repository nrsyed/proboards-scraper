import re
from typing import Tuple


def int_(num: str) -> int:
    """
    Take an integer in the form of a string, remove any commas from it,
    then return it as an ``int``.

    Args:
        num: A string containing only numeric characters or commas.

    Returns:
        An integer version of the string.
    """
    return int(num.replace(",", ""))


def split_url(url: str) -> Tuple[str, str]:
    """
    Given a forum page URL like, e.g.,
    `https://yoursite.proboards.com/board/3/board-name`, return the base URL
    (`https://yoursite.proboards.com`) and resource path component
    (`board/3/board-name`).

    Site/page URLs take the following forms:

    * Homepage: https://yoursite.proboards.com/
    * Board: https://yoursite.proboards.com/board/3/board-name
    * Thread: https://yoursite.proboards.com/thread/123/thread-title
    * Users: https://yoursite.proboards.com/members
    * User: https://yoursite.proboards.com/user/10

    Args:
        url: URL to a forum page.

    Returns:
        :data:`(base_url, path)`

        The base URL and resource path URL component (or ``None`` if ``url``
        is just the base/homepage URL).
    """
    url = url.rstrip("/")
    expr = r"(^.*\.com)(/.*)?$"
    match = re.match(expr, url)
    base_url, path = match.groups()
    return base_url, path
