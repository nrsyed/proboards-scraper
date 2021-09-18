import logging
import pathlib
from typing import List, Optional, Tuple, Union

import sqlalchemy
import sqlalchemy.orm

from .schema import (
    Base, Avatar, Board, Category, CSS, Image, Moderator, Poll, PollOption,
    PollVoter, Post, ShoutboxPost, Thread, User
)


logger = logging.getLogger(__name__)


def serialize(
    obj: Union[sqlalchemy.orm.DeclarativeMeta, list]
) -> Union[dict, List[dict]]:
    """
    Helper function that recursively serializes a database table object
    (or list of objects) and returns them as Python dictionaries.

    Args:
        obj: A sqlalchemy Metaclass instance, i.e., one of:

            * :class:`Avatar`
            * :class:`Board`
            * :class:`Category`
            * :class:`CSS`
            * :class:`Image`
            * :class:`Moderator`
            * :class:`Poll`
            * :class:`PollOption`
            * :class:`PollVoter`
            * :class:`Post`
            * :class:`ShoutboxPost`
            * :class:`Thread`
            * :class:`User`

    Returns: Serialized version of the object (or list of objects).
    """
    if isinstance(
        obj,
        (
            Board, Category, Image, Poll, PollOption, PollVoter, Post, Thread,
            User
        )
    ):
        dict_ = {}
        for k, v in vars(obj).items():
            if not k.startswith("_"):
                dict_[k] = serialize(v)

        # association_proxy._AssociationList and collections.InstrumentedList
        # objects are not in Board.__dict__ and must be separately serialized.
        if isinstance(obj, Board):
            dict_["moderators"] = serialize(list(obj.moderators))
        elif isinstance(obj, Poll):
            dict_["options"] = serialize(list(obj.options))
            dict_["voters"] = serialize(list(obj.voters))
        elif isinstance(obj, Thread):
            dict_["posts"] = serialize(list(obj.posts))
        elif isinstance(obj, User):
            avatar_ = None
            if obj.avatar:
                avatar = serialize(obj.avatar[0])
                avatar_ = {
                    "filename": avatar["filename"],
                    "url": avatar["url"],
                }
            dict_["avatar"] = avatar_

        return dict_
    elif isinstance(obj, list):
        return [serialize(item) for item in obj]
    else:
        return obj


