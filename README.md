# ProBoards Forum Scraper

## Disclaimer

**It is against
[ProBoards's Terms of Service](https://www.proboards.com/tos)
to scrape content from a ProBoards forum. The code in this repository is purely
for educational purposes, i.e., to demonstrate the use of various libraries and
techniques, and should NOT be used to scrape any ProBoards forum or website,
even though ProBoards does not offer the option, paid or otherwise, for forum
owners and administrators to export their site.**

**Neither I (the author) nor this repository have any affiliation or association
with ProBoards.**

**Per the license included in this repository, this software is provided
"as is" without warranty of any kind and is not guaranteed to work, and neither
the author nor the software shall be held liable for any consequences
resulting from its use.**

# Overview

The purpose of this package is, as the disclaimer above states, to
demonstrate the use of various Python modules/packages and various
web-scraping techniques. It is designed to crawl a forum in a top-down
manner and store user profiles, categories, boards, threads, polls, posts,
shoutbox posts, post smileys, user avatars, and the site background/banner
images in a SQLite database. Scraping is achieved via a
combination of BeautifulSoup and Selenium, and sqlalchemy is used to
interface with the SQLite database. Because the majority of this task
involves HTTP requests and network I/O, the forum is scraped asynchronously
using `asyncio`, `aiohttp`, and `aiofiles`.
