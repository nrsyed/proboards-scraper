import sys

import bs4
import urllib.request

#https://stackoverflow.com/questions/51682341/how-to-send-cookies-with-urllib

def get_source(url):
    with urllib.request.urlopen(url) as response:
        source = response.read()
    soup = bs4.BeautifulSoup(source, "html.parser")
    return soup

def scrape_category(category: bs4.element.Tag):
    title_bar = category.find("div", class_="title_wrapper")
    title = title_bar.text

    x = category
    breakpoint()

def scrape_root(url: str):
    source = get_source(url)
    categories = source.findAll("div", class_="container boards")

    for category in categories:
        scrape_category(category)


if __name__ == "__main__":
    url = sys.argv[1]
    scrape_root(url)