class Database:
    def __init__(self, db_path: pathlib.Path):
        """
        This class serves as an interface for the SQLite database, and allows
        items to be inserted/updated or queried using a variety of specific
        functions that abstract away implementation details of the database
        and its schema.

        Args:
            db_path: Path to SQLite database file.
        """
        engine_str = f"sqlite:///{db_path}"
        engine = sqlalchemy.create_engine(engine_str)
        Session = sqlalchemy.orm.sessionmaker(engine)
        session = Session()
        Base.metadata.create_all(engine)

        self.engine = engine
        self.session = session

    def _insert_log_msg(self, item_desc: str, inserted: int) -> None:
        """
        TODO

        Args:
            item_desc: Item description.
            inserted: Whether the item was updated (2), added (1), or not
                added (0) to the database.
        """
        if inserted == 0:
            logger.info(f"{item_desc} already exists in database")
        elif inserted == 1:
            logger.info(f"{item_desc} added to database")
        elif inserted == 2:
            logger.info(f"{item_desc} database entry was updated")

    def insert(
        self, obj: sqlalchemy.orm.DeclarativeMeta,
        filters: dict = None,
        update: bool = False
    ) -> Tuple[int, sqlalchemy.orm.DeclarativeMeta]:
        """
        Query the database for an object of the given sqlalchemy Metaclass
        using the given ``filters`` to determine if it already exists in the
        database. If it doesn't, insert it into the database. Either way,
        return a bool indicating whether the object was added, as well as the
        resulting object from the query.

        Although this method can be called directly, it is preferable to call
        the corresponding `insert_*` or `query_*` wrapper methods instead,
        which simplify the task of querying/inserting into the database.

        Args:
            obj: A sqlalchemy Metaclass instance corresponding to a
                database table class, i.e., an instance of one of:

                * :class:`Avatar`
                * :class:`Board`
                * :class:`Category`
                * :class:`CSS`
                * :class:`Image`
                * :class:`Moderator`
                * :class:`Poll`
                * :class:`PollOption`
                * :class:`PollVoter`
                * :class:`Post`
                * :class:`ShoutboxPost`
                * :class:`Thread`
                * :class:`User`

            filters: A dict of key/value pairs on which to filter the query
                results. The keys should correspond to the attributes of the
                Metaclass, i.e., attributes of the ``obj`` argument class.
                See example below. If ``filters`` is ``None``, it defaults to
                the ``id`` attribute of ``obj``, i.e., ``obj.id``.
            update: Whether to update the database entry if the queried object
                already exists.

        Example:
            The following example demonstrates how to insert a new user into
            the database. Note that we first create an instance of the user
            (which is passed to :meth:`insert`) and filter by the user id
            (which is the :class:`User` table primary key). In other words,
            this searches the database for an existing user with the given
            filter (i.e., the user with id 7) and, if the user doesn't exist,
            inserts it into the database, then returns the inserted object:

            .. code-block:: python

                user_data = {
                    "id": 7,
                    "date_registered": 1631019126,
                    "email": "foo@bar.com",
                    "name": "Snake Plissken",
                    "username": "snake",
                }
                
                new_user = User(**user_data)
                
                db = Database("forum.db")
                inserted, new_user = db.insert(
                    new_user,
                    filters={"id": 7}
                )

        Returns:
            :data:`(inserted, ret)`

            * inserted:
                An integer code denoting insert status.

                * 0: The object failed to be inserted or updated.
                * 1: ``obj`` was inserted into the database.
                * 2: ``obj`` existed in the database and was updated.
            * ret:
                The inserted object, if the object didn't previously
                exist in the database, or the existing object if it did
                already exist. It is effectively an updated version of
                ``obj``.
        """
        if filters is None:
            filters = {"id": obj.id}

        Metaclass = type(obj)
        result = self.session.query(Metaclass).filter_by(**filters).first()

        inserted = 0
        if result is None:
            self.session.add(obj)
            self.session.commit()
            inserted = 1
            ret = obj
        elif result is not None and update:
            for attr, val in vars(obj).items():
                if not attr.startswith("_"):
                    setattr(result, attr, val)
            self.session.commit()
            inserted = 2
            ret = result
        else:
            ret = result
        return inserted, ret

    def insert_avatar(self, avatar_: dict, update: bool = False) -> Avatar:
        """
        Insert a user avatar into the database; this method wraps
        :meth:`insert`.

        Args:
            avatar\_: A dict containing the keyword args (attributes) needed to
                instantiate a :class:`Avatar` object.
            update: See :meth:`insert`.

        Returns:
            The inserted (or updated) :class:`Avatar` object.
        """
        avatar = Avatar(**avatar_)
        filters = {
            "image_id": avatar.image_id,
            "user_id": avatar.user_id,
        }
        inserted, avatar = self.insert(avatar, filters=filters, update=update)
        self._insert_log_msg(f"Avatar for user {avatar.user_id}", inserted)
        return avatar

    def insert_board(self, board_: dict, update: bool = False) -> Board:
        """
        Insert a board into the database; this method wraps :meth:`insert`.

        Args:
            board\_: A dict containing the keyword args (attributes) needed to
                instantiate a :class:`Board` object.
            update: See :meth:`insert`.

        Returns:
            The inserted (or updated) :class:`Board` object.
        """
        board = Board(**board_)
        inserted, board = self.insert(board, update=update)
        self._insert_log_msg(f"Board {board.name}", inserted)
        return board

    def insert_category(
        self, category_: dict, update: bool = False
    ) -> Category:
        """
        Insert a category into the database; this method wraps :meth:`insert`.

        Args:
            category\_: A dict containing the keyword args (attributes) needed
                to instantiate a :class:`Category` object.
            update: See :meth:`insert`.

        Returns:
            The inserted (or updated) :class:`Category` object.
        """
        category = Category(**category_)
        inserted, category = self.insert(category, update=update)
        self._insert_log_msg(f"Category {category.name}", inserted)
        return category

    def insert_image(self, image_: dict, update: bool = False) -> Image:
        """
        Insert an image into the database; this method wraps :meth:`insert`.

        Args:
            image\_: A dict containing the keyword args (attributes) needed
                to instantiate a :class:`Image` object.
            update: See :meth:`insert`.

        Returns:
            The inserted (or updated) :class:`Image` object.
        """
        image = Image(**image_)

        # To determine if the image already exists in the database, search by
        # its md5 hash. If the image couldn't be downloaded (e.g., because its
        # URL no longer exists), we will have no md5 hash information and
        # should search by its URL instead.
        if image.md5_hash is not None:
            filters = {"md5_hash": image.md5_hash}
        else:
            filters = {"url": image.url}

        inserted, image = self.insert(image, filters=filters, update=update)
        self._insert_log_msg(f"Image {image.url}", inserted)
        return image

    def insert_moderator(
        self, moderator_: dict, update: bool = False
    ) -> Moderator:
        """
        Insert a moderator into the database; this method wraps :meth:`insert`.

        Args:
            moderator\_: A dict containing the keyword args (attributes) needed
                to instantiate a :class:`Moderator` object.
            update: See :meth:`insert`.

        Returns:
            The inserted (or updated) :class:`Moderator` object.
        """
        moderator = Moderator(**moderator_)
        filters = {
            "user_id": moderator.user_id,
            "board_id": moderator.board_id,
        }
        inserted, moderator = self.insert(
            moderator, filters=filters, update=update
        )
        self._insert_log_msg(
            f"Moderator ({moderator.user_id}, board {moderator.board_id})",
            inserted
        )
        return moderator

    def insert_poll(self, poll_: dict, update: bool = False) -> Poll:
        """
        Insert a poll into the database; this method wraps :meth:`insert`.

        Args:
            poll\_: A dict containing the keyword args (attributes) needed
                to instantiate a :class:`Poll` object.
            update: See :meth:`insert`.

        Returns:
            The inserted (or updated) :class:`Poll` object.
        """
        poll = Poll(**poll_)
        inserted, poll = self.insert(poll, update=update)
        self._insert_log_msg(f"Poll from thread {poll.id}", inserted)
        return poll

    def insert_poll_option(
        self, poll_option_: dict, update: bool = False
    ) -> PollOption:
        """
        Insert a poll option into the database; this method wraps
        :meth:`insert`.

        Args:
            poll_option\_: A dict containing the keyword args (attributes)
                needed to instantiate a :class:`PollOption` object.
            update: See :meth:`insert`.

        Returns:
            The inserted (or updated) :class:`PollOption` object.
        """
        poll_option = PollOption(**poll_option_)
        inserted, poll_option = self.insert(poll_option, update=update)
        self._insert_log_msg(f"Poll option {poll_option.id}", inserted)
        return poll_option

    def insert_poll_voter(
        self, poll_voter_: dict, update: bool = False
    ) -> PollVoter:
        """
        Insert a poll voter into the database; this method wraps
        :meth:`insert`.

        Args:
            poll_voter\_: A dict containing the keyword args (attributes) needed
                to instantiate a :class:`PollVoter` object.
            update: See :meth:`insert`.

        Returns:
            The inserted (or updated) :class:`PollVoter` object.
        """
        poll_voter = PollVoter(**poll_voter_)
        filters = {
            "poll_id": poll_voter.poll_id,
            "user_id": poll_voter.user_id,
        }
        inserted, poll_voter = self.insert(
            poll_voter, filters=filters, update=update
        )
        self._insert_log_msg(
            f"Poll voter (thread {poll_voter.poll_id}, "
            f"user {poll_voter.user_id})",
            inserted
        )
        return poll_voter

    def insert_post(self, post_: dict, update: bool = False) -> Post:
        """
        Insert a post into the database; this method wraps :meth:`insert`.

        Args:
            post\_: A dict containing the keyword args (attributes) needed to
                instantiate a :class:`Post` object.
            update: See :meth:`insert`.

        Returns:
            The inserted (or updated) :class:`Post` object.
        """
        post = Post(**post_)
        inserted, post = self.insert(post, update=update)
        self._insert_log_msg(
            f"Post {post.id} (thread {post.thread_id}, user {post.user_id})",
            inserted)
        return post

    def insert_shoutbox_post(
        self, shoutbox_post_: dict, update: bool = False
    ) -> ShoutboxPost:
        """
        Insert a shoutbox post into the database; this method wraps
        :meth:`insert`.

        Args:
            shoutbox_post\_: A dict containing the keyword args (attributes)
                needed to instantiate a :class:`ShoutboxPost` object.
            update: See :meth:`insert`.

        Returns:
            The inserted (or updated) :class:`ShoutboxPost` object.
        """
        shoutbox_post = ShoutboxPost(**shoutbox_post_)
        inserted, shoutbox_post = self.insert(shoutbox_post, update=update)
        self._insert_log_msg(f"Shoutbox post {shoutbox_post.id}", inserted)
        return shoutbox_post

    def insert_thread(self, thread_: dict, update: bool = False) -> Thread:
        """
        Insert a thread into the database; this method wraps :meth:`insert`.

        Args:
            thread\_: A dict containing the keyword args (attributes)
                needed to instantiate a :class:`Thread` object.
            update: See :meth:`insert`.

        Returns:
            The inserted (or updated) :class:`Thread` object.
        """
        thread = Thread(**thread_)
        inserted, thread = self.insert(thread, update=update)
        self._insert_log_msg(f"Thread {thread.title}", inserted)
        return thread

    def insert_user(self, user_: dict, update: bool = False) -> User:
        """
        Insert a user into the database; this method wraps :meth:`insert`.

        Args:
            user\_: A dict containing the keyword args (attributes)
                needed to instantiate a :class:`User` object.
            update: See :meth:`insert`.

        Returns:
            The inserted (or updated) :class:`User` object.
        """
        user = User(**user_)
        inserted, user = self.insert(user, update=update)
        self._insert_log_msg(f"User {user.name}", inserted)
        return user

    def insert_guest(self, guest_: dict) -> User:
        """
        Guest users are a special case of :class:`User`. Guests are users who
        do not have a user id or a user profile page, and may include deleted
        users. Since there may be posts or threads started by guests, they are
        treated as normal users for the purposes of the database, except they
        are assigned a negative integer user id (which does not exist on the
        actual forum). Because a given guest has only a username and not a
        user id, guests are queried by name. If a guest does not already exist
        in the database, the next smallest negative integer is used as their
        user id.

        Args:
            guest\_: A dict containing a ``name`` key, corresponding to the
                guest user's name.

        Returns:
            The inserted or existing :class:`User` object corresponding to
            the guest.
        """
        guest = User(**guest_)

        # Query the database for all existing guests (negative user id).
        query = self.session.query(User).filter(User.id < 0)

        # Of the existing guests, query for the name of the current guest.
        this_guest = query.filter_by(name=guest.name).first()

        if this_guest:
            # This guest user already exists in the database.
            guest.id = this_guest.id
        else:
            # Otherwise, this particular guest user does not exist in the
            # database. Iterate through all guests and assign a new negative
            # user id by decrementing the smallest guest user id already in
            # the database.
            lowest_id = 0
            for existing_guest in query.all():
                lowest_id = min(existing_guest.id, lowest_id)
            new_guest_id = lowest_id - 1
            guest.id = new_guest_id

        inserted, guest = self.insert(guest)
        self._insert_log_msg(f"Guest {guest.name}", inserted)
        return guest

    def query_users(
        self, user_id: Optional[int] = None
    ) -> Union[List[dict], dict]:
        """
        Return a list of all users, if no ``user_id`` is provided, or a
        specific user, if it is provided.

        Args:
            user_id: A user id (optional).

        Returns:
            A dict corresponding to a user in the database (if ``user_id``
            was provided), else a list of dicts of all users (if ``user_id``
            was not provided).

        .. note::
            The returned :class:`User` object(s) are serialized to a
            human-readable JSON format (Python dict) by :func:`serialize`.
        """
        result = self.session.query(User)

        if user_id is not None:
            result = result.filter_by(id=user_id).first()
        else:
            result = result.all()
        return serialize(result)

    def query_boards(
        self, board_id: Optional[int] = None
    ) -> Union[List[dict], dict]:
        """
        Return a list of all boards if no ``board_id`` is provided or a
        specific board if it is provided.

        Args:
            board_id: A board id (optional).

        Returns:
            A dict corresponding to a board in the database (if ``board_id``
            was provided), else a list of dicts of all boards (if ``board_id``
            was not provided).

        .. note::
            The returned :class:`Board` object(s) are serialized to a
            human-readable JSON format (Python dict) by :func:`serialize`.
        """
        result = self.session.query(Board)

        if board_id is not None:
            result = result.filter_by(id=board_id).first()
            # AssociationList and InstrumentedList objects are lazily populated
            # and not part of Board.__dict__, so we add them manually here
            # (but only for querying a single board).
            result.__dict__["moderators"] = list(result.moderators)
            result.__dict__["sub_boards"] = list(result.sub_boards)
            result.__dict__["threads"] = list(result.threads)
        else:
            result = result.all()
        return serialize(result)

    def query_threads(
        self, thread_id: Optional[int] = None
    ) -> Union[List[dict], dict]:
        """
        Return a list of all threads if no ``thread_id`` is provided or a
        specific thread if it is provided.

        Args:
            thread_id: A thread id (optional).

        Returns:
            A dict corresponding to a thread in the database (if ``thread_id``
            was provided), else a list of dicts of all threads (if
            ``thread_id`` was not provided).

        .. note::
            The returned :class:`Thread` object(s) are serialized to a
            human-readable JSON format (Python dict) by :func:`serialize`.
        """
        result = self.session.query(Thread)

        if thread_id is not None:
            result = result.filter_by(id=thread_id).first()
            thread = serialize(result)

            if result is not None:
                poll_query = self.session.query(Poll).filter_by(id=thread_id)
                poll_result = poll_query.first()
                if poll_result is not None:
                    poll = serialize(poll_result)
                    thread["poll"] = poll
            return thread
        else:
            threads = serialize(result.all())
            threads = [
                f"{thread['id']}: {thread['title']}" for thread in threads
            ]
            return threads
