pbd
===

The **P**\ ro\ **B**\ oards Scraper **D**\ atabase command line tool ``pbd``
can be used to perform simple queries on the database generated from scraping
the site via the :doc:`pbs` command line tool.

Usage
-----

.. code-block:: none

  usage: pbd [-h] [-d <path>] (--user [user_id] | --board [board_id] | --thread [thread_id])

  optional arguments:
    -h, --help            show this help message and exit
    -d <path>, --database <path>
                          Path to database file
    --user [user_id], -u [user_id]
    --board [board_id], -b [board_id]
    --thread [thread_id], -t [thread_id]

Examples
--------
