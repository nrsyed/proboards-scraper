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

Examples
--------
