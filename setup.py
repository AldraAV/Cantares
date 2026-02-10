from setuptools import setup, find_packages

setup(
    name="cantares",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click",
        "requests",
        "rich",
        "spotipy",
        "yt-dlp",
        "textual",
        "python-telegram-bot",
        "mutagen",
        "python-dotenv",
        "beautifulsoup4",
        "lxml",
        "pycryptodome",
    ],
    entry_points={
        "console_scripts": [
            "cantares=cantares.__main__:main",
        ],
    },
)
