Overview
========

The purpose of this package is to demonstrate the use of various Python
modules/packages and web-scraping techniques. It is designed to crawl a forum
in a top-down manner and store user profiles, categories, boards, threads,
polls, posts, shoutbox posts, post smileys, user avatars, and the site
background/banner images primarily in a SQLite database. Scraping is
achieved via a combination of BeautifulSoup and Selenium, and sqlalchemy is
used to interface with the SQLite database. Because the majority of this task
involves HTTP requests and network I/O, the forum is scraped asynchronously
using `asyncio`, `aiohttp`, and `aiofiles`.


Disclaimer
----------

It is against the `ProBoards Terms of Service`_ to scrape content from a
ProBoards forum. This code is purely for educational purposes, i.e., to
demonstrate the use of various libraries and techniques, and should NOT be
used to scrape any ProBoards forum or website.

Neither the author(s) nor this software have any affiliation or association
with ProBoards.

Per the license included in the repository, this software is provided
"as is" without warranty of any kind and is not guaranteed to work. Neither
the author(s) nor the software shall be held liable for any consequences
resulting from its use.

.. _`Proboards Terms of Service`: https://www.proboards.com/tos
