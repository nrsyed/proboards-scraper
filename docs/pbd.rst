pbd
===

The **P**\ ro\ **B**\ oards Scraper **D**\ atabase command line tool ``pbd``
can be used to perform simple queries on the database generated from scraping
the site via the :doc:`pbs` command line tool.

Usage
-----

.. code-block:: none

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

Optional arguments
------------------

* ``-d``/``--database``: Path to the SQLite database file (`./site/forum.db`
  by default). See the ``--output`` option of :doc:`pbs` for more on writing
  the site files to a different directory.

* ``-b``/``--board``: If this option is selected without providing a board id,
  a list of all boards is printed. If a board id is provided, a list of all
  threads in the given board are printed.

* ``-u``/``--user``: If this option is selected without providing a user id,
  a list of all users is printed. If a user id is provided, information about
  the given user is printed.

* ``-t``/``--thread``: If this option is selected without providing a thread
  id, a list of all threads on the forum is printed. If a thread id is
  provided, a list of all posts in the given thread is printed.

.. note:: One of ``--board``, ``--user``, or ``--thread`` is required.

Examples
--------

Display a list of all boards
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample command:

.. code-block:: none

  pbd -b

Sample output:

.. code-block:: none

  1: Media
  2: Announcements
  3: Lounge
  4: Writer's Room

Display information about a specific board
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample command:

.. code-block:: none

  pbd -b 3

Sample output:

.. code-block:: none

  {'category_id': 1,
   'description': 'A place to talk about anything',
   'id': 3,
   'moderators': ['SnakeShake', 'Tom'],
   'name': 'Lounge',
   'num_threads': 4,
   'parent_id': None,
   'password_protected': None,
   'posts': 50,
   'sub_boards': [1],
   'threads': [{'num_posts': 2, 'thread_id': 1, 'title': 'Welcome!'},
               {'num_posts': 31, 'thread_id': 5, 'title': 'Hobbies'},
               {'num_posts': 3, 'thread_id': 6, 'title': 'Favorite sports'},
               {'num_posts': 4, 'thread_id': 8, 'title': 'Podcasts'}],
   'url': 'https://yoursite.proboards.com/board/3/lounge'}

.. seealso:: :class:`proboards_scraper.database.Board`

Display a list of all users
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample command:

.. code-block:: none

  pbd -u

Sample output:

.. code-block:: none

  -2: bob
  -1: guest1
  1: SnakeShake
  2: Tom
  3: patrick_jane

.. note::
  Guests receive negative user ids in the database. Refer to
  :meth:`proboards_scraper.database.Database.insert_guest` for more
  information.

Display information about a specific user
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample command:

.. code-block:: none

  pbd -u 1

Sample output:

.. code-block:: none

  {'age': 30,
   'avatar': {'filename': '5adac452f7eedc7e1abcec513750a139.jpg',
              'url': 'http://img.photobucket.com/albums/v10/snake/vegeta.jpg'},
   'birthdate': 'January 1, 1991',
   'date_registered': 1090902497000,
   'email': 'snake@snakemail.com',
   'gender': 'Male',
   'group': 'Administrator',
   'id': 1,
   'instant_messengers': 'AIM:snak3_p1i55k3n',
   'last_online': 1625547390000,
   'latest_status': '',
   'location': 'LA',
   'name': 'SnakeShake',
   'post_count': 250,
   'signature': None,
   'url': 'https://yoursite.proboards.com/user/1',
   'username': 'snakep123',
   'website': None,
   'website_url': None}

.. seealso:: :class:`proboards_scraper.database.User`

Display a list of all threads
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample command:

.. code-block:: none

  pbd -t

Sample output:

.. code-block:: none

  ['1: Welcome!',
   '2: worst tv show',
   '3: ABC game',
   '4: Short story practice',
   '5: Hobbies',
   '6: Favorite sports',
   '7: Forum Rules',
   '8: Podcasts']

Display all posts in a specific thread
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample command:

.. code-block:: none

  pbd -t 2

Sample output:

.. code-block:: none

  {'announcement': False,
   'board_id': 1,
   'id': 2,
   'locked': False,
   'posts': [{'date': 1089681705000,
              'edit_user_id': None,
              'id': 402,
              'last_edited': None,
              'message': "What's the worst TV show? IMO it's the bachelor",
              'thread_id': 2,
              'url': 'https://yoursite.proboards.com/post/12',
              'user_id': 1},
             {'date': 1089697194000,
              'edit_user_id': None,
              'id': 403,
              'last_edited': None,
              'message': 'No way, I love the bachelor!',
              'thread_id': 2,
              'url': 'https://yoursite.proboards.com/post/13',
              'user_id': 3},
   'sticky': False,
   'title': 'worst tv show',
   'url': 'https://yoursite.proboards.com/thread/2/worst-tv-show',
   'user_id': 1,
   'views': 310}

.. seealso::
  :class:`proboards_scraper.database.Thread`

  :class:`proboards_scraper.database.Post`
