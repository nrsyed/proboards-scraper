import argparse

import proboards_scraper


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str, help="Homepage URL")
    parser.add_argument("username", type=str, help="Login username")
    parser.add_argument("password", type=str, help="Login password")
    parser.add_argument(
        "-d", "--database", type=str, default="forum.db",
        help="Path to database file"
    )
    args = parser.parse_args()

    args.url = args.url.rstrip("/")
    proboards_scraper.scrape_site(
        args.url, args.username, args.password, args.database
    )
