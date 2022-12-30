from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="srtranslator",
    description="Traslate a .SRT file using any custom translator",
    url="https://github.com/sinedie/SRTranslator",
    version="0.1.0",
    author="EAR",
    author_email="sinedie@protonmail.com",
    license="FREE",
    python_requires=">=3.6",
    install_requires=requirements,
    packages=find_packages(),
    keywords=["python", "srt", "languages", "translator", "subtitles"],
)
