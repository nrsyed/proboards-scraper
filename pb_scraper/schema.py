from sqlalchemy import (
    Column, DateTime, ForeignKey, String, Text, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """
    Attributes:
        id (int):
        name (str): Display name.
        username (str): Registration name.
        group (str): Group/rank.
        email (str):
        birthdate (str):
        location (str):
        date_registered (datetime.datetime):
        avatar (str): Filename of avatar.
        signature (str):

        num_posts (int): Number of posts.
        last_online (datetime.datetime):

        posts: relationship
    """
    __tablename__ = "user"


class Board(Base):
    """
    Attributes:
        id (int):
        name (str):
        parent_board (int):
        url (str):

        sub_boards: relationship
    """
    __tablename__ = "board"


class Thread(Base):
    """
    Attributes:
        id (int):
        locked (bool):
        url (str):

        board_id (int): Board (in ``board``) table where the thread was made.
        started_by_user (int):
    """
    __tablename__ = "thread"


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

    # NOTE: use Text for message


class Poll(Base):
    """
    Attributes:
        id (int):
    """
    __tablename__ = "poll"
