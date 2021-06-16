# TODO: should numbers be the primary keys?
from sqlalchemy import (
    Boolean, Column, Integer, ForeignKey, String, Text, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """
    Attributes:
        id (int): Primary key.
        number (int): User number obtained from the user's profile URL,
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
    number = Column("number", Integer, nullable=False, unique=True)

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
    posts = relationship("Post", foreign_keys="Post.user_id")
    threads = relationship("Thread")


class Category(Base):
    """
    Attributes:
        id (int): Primary key.
        name (str): Category name.
        number (int): Category number obtained from the main page source.

        boards: This category's boards (including sub-boards).
    """
    __tablename__ = "category"

    id = Column("id", Integer, primary_key=True)
    name = Column("name", String, nullable=False)
    number = Column("number", Integer, nullable=False, unique=True)

    boards = relationship("Board")



class Board(Base):
    """
    Attributes:
        id (int): Primary key.
        name (str): Board name (required).
        number (int): Board number obtained from the board URL, eg,
            ``https://yoursite.proboards.com/board/42/general`` refers to the
            "General" board having board number 42. This should be unique.
        url (str): 

        category_id (int): Category to which this board belongs.
        parent_id (int): Parent board primary key (if a sub-board).

        sub_boards: This board's sub-boards.
        threads: This board's threads.
    """
    __tablename__ = "board"

    id = Column("id", Integer, primary_key=True)
    name = Column("name", String, nullable=False)
    number = Column("number", Integer, nullable=False, unique=True)
    url = Column("url", String)

    category_id = Column("category_id", ForeignKey("category.id"))
    parent_id = Column("parent_id", ForeignKey("board.id"))

    sub_boards = relationship("Board")
    threads = relationship("Thread")


class Thread(Base):
    """
    Attributes:
        id (int): Primary key.
        locked (bool):
        number: Thread number from thread URL.
        title (str): Thread title.
        url (str): Original URL.

        board_id (int): Board (in ``board`` table) where the thread was made.
        user_id (int): User (in ``user`` table) who started the thread.

        posts: This thread's posts.
    """
    __tablename__ = "thread"

    id = Column("id", Integer, primary_key=True)
    # TODO: default for locked, check bool type
    locked = Column("locked", Boolean)
    number = Column("number", Integer, nullable=False, unique=True)
    title = Column("title", String)
    url = Column("url", String)

    board_id = Column("board_id", ForeignKey("board.id"), nullable=False)
    user_id = Column("user_id", ForeignKey("user.id"), nullable=False)

    posts = relationship("Post")


class Post(Base):
    """
    Attributes:
        id (int): Primary key.
        date (str): When the post was made (Unix timestamp).
        last_edited (str): When the post was last edited (Unix timestamp); if
            never, this field should be null.
        message (str): Post content/message.
        url (str): Original post URL.

        edit_user_id (int): User (in ``user`` table) who made the last edit.
        thread_id (int): Thread (in ``thread``) where the post was made.
        user_id (int): User (in ``user`` table) who made the post.
    """
    __tablename__ = "post"

    id = Column("id", Integer, primary_key=True)
    date = Column("date", String)
    last_edited = Column("last_edited", String)
    number = Column("number", Integer, nullable=False, unique=True)
    message = Column("message", String)
    url = Column("url", String)

    edit_user_id = Column("edit_user_id", ForeignKey("user.id"))
    thread_id = Column("thread_id", ForeignKey("thread.id"), nullable=False)
    user_id = Column("user_id", ForeignKey("user.id"), nullable=False)


#class Poll(Base):
#    """
#    Attributes:
#        id (int):
#    """
#    __tablename__ = "poll"
