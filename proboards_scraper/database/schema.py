from sqlalchemy import (
    Boolean, Column, Integer, ForeignKey, String, UniqueConstraint
)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Avatar(Base):
    """
    This table links a user to their avatar.
    """
    __tablename__ = "avatar"
    __table_args__ = (UniqueConstraint("image_id", "user_id"),)

    image_id = Column(
        "image_id", Integer, ForeignKey("image.id"), primary_key=True
    )
    user_id = Column(
        "user_id", Integer, ForeignKey("user.id"), primary_key=True
    )

    _image = relationship("Image")


class Board(Base):
    """
    Attributes:
        id (int): Board number obtained from the board URL, eg,
            ``https://yoursite.proboards.com/board/42/general`` refers to the
            "General" board having board id 42.
        category_id (int): Category to which this board belongs.
        description (str): Board description.
        name (str): Board name (required).
        parent_id (int): Parent board primary key (if a sub-board).
        password_protected (bool):
        url (str):


        sub_boards: This board's sub-boards.
        threads: This board's threads.
    """
    __tablename__ = "board"

    id = Column("id", Integer, primary_key=True, autoincrement=False)
    category_id = Column("category_id", ForeignKey("category.id"))
    description = Column("description", String)
    name = Column("name", String, nullable=False)
    parent_id = Column("parent_id", ForeignKey("board.id"))
    password_protected = Column("password_protected", Boolean)
    url = Column("url", String)

    sub_boards = relationship("Board")
    threads = relationship("Thread")

    _moderators = relationship("Moderator")
    moderators = association_proxy("_moderators", "_users")


class Category(Base):
    """
    Attributes:
        id (int): Category id number obtained from the main page source.
        name (str): Category name.

        boards: This category's boards (including sub-boards).
    """
    __tablename__ = "category"

    id = Column("id", Integer, primary_key=True, autoincrement=False)
    name = Column("name", String, nullable=False)

    boards = relationship("Board")


class Image(Base):
    """
    Generic image table/class for storing metadata for any image. Image files
    themselves should be downloaded and stored somewhere; this table only
    records the filename of the downloaded file (which may differ from the
    original filename, found in the url).

    Attributes:
        id (int): Autoincrementing primary key.
        description (str): Optional description of this image.
        filename (str): Filename of the downloaded file on disk.
        md5_hash (str): MD5 hash of the downloaded file.
        size (int): Size, in bytes, of the downloaded file.
        url (str): Original URL of the file.
    """
    __tablename__ = "image"

    id = Column("id", Integer, primary_key=True)
    description = Column("description", String)
    filename = Column("filename", String)
    md5_hash = Column("md5_hash", String)
    size = Column("size", Integer)
    url = Column("url", String)


class Moderator(Base):
    """
    This table links a user to a board they moderate. A given moderation
    relationship (i.e., board + user combination) must be unique.

    Attributes:
        board_id (int): Board from ``board`` table.
        user_id (int): User from ``user`` table.
    """
    __tablename__ = "moderator"
    __table_args__ = (UniqueConstraint("board_id", "user_id"),)

    board_id = Column(
        "board_id", Integer, ForeignKey("board.id"), primary_key=True
    )
    user_id = Column(
        "user_id", Integer, ForeignKey("user.id"), primary_key=True
    )

    _users = relationship("User")


class Poll(Base):
    """
    Attributes:
        id (int): The thread id to which this poll belongs.
        name (str): Poll name, i.e., the poll question.
        options: The options associated with this poll.
        users: Users who have voted in this poll.
    """
    __tablename__ = "poll"

    id = Column("id", Integer, ForeignKey("thread.id"), primary_key=True)
    name = Column("name", String)

    options = relationship("PollOption")
    _voters = relationship("PollVoter")
    voters = association_proxy("_voters", "_user")


