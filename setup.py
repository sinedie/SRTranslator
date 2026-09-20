from pathlib import Path
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="srtranslator",
    description="Translate .srt and .ass subtitle files from the CLI",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/sinedie/SRTranslator",
    version="0.4.0",
    author="EAR",
    author_email="sinedie@protonmail.com",
    license="FREE",
    python_requires=">=3.9",
    install_requires=requirements,
    packages=find_packages(),
    entry_points={
        "console_scripts": ["srtranslator=srtranslator.__main__:main"],
    },
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: Free for non-commercial use",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Video",
        "Topic :: Utilities",
    ],
    keywords=["python", "srt", "languages", "translator", "subtitles"],
)
