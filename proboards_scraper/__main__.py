import argparse
import logging
from pprint import pprint

import proboards_scraper

def pbs_cli():
    """
    Entrypoint for ``pbs`` (proboards scraper) tool.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str, help="Homepage URL")
    parser.add_argument("username", type=str, help="Login username")
    parser.add_argument("password", type=str, help="Login password")
    parser.add_argument(
        "-d", "--database", type=str, default="forum.db",
        help="Path to database file"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    args.url = args.url.rstrip("/")
    proboards_scraper.scrape_site(
        args.url, args.username, args.password, args.database
    )


def pbd_cli():
    """
    Entrypoint for ``pbd`` (proboards scraper database) database query tool.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--database", type=str, default="forum.db",
        help="Path to database file"
    )

    # One actions must be chosen. The value of `-1` is used to indicate that
    # that a given action was NOT provided.
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument(
        "--user", "-u", nargs="?", type=int, default=-1, const=None
    )
    actions.add_argument(
        "--board", "-b", nargs="?", type=int, default=-1, const=None
    )
    args = vars(parser.parse_args())

    db = proboards_scraper.database.get_session(args["database"])

    action = None
    value = None

    # Determine which action was selected (and its value, if any provided).
    for _action in ("user", "board"):
        if args[_action] != -1:
            action = _action
            value = args[_action]

    if action == "user":
        result = proboards_scraper.database.query_users(db, user_num=value)

        if isinstance(result, list):
            users = []
            for user in result:
                users.append((user["number"], user["name"]))

            users.sort(key=lambda tup: tup[0])
            for user in users:
                user_num = user[0]
                user_name = user[1]
                print(f"{user_num}: {user_name}")
        else:
            user = result
            pprint(user)
    elif action == "board":
        pass
    else:
        raise ValueError("Invalid action")
