from translatepy import Translator
from translatepy.exceptions import TranslatepyException, UnknownLanguage

from .base import Translator as BaseTranslator


class TranslatePy(BaseTranslator):
    max_char = 1e10

    def __init__(self):
        self.translator = Translator()

    def translate(self, text, source_language, destination_language):
        try:
            result = self.translator.translate(
                text,
                source_language=source_language,
                destination_language=destination_language,
            )
            return result.result
        except UnknownLanguage as err:
            print("An error occured while searching for the language you passed in")
            print("Similarity:", round(err.similarity), "%")
            return
        except TranslatepyException:
            print("An error occured while translating with translatepy")
            return
        except Exception:
            print("An unknown error occured")
            return

    def quit(self):
        ...
