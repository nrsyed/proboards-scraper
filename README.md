# ProBoards Forum Scraper

* [Disclaimer](#disclaimer)
* [Overview](#overview)
* [Installation](#installation)
* [Quickstart](#quickstart)
  - [Scraper command-line tool](#quickstart-pbs)
  - [Database command-line tool](#quickstart-pbd)
* [Usage](#usage)
  - [ProBoards Scraper tool](#pbs)
  - [ProBoards Scraper Database tool](#pbd)


# Disclaimer

**It is against [ProBoards's Terms of Service](https://www.proboards.com/tos)
to scrape content from a ProBoards forum. The code in this repository is purely
for educational purposes, i.e., to demonstrate the use of various libraries and
techniques, and should NOT be used to scrape any ProBoards forum or website.**

**Neither the author(s) nor this repository have any affiliation or association
with ProBoards.**

**Per the license included in this repository, this software is provided
"as is" without warranty of any kind and is not guaranteed to work. Neither
the author(s) nor the software shall be held liable for any consequences
resulting from its use.**

# Overview

The purpose of this package is, as the disclaimer above states, to
demonstrate the use of various Python modules/packages and various
web-scraping techniques. It is designed to crawl a forum in a top-down
manner and store user profiles, categories, boards, threads, polls, posts,
shoutbox posts, post smileys, user avatars, and the site background/banner
images primarily in a SQLite database. Scraping is achieved via a
combination of BeautifulSoup and Selenium, and sqlalchemy is used to
interface with the SQLite database. Because the majority of this task
involves HTTP requests and network I/O, the forum is scraped asynchronously
using `asyncio`, `aiohttp`, and `aiofiles`.


# Installation

```
git clone git@github.com:nrsyed/proboards-scraper.git
cd proboards-scraper
pip install .
```

# Quickstart

<span id="quickstart-pbs"></span>
## Scraper command-line tool

Scraping is performed via the `pbs` (**P**ro**B**oards **S**craper) command
line tool. Login is *not* required to scrape a site. If authentication
credentials, i.e., username and password, are not provided, the program will
proceed without logging in and any password-protected areas of the site will
not be scraped. The following examples demonstrate basic use of the `pbs`
command.

```
# Scrape the entire forum.
pbs https://yoursite.proboards.com -u user -p pass

# Scrape all user profiles.
pbs https://yoursite.proboards.com/members -u user -p pass

# Scrape a specific user's profile.
pbs https://yoursite.proboards.com/user/4 -u user -p pass

# Scrape a specific board (including all its threads and sub-boards).
pbs https://yoursite.proboards.com/board/2/boardname -u user -p pass

# Scrape a specific thread.
pbs https://yoursite.proboards.com/thread/123/thread-title -u user -p pass
```

By default, the command stores files in `./site`, with the database file named
`forum.db` and all downloaded images stored in `./site/images`:

```
site
├── forum.db
└── images
    ├── 0109df55a94edf945e04bfa1ac494133.png
    ├── 44af035a39a673cce28d10d2c7a7ef0.gif
    ├── 791ec775aa570e88734cf9e83c4105966.ico
    └── fd0d26b36a29dc621b7aebd1a4d5a0d7.jpg
```

The output directory can be changed from `./site` with the `-o`/`--output` option:

```
pbs https://yoursite.proboards.com -o /path/to/directory
```

<span id="quickstart-pbd"></span>
## Database command-line tool

The package includes a simple command line utility for querying the database
with `pbd` (**P**ro**B**oards Scraper **D**atabase).

```
# Print all boards.
pbd -b

# Print detailed information (sub-boards, thread list, etc.) for a
# specific board id.
pbd -b 2

# Print a list of all threads.
pbd -t

# Print detailed information (poll, posts) for a specific thread id.
pbd -t 500

# Print a list of all users, including guests.
pbd -u

# Print detailed information about a specific user id.
pbd -u 23
```

The tool assumes the database is located at `./site/forum.db` by default, but
a different database file can be specified with the `-d`/`--database` option:

```
pbd -d /path/to/database.db -u 23
```

# Usage

## pbs

The **P**\ ro\ **B**\ oards **S**\ craper command line tool `pbs` can be
used to scrape part or all of a ProBoards forum.

```
usage: pbs [-h] [-u USERNAME] [-p PASSWORD] [-o <path>] [-D] [-U]
           [-v {0,1,2,3,4,5}] url

positional arguments:
  url                   URL for either the main page, a board, a thread, or
                        a user

optional arguments:
  -h, --help            show this help message and exit
  -o <path>, --output <path>
                        Path to output directory containing database and
                        site files (default ./site)
  -D, --no-delay        Do not rate limit requests
  -U, --no-users        Do not grab user profiles (only use this option if
                        a database exists and users have already been added
                        to it)
  -v {0,1,2,3,4,5}, --verbosity {0,1,2,3,4,5}
                        Verbosity level from 0 (silent) to 5 (full debug);
                        default 2

Login arguments:
  -u USERNAME, --username USERNAME
                        Login username
  -p PASSWORD, --password PASSWORD
                        Login password
```

## pbd

The **P**\ ro\ **B**\ oards Scraper **D**\ atabase command line tool `pbd`
can be used to perform simple queries on the database generated from scraping
the site via the `pbs` command line tool.

```
usage: pbd [-h] [-d <path>]
(--board [board_id] | --user [user_id] | --thread [thread_id])

optional arguments:
  -h, --help            show this help message and exit
  -d <path>, --database <path>
                        Path to database file; default ./site/forum.db
  --board [board_id], -b [board_id]
                        Board id; if omitted, list all boards
  --user [user_id], -u [user_id]
                        User id; if omitted, list all users
  --thread [thread_id], -t [thread_id]
                        Thread id; if omitted, list all threads
```
