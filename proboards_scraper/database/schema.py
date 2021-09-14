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

    Attributes:
        image_id (int): Image id of the image that corresponds to this avatar;
            see :class:`Image`.
        user_id (int): User id of the user to which this avatar belongs;
            see :class:`User`.
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
    This table contains information on boards and their associated metadata.

    Attributes:
        id (int): Board number obtained from the board URL, eg,
            ``https://yoursite.proboards.com/board/42/general`` refers to the
            "General" board with id 42.
        category_id (int): Category id of the category to which this board
            belongs; see :class:`Category`.
        description (str): Board description.
        name (str): Board name. Required.
        parent_id (int): Board id of this board's parent board, if it is a
            sub-board.
        password_protected (bool): Whether the board is password-protected.
        url (str): Board URL.

        moderators: List of this board's moderators, if any; see
            :class:`Moderator`.
        sub_boards: List of this board's sub-boards, if any.
        threads: List of this board's threads; see :class:`Thread`.
    """
    __tablename__ = "board"

    id = Column("id", Integer, primary_key=True, autoincrement=False)
    category_id = Column("category_id", ForeignKey("category.id"))
    description = Column("description", String)
    name = Column("name", String, nullable=False)
    parent_id = Column("parent_id", ForeignKey("board.id"))
    password_protected = Column("password_protected", Boolean)
    url = Column("url", String)

    _moderators = relationship("Moderator")
    moderators = association_proxy("_moderators", "_users")

    sub_boards = relationship("Board")
    threads = relationship("Thread")


class Category(Base):
    """
    This table stores information on categories (on the main page) and their
    associated metadata.

    Attributes:
        id (int): Category id number obtained from the main page source.
        name (str): Category name.

        boards: List of boards belonging to this category; see :class:`Board`.
    """
    __tablename__ = "category"

    id = Column("id", Integer, primary_key=True, autoincrement=False)
    name = Column("name", String, nullable=False)

    boards = relationship("Board")


class CSS(Base):
    """
    Table for storing information related to downloaded CSS files. The CSS
    files themselves should be stored on disk.

    Attributes:
        id (int): An arbitrary autoincrementing primary key for each CSS file.
        description (str): Description of the file.
        filename (str): Filename of the CSS file stored on disk.
        md5_hash (str): MD5 hash of the downloaded file.
        url (str): Original URL of the CSS file.
    """
    __tablename__ = "css"

    id = Column("id", Integer, primary_key=True)
    description = Column("description", String)
    filename = Column("filename", String)
    md5_hash = Column("md5_hash", String)
    url = Column("url", String)


class Image(Base):
    """
    This table stores generic metadata for any image. Image files
    themselves should be downloaded and stored somewhere; this table only
    records the filename of the downloaded file (which may differ from the
    original filename, found in the url). The table may also be used to store
    metadata on files that no longer exist, e.g., an avatar hosted on a site
    that no longer exists, as a record of the original URL.

    Attributes:
        id (int): An arbitrary autoincrementing primary key for each image.
        description (str): Description of the image. Optional.
        filename (str): Filename of the downloaded file on disk.
        md5_hash (str): MD5 hash of the downloaded file.
        size (int): Size, in bytes, of the downloaded file.
        url (str): Original URL of the file.

    .. seealso::
        The :class:`Avatar` table, which links an :class:`Image` to a
        :class:`User`.
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
        board_id (int): Board id of the board the user moderates; see
            :class:`Board`.
        user_id (int): User id of the moderator; see :class:`User`.
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
    This table stores information on a poll associated with a thread.
    Specifically, it links the poll id (which is the same as the thread id)
    to the options for the poll and the users who have voted in the poll.

    Attributes:
        id (int): The thread id to which this poll belongs; see
            :class:`Thread`.
        name (str): Poll name, i.e., the poll question.

        options: List of options associated with this poll;
            see :class:`PollOption`.
        voters: List of users who have voted in this poll; see :class:`PollVoter`.
    """
    __tablename__ = "poll"

    id = Column("id", Integer, ForeignKey("thread.id"), primary_key=True)
    name = Column("name", String)

    options = relationship("PollOption")

    _voters = relationship("PollVoter")
    voters = association_proxy("_voters", "_user")


class PollOption(Base):
    """
    This table stores the number of votes for a poll option. A poll option
    must have an associated poll. Note that poll option ids are unique across
    the entire site, so we don't need to create an arbitrary autoincrementing
    primary key and can simply use the integer value found on the forum itself.

    Attributes:
        id (int): Poll option (answer) id obtained from scraping the site.
        poll_id (int): Poll id (aka, thread id) to which this option belongs;
            see :class:`Poll`.
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
    This table links a poll to users who have voted in the poll. Note that we
    can only see who has voted on a poll but not which option
    (:class:`PollOption`) they voted for. Each row in the table corresponds to
    a unique poll/user combination, since a user can vote, at most, only once
    in a given poll.

    Attributes:
        poll_id (int): Poll id of the poll to which this user/vote belongs;
            see :class:`Poll`.
        user_id (int): User id of the user/voter; see :class:`User`.
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
    This table holds information for each post.

    Attributes:
        id (int): Post id, obtained from the forum. Every post on a forum has
            a unique integer id.
        date (int): When the post was made (Unix timestamp).
        edit_user_id (int): User id of the user who made the last edit, if any;
            see :class:`User`. If never edited, this value will be `null`.
        last_edited (int): When the post was last edited (Unix timestamp), if
            at all. If never edited, this value will be `null`.
        message (str): Post content/message, including any raw HTML.
        thread_id (int): Thread id of the thread in which the post was made;
            see :class:`Thread`.
        url (str): Original post URL.
        user_id (int): User id of the user who made the post; see :class:`User`.
    """
    __tablename__ = "post"

    id = Column("id", Integer, primary_key=True, autoincrement=False)
    date = Column("date", Integer)
    edit_user_id = Column("edit_user_id", ForeignKey("user.id"))
    last_edited = Column("last_edited", Integer)
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
    This table holds information for each shoutbox post.

    Attributes:
        id (int): Autoincrementing primary key.
        date (int): When the post was made (Unix timestamp).
        message (str): Post content/message, including any HTML.
        user_id (int): User id of the user who made the post; see
            :class:`User`.
    """
    __tablename__ = "shoutbox_post"

    id = Column("id", Integer, primary_key=True, autoincrement=False)
    date = Column("date", Integer)
    message = Column("message", String)
    user_id = Column("user_id", Integer, ForeignKey("user.id"))


