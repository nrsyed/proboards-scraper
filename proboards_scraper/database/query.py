from typing import List, Union

import sqlalchemy
import sqlalchemy.orm

from .schema import Board, Category, Post, Thread, User


def serialize(obj):
    """
    TODO
    """
    if isinstance(obj, (Board, Category, Post, Thread, User)):
        dict_ = {}
        for k, v in vars(obj).items():
            if not k.startswith("_"):
                dict_[k] = serialize(v)
        return dict_
    elif isinstance(obj, list):
        return [serialize(item) for item in obj]
    else:
        return obj


def query_users(
    db: sqlalchemy.orm.Session, user_id: int = None
) -> Union[List[dict], dict]:
    """
    Return a list of all users if no ``user_num`` provided, or a specific
    user if provided.
    """
    result = db.query(User)

    if user_id is not None:
        result = result.filter_by(id=user_id).first()
    else:
        result = result.all()
    serialized = serialize(result)

    return serialized

