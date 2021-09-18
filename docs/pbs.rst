pbs
===

The **P**\ ro\ **B**\ oards **S**\ craper command line tool ``pbs`` can be
used to scrape part or all of a ProBoards forum.

Usage
-----

.. code-block:: none

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
    -U, --no-users        Do not grab user profiles (only use this options if
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

Required arguments
------------------

* ``url``: The URL for the forum homepage, users page, a user profile, a board,
  or a thread to be scraped. See the ``url`` parameter of
  :func:`proboards_scraper.run_scraper` for more information.

Optional arguments
------------------

* ``-u``/``--username``: Optional login username; must be used with
  ``--password``. Login credentials are optional, but password-protected or
  members-only pages cannot be accessed without them.

* ``-p``/``--password``: See ``--username``.

* ``-o``/``--output``: Path to the output directory where the database and
  any downloaded files (e.g., images) will be written. The SQLite database
  file will written to `forum.db`, images will be written to a subdirectory
  named `images`, and scraper logging output will be written to a subdirectory
  named `logs`.

* ``-D``/``--no-delay``: This flag disables rate-limiting by the scraper.
  See the ``request_threshold``, ``short_delay_time``, and ``long_delay_time``
  attributes of :class:`proboards_scraper.ScraperManager` for more
  information on rate-limiting values and behavior.

.. warning::
  Disabling delays between requests may result in request throttling or being
  blocked by the server.
  

* ``-U``/``--no-users``: This flag disables the users page from being scraped
  when the forum homepage URL is given for ``url``. This might be desirable if
  a previous attempt to scrape the site was interrupted (after all users from
  the members page have been scraped but before scraping of the rest of the
  site completed) to avoid going through the user profiles again.

* ``-v``/``--verbosity``: This argument controls the amount of logging output.
  The logging behavior is defined in
  :func:`proboards_scraper.__main__.configure_logging`.


Examples
--------

Scrape the entire forum
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: none

  pbs https://yoursite.proboards.com -u user -p pass

Scrape all user profiles
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: none

  pbs https://yoursite.proboards.com/members -u user -p pass

Scrape a specific user's profile
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: none

  pbs https://yoursite.proboards.com/user/4 -u user -p pass

Scrape a specific board
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: none

  pbs https://yoursite.proboards.com/board/2/boardname -u user -p pass

.. note::
  This scrapes all threads in the board and recursively scrapes any sub-boards.

Scrape a specific thread
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: none

  pbs https://yoursite.proboards.com/thread/123/thread-title -u user -p pass
