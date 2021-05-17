import argparse

import proboards_scraper


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str, help="Homepage URL")
    parser.add_argument("username", type=str, help="Login username")
    parser.add_argument("password", type=str, help="Login password")
    args = parser.parse_args()

    args.url = args.url.rstrip("/")
    proboards_scraper.scrape_site(args.url, args.username, args.password)
