from setuptools import setup

setup(
    name="proboards-scraper",
    version="0.8",
    author="Najam R. Syed",
    author_email="najam.r.syed@gmail.com",
    license="MIT",
    packages=["proboards_scraper"],
    install_requires=["aiohttp", "bs4", "selenium", "sqlalchemy"],
    entry_points={
        "console_scripts": [
            "pbs = proboards_scraper.__main__:pbs_cli",
            "pbd = proboards_scraper.__main__:pbd_cli",
        ],
    },
)
