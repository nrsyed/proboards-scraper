import argparse
import logging
import pathlib
from pprint import pprint

import proboards_scraper


def configure_logging(verbosity: int = 2):
    """
    Verbosity levels:
    0: silent (only show CRITICAL)
    1: quiet (show proboards_scraper ERROR, imported module ERROR)
    2: normal (show proboards_scraper INFO, imported module ERROR)
    3: verbose (show proboards_scraper DEBUG, imported module ERROR)
    4: vverbose (show proboards_scraper DEBUG, imported module INFO)
    5: vvverbose (show proboards_scraper DEBUG, imported module DEBUG)

    """
    scraper_log_level = logging.CRITICAL
    import_log_level = logging.CRITICAL

    if verbosity >= 1:
        scraper_log_level = logging.ERROR
        import_log_level = logging.ERROR

    if verbosity >= 3:
        scraper_log_level = logging.DEBUG
    elif verbosity >= 2:
        scraper_log_level = logging.INFO

    if verbosity == 5:
        import_log_level = logging.DEBUG
    elif verbosity >= 4:
        import_log_level = logging.INFO

    logging.basicConfig(
        level=scraper_log_level,
        format="[%(asctime)s][%(levelname)s][%(name)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    # Disable "verbose" debug/info logging for imported modules.
    for module in ["asyncio", "selenium", "urllib3"]:
        module_logger = logging.getLogger(module)
        module_logger.setLevel(import_log_level)


def pbs_cli():
    """
    Entrypoint for ``pbs`` (proboards scraper) tool.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("url", type=str, help="Homepage URL")

    login_group = parser.add_argument_group("Login arguments")
    login_group.add_argument(
        "-u", "--username", type=str, help="Login username"
    )
    login_group.add_argument(
        "-p", "--password", type=str, help="Login password"
    )

    parser.add_argument(
        "-o", "--output", type=pathlib.Path, default="site",
        help="Path to output directory containing database and site files"
        " (default ./site)"
    )

    parser.add_argument(
        "-U", "--no-users", action="store_true", dest="skip_users",
        help="Do not grab user profiles (only use this options if a database "
        "exists and users have already been added to it)"
    )
    parser.add_argument(
        "-v", "--verbosity", type=int, choices=[0, 1, 2, 3, 4, 5], default=2,
        help="Verbosity level from 0 (silent) to 5 (full debug); default 2"
    )
    args = parser.parse_args()

    if (
        (args.username and not args.password)
        or (args.password and not args.username)
    ):
        print(
            "If providing login credentials, both username and password "
            "are required"
        )
        exit(1)

    configure_logging(args.verbosity)

    proboards_scraper.scrape_site(
        args.url, dst_dir=args.output, username=args.username,
        password=args.password, skip_users=args.skip_users
    )


def pbd_cli():
    """
    Entrypoint for ``pbd`` (proboards scraper database) database query tool.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--database", type=str, default="site/forum.db",
        help="Path to database file"
    )

    # One actions must be chosen. The value of `0` is used to indicate that
    # that a given action was NOT provided.
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument(
        "--user", "-u", nargs="?", type=int, default=0, const=None
    )
    actions.add_argument(
        "--board", "-b", nargs="?", type=int, default=0, const=None
    )
    args = vars(parser.parse_args())

    db = proboards_scraper.database.Database(args["database"])

    action = None
    value = None

    # Determine which action was selected (and its value, if any provided).
    for _action in ("user", "board"):
        if args[_action] != 0:
            action = _action
            value = args[_action]

    if action == "user":
        result = db.query_users(user_id=value)

        if isinstance(result, list):
            users = []
            for user in result:
                users.append((user["id"], user["name"]))

            users.sort(key=lambda tup: tup[0])
            for user in users:
                user_id = user[0]
                user_name = user[1]
                print(f"{user_id}: {user_name}")
        else:
            user = result
            pprint(user)
    elif action == "board":
        result = db.query_boards(board_id=value)

        if isinstance(result, list):
            boards = []
            for board in result:
                boards.append((board["id"], board["name"]))
            boards.sort(key=lambda tup: tup[0])
            for board in boards:
                board_id = board[0]
                board_name = board[1]
                print(f"{board_id}: {board_name}")
        else:
            board = result
            if "moderators" in board:
                mods = [user["name"] for user in board["moderators"]]
                board["moderators"] = mods
            if "sub_boards" in board:
                sub = [sub["id"] for sub in board["sub_boards"]]
                board["sub_boards"] = sub
            pprint(board)
    else:
        raise ValueError("Invalid action")