class PollOption(Base):
    """
    Attributes:
        id (int): Poll option (answer) id obtained from scraping the site.
        poll_id (int): Poll id (aka, thread id) to which this option belongs.
        name (str): Option name.
        votes (int): Number of votes this option received.
    """
    __tablename__ = "poll_option"

    id = Column("id", Integer, primary_key=True, autoincrement=False)
    poll_id = Column("poll_id", Integer, ForeignKey("poll.id"))
    name = Column("name", String)
    votes = Column("votes", Integer)


class PollVoter(Base):
    """
    Attributes:
    """
    __tablename__ = "poll_voter"
    __table_args__ = (UniqueConstraint("poll_id", "user_id"),)

    poll_id = Column(
        "poll_id", Integer, ForeignKey("poll.id"), primary_key=True
    )
    user_id = Column(
        "user_id", Integer, ForeignKey("user.id"), primary_key=True
    )

    _user = relationship("User")


class Post(Base):
    """
    Attributes:
        id (int):
        date (str): When the post was made (Unix timestamp).
        edit_user_id (int): User (in ``user`` table) who made the last edit.
        last_edited (str): When the post was last edited (Unix timestamp); if
            never, this field should be null.
        message (str): Post content/message.
        thread_id (int): Thread (in ``thread``) where the post was made.
        url (str): Original post URL.
        user_id (int): User (in ``user`` table) who made the post.
    """
    __tablename__ = "post"

    id = Column("id", Integer, primary_key=True, autoincrement=False)
    date = Column("date", String)
    edit_user_id = Column("edit_user_id", ForeignKey("user.id"))
    last_edited = Column("last_edited", String)
    message = Column("message", String)
    thread_id = Column(
        "thread_id", ForeignKey("thread.id"), nullable=False
    )
    url = Column("url", String)
    user_id = Column(
        "user_id", ForeignKey("user.id"), nullable=False
    )


class ShoutboxPost(Base):
    """
    Table for shoutbox posts.

    Attributes:
        id (int): Autoincrementing primary key.
        date (str): When the post was made (Unix timestamp).
        message (str): Post content/message.
        user_id (int): User who made the post.
    """
    __tablename__ = "shoutbox_post"

    id = Column("id", Integer, primary_key=True, autoincrement=False)
    date = Column("date", String)
    message = Column("message", String)
    user_id = Column("user_id", Integer, ForeignKey("user.id"))


class Thread(Base):
    """
    Attributes:
        id: Thread id from thread URL.
        announcement (bool):
        board_id (int): Board (in ``board`` table) where the thread was made.
        locked (bool):
        title (str): Thread title.
        url (str): Original URL.
        sticky (bool):
        user_id (int): User (in ``user`` table) who started the thread.

        posts: This thread's posts.
    """
    __tablename__ = "thread"

    id = Column("id", Integer, primary_key=True, autoincrement=False)

    # TODO: default for locked, sticky, announcement, check bool type
    announcement = Column("announcement", Boolean)
    board_id = Column(
        "board_id", ForeignKey("board.id"), nullable=False
    )
    locked = Column("locked", Boolean)
    sticky = Column("sticky", Boolean)
    title = Column("title", String)
    url = Column("url", String)
    user_id = Column(
        "user_id", ForeignKey("user.id"), nullable=False
    )
    views = Column("views", Integer)

    posts = relationship("Post")


class User(Base):
    """
    Attributes:
        id (int): User number obtained from the user's profile URL,
            eg, ``https://yoursite.proboards.com/user/21`` refers to the user
            with user id 21. A negative value indicates a "guest" or deleted
            user and does not refer to an actual user id.
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

        avatar: relationship
        posts: relationship
        threads: relationship
    """
    __tablename__ = "user"

    id = Column("id", Integer, primary_key=True, autoincrement=False)

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

    # One-to-one mapping of a user to their avatar, and one-to-many mapping
    # of all posts/threads they've made or started.
    posts = relationship("Post", foreign_keys="Post.user_id")
    threads = relationship("Thread")

    _avatar = relationship("Avatar")
    avatar = association_proxy("_avatar", "_image")
