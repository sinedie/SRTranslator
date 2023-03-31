from abc import ABC, abstractmethod


class Translator(ABC):
    max_char: int

    @abstractmethod
    def translate(
        self, text: str, source_language: str, destination_language: str
    ) -> str:
        ...

    def quit(self):
        ...


class TimeOutException(Exception):
    """Translation timed out"""
