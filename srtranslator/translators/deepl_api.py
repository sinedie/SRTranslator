import deepl
from .base import Translator


class DeeplApi(Translator):
    max_char = 1500

    def __init__(self, api_key):
        self.translator = deepl.Translator(api_key)

    def translate(self, text: str, source_language: str, destination_language: str):
        result = self.translator.translate_text(
            text, source_lang=source_language, target_lang=destination_language
        )
        return result.text
