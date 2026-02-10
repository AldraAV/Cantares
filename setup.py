from setuptools import setup, find_packages
import os

# Read the contents of your README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="cantares",
    version="0.1.0",
    description="CLI/TUI Music & Book Downloader. Porque lo bueno siempre se comparte.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AldraAV",
    url="https://github.com/AldraAV/Cantares",
    project_urls={
        "Bug Tracker": "https://github.com/AldraAV/Cantares/issues",
        "Source Code": "https://github.com/AldraAV/Cantares",
    },
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
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Utilities",
    ],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "cantares=cantares.__main__:main",
        ],
    },
    keywords="music downloader deezer spotify books cli tui",
)
