from sqlalchemy import (
    Column, Integer, ForeignKey, String, Text, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """
    Attributes:
        id (int): Primary key.
        user_number (int): User number obtained from the user's profile URL,
            eg, ``https://yoursite.proboards.com/user/21`` refers to the user
            with user number 23. This should be unique for each user.

        age (int): Optional
        birthdate (str): Optional
        date_registered (str): Unix timestamp
        email (str): User email.
        instant_messengers (str): Optional; a string consisting of
            semicolon-delimited "messenger_name:screen_name" pairs, eg,
            "AIM:ssj_goku12;ICQ:12345;YIM:duffman20".
        gender (str): Optional ("Male"/"Female"/"Other")
        group (str): Group/rank (eg, "Regular Membership", "Global Moderator")
        last_online (str): Unix timestamp
        latest_status (str): Optional
        location (str): Optional
        name (str): Display name.
        post_count (int): Number of posts (scraped from the user's profile
            page); to get the actual number of posts by the user in the
            database, use the ``posts`` key.
        signature (str): Optional
        url (str): Original user profile page URL.
        username (str): Registration name.
        website (str): Optional
        website_url (str): Optional

        posts: relationship
        threads: relationship

        TODO
        avatar (bytes?): avatar as a bitmap?
    """
    __tablename__ = "user"

    id = Column("id", Integer, primary_key=True)
    user_number = Column("user_number", Integer, nullable=False, unique=True)

    age = Column("age", Integer)
    birthdate = Column("birthdate", String)
    date_registered = Column("date_registered", String)
    email = Column("email", String)
    instant_messengers = Column("instant_messengers", String)
    gender = Column("gender", String)
    group = Column("group", String)
    last_online = Column("last_online", String)
    latest_status = Column("latest_status", String)
    location = Column("location", String)
    name = Column("name", String)
    post_count = Column("post_count", Integer)
    signature = Column("signature", String)
    url = Column("url", String)
    username = Column("username", String)
    website = Column("website", String)
    website_url = Column("website_url", String)

    # One-to-many mapping of a user and all posts they've made or threads
    # they've started.
    posts = relationship("Post")
    threads = relationship("Thread")


class Category(Base):
    """
    Attributes:
        id (int): Primary key.
        category_number (int): Category number obtained from the site's main
            page source.
        name (str): Category name.
    """
    __tablename__ = "category"


class Board(Base):
    """
    Attributes:
        id (int): Primary key.
        board_number (int): Board number obtained from the board URL, eg,
            ``https://yoursite.proboards.com/board/42/general`` refers to the
            "General" board having board number 42. This should be unique.
        name (str): Board name (required).
        parent_board (int): Parent board primary key (if a sub-board).
        url (str): 

        sub_boards: relationship
    """
    __tablename__ = "board"

    id = Column("id", Integer, primary_key=True)
    board_number = Column("board_number", Integer, nullable=False, unique=True)


class Thread(Base):
    """
    Attributes:
        id (int):
        locked (bool):
        url (str):

        board_id (int): Board (in ``board`` table) where the thread was made.
        user_id (int): User (in ``user`` table) who started the thread.
    """
    __tablename__ = "thread"

    id = Column("id", Integer, primary_key=True)
    thread_number = Column(
        "thread_number", Integer, nullable=False, unique=True
    )

    board_id = Column("board_id", ForeignKey("board.id"), nullable=False)
    user_id = Column("user_id", ForeignKey("user.id"), nullable=False)


class Post(Base):
    """
    Attributes:
        id (int): Primary key.
        datetime (datetime.datetime): Datetime at which post was made.
        last_edited (datetime.datetime): Datetime at which post was edited.
        message (str): Message text.
        url (str):

        user_id (int): User (in ``user`` table) who made the post.
        thread_id (int): Thread (in ``thread``) where the post was made.
        edit_user_id (int): User (in ``user`` table) who made the last edit.
    """
    __tablename__ = "post"

    # NOTE: use Text for message?

    thread_id = Column("thread_id", ForeignKey("thread.id"), nullable=False)
    user_id = Column("user_id", ForeignKey("user.id"), nullable=False)


class Poll(Base):
    """
    Attributes:
        id (int):
    """
    __tablename__ = "poll"