class Thread(Base):
    """
    This table stores information for each thread.

    Attributes:
        id (int): Thread id, obtained from the thread URL.
        announcement (bool): Whether the thread is marked as an announcement.
        board_id (int): Board id of the board in which the thread was made;
            see :class:`Board`.
        locked (bool): Whether the thread is locked.
        title (str): Thread title.
        url (str): Original URL.
        sticky (bool): Whether the thread is stickied.
        user_id (int): User id of the user who started the thread; see
            :class:`User`.
        views (int): Number of thread views.

        posts: A list of this thread's posts; see :class:`Post`.
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
    This table holds information on users obtained from their user profile.

    Attributes:
        id (int): User number obtained from the user's profile URL,
            eg, ``https://yoursite.proboards.com/user/21`` refers to the user
            with user id 21. A negative value indicates a "guest" or deleted
            user and does not refer to an actual user id.
        age (int): User age. Optional.
        birthdate (str): User birthdate string. Optional.
        date_registered (int): Unix timestamp.
        email (str): User email.
        instant_messengers (str): Optional; a string consisting of
            semicolon-delimited "messenger_name:screen_name" pairs, eg,
            ``"AIM:ssj_goku12;ICQ:12345;YIM:duffman20"``.
        gender (str): Optional ("Male"/"Female"/"Other").
        group (str): Group/rank (eg, "Regular Membership", "Global Moderator").
        last_online (int): Unix timestamp.
        latest_status (str): User's latest status. Optional.
        location (str): User location. Optional.
        name (str): Display name.
        post_count (int): Number of posts (scraped from the user's profile
            page); to get the actual number of posts by the user in the
            database, use the :attr:`posts` attribute.
        signature (str): User signature. Optional.
        url (str): Original user profile page URL.
        username (str): Registration name.
        website (str): User website. Optional.
        website_url (str): User website URL. Optional.

        avatar: The avatar associated with the user; see :class:`Avatar`.
        posts: A list of posts by the user; see :class:`Post`.
        threads: A list of threads started by the user; see :class:`Thread`.
    """
    __tablename__ = "user"

    id = Column("id", Integer, primary_key=True, autoincrement=False)

    age = Column("age", Integer)
    birthdate = Column("birthdate", String)
    date_registered = Column("date_registered", Integer)
    email = Column("email", String)
    instant_messengers = Column("instant_messengers", String)
    gender = Column("gender", String)
    group = Column("group", String)
    last_online = Column("last_online", Integer)
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
