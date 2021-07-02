import logging
import pathlib
from typing import List, Tuple, Union

import sqlalchemy
import sqlalchemy.orm

from .schema import (
    Base, Avatar, Board, Category, Image, Moderator, Poll, PollOption,
    PollVoter, Post, Thread, User
)


logger = logging.getLogger(__name__)


def serialize(obj):
    """
    TODO
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

    def _insert_log_msg(self, item_desc: str, inserted: bool):
        """
        Args:
            item_desc: Item description.
            inserted: Whether or not the item was added to the database.
        """
        if inserted:
            logger.info(f"{item_desc} added to database")
        else:
            logger.info(f"{item_desc} already exists in database")

    def insert(
        self, obj: sqlalchemy.orm.DeclarativeMeta, filters: dict = None
    ) -> Tuple[bool, sqlalchemy.orm.DeclarativeMeta]:
        """
        Query the database for an object of the given ``Metaclass`` using the
        given ``filters`` to determine if it already exists in the database.
        If it doesn't, insert it into the database. Either way, return a bool
        indicating whether the object was added, as well as the object.
        """
        if filters is None:
            filters = {"id": obj.id}

        Metaclass = type(obj)
        result = self.session.query(Metaclass).filter_by(**filters).first()

        inserted = False
        if result is None:
            self.session.add(obj)
            self.session.commit()
            inserted = True
        return inserted, obj

    def insert_avatar(self, avatar_: dict):
        avatar = Avatar(**avatar_)
        filters = {
            "image_id": avatar.image_id,
            "user_id": avatar.user_id,
        }
        inserted, avatar = self.insert(avatar, filters)
        self._insert_log_msg(f"Avatar for user {avatar.user_id}", inserted)
        return avatar

    def insert_board(self, board_: dict):
        board = Board(**board_)
        inserted, board = self.insert(board)
        self._insert_log_msg(f"Board {board.name}", inserted)
        return board

    def insert_category(self, category_: dict):
        category = Category(**category_)
        inserted, category = self.insert(category)
        self._insert_log_msg(f"Category {category.name}", inserted)
        return category

    def insert_image(self, image_: dict):
        image = Image(**image_)
        inserted, image = self.insert(image)
        self._insert_log_msg(f"Image {image.url}", inserted)
        return image

    def insert_moderator(self, moderator_: dict):
        moderator = Moderator(**moderator_)
        filters = {
            "user_id": moderator.user_id,
            "board_id": moderator.board_id,
        }
        inserted, moderator = self.insert(moderator, filters)
        self._insert_log_msg(
            f"Moderator {moderator.user_id}, board {moderator.board_id})",
            inserted
        )
        return moderator

    def insert_poll(self, poll_: dict):
        poll = Poll(**poll_)
        inserted, poll = self.insert(poll)
        self._insert_log_msg(f"Poll from thread {poll.id}", inserted)
        return poll

    def insert_poll_option(self, poll_option_: dict):
        poll_option = PollOption(**poll_option_)
        inserted, poll_option = self.insert(poll_option)
        self._insert_log_msg(f"Poll option {poll_option.id}", inserted)
        return poll_option

    def insert_poll_voter(self, poll_voter_: dict):
        poll_voter = PollVoter(**poll_voter_)
        filters = {
            "poll_id": poll_voter.poll_id,
            "user_id": poll_voter.user_id,
        }
        inserted, poll_voter = self.insert(poll_voter, filters)
        self._insert_log_msg(
            f"Poll voter (thread {poll_voter.poll_id}, "
            f"user {poll_voter.user_id})",
            inserted
        )
        return poll_voter

    def insert_post(self, post_: dict):
        post = Post(**post_)
        inserted, post = self.insert(post)
        self._insert_log_msg(f"Post {post.id}", inserted)
        return post

    def insert_thread(self, thread_: dict):
        thread = Thread(**thread_)
        inserted, thread = self.insert(thread)
        self._insert_log_msg(f"Thread {thread.title}", inserted)
        return thread

    def insert_user(self, user_: dict):
        user = User(**user_)
        inserted, user = self.insert(user)
        self._insert_log_msg(f"User {user.name}", inserted)
        return user

    def insert_guest(self, guest_: dict):
        """
        Guest users are a special case of `user`. Guests are users who do not
        have a user id or a user profile page. They may include deleted users.
        Since guests may still have posts or threads they've started, they are
        treated as normal users for the purposes of the database, except they
        are assigned a negative integer user id (which does not exist on the
        actual site). Because a given guest has only a username (not a
        persistent user id), guests are queried by name. If a guest does not
        already exist in the database, we use the next smallest negative
        integer as its user id.
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

    def query_users(self, user_id: int = None) -> Union[List[dict], dict]:
        """
        Return a list of all users if no ``user_num`` provided, or a specific
        user if provided.
        """
        result = self.session.query(User)

        if user_id is not None:
            result = result.filter_by(id=user_id).first()
        else:
            result = result.all()
        return serialize(result)

    def query_boards(self, board_id: int = None) -> Union[List[dict], dict]:
        """
        TODO
        """
        result = self.session.query(Board)

        if board_id is not None:
            result = result.filter_by(id=board_id).first()
            # AssociationList and InstrumentedList objects are lazily populated
            # and not part of Board.__dict__, so we add them manually here
            # (but only for querying a single board).
            result.__dict__["moderators"] = list(result.moderators)
            result.__dict__["sub_boards"] = list(result.sub_boards)
        else:
            result = result.all()
        return serialize(result)

    def query_threads(self, thread_id: int = None) -> dict:
        """
        TODO
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
