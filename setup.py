from pathlib import Path
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="srtranslator",
    description="Traslate a .SRT file using any custom translator",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/sinedie/SRTranslator",
    version="0.3.9",
    author="EAR",
    author_email="sinedie@protonmail.com",
    license="FREE",
    python_requires=">=3.6",
    install_requires=requirements,
    packages=find_packages(),
    keywords=["python", "srt", "languages", "translator", "subtitles"],
)
