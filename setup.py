from setuptools import setup

setup(
    name="proboards-scraper",
    version="0.3",
    author="Najam R. Syed",
    author_email="najam.r.syed@gmail.com",
    license="MIT",
    packages=["proboards_scraper"],
    install_requires=["bs4", "selenium", "sqlalchemy", "requests"],
    entry_points={
        "console_scripts": ["pbs = proboards_scraper.__main__:cli"],
    },
)
