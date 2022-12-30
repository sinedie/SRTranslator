import time
import logging

from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.proxy import Proxy

from .base import Translator, TimeOutException
from .selenium_utils import (
    create_proxy,
    create_driver,
    TextArea,
    Button,
    Text,
)


class DeeplTranslator(Translator):
    url = "https://www.deepl.com/translator"
    max_char = 2800
    languages = {
        "auto": "Any language (detect)",
        "bg": "Bulgarian",
        "zh": "Chinese",
        "cs": "Czech",
        "da": "Danish",
        "nl": "Dutch",
        "en-US": "English (American)",
        "en-GB": "English (British)",
        "et": "Estonian",
        "fi": "Finnish",
        "fr": "French",
        "de": "German",
        "el": "Greek",
        "hu": "Hungarian",
        "it": "Italian",
        "ja": "Japanese",
        "lv": "Latvian",
        "lt": "Lithuanian",
        "pl": "Polish",
        "pt": "Portuguese",
        "ro": "Romanian",
        "ru": "Russian",
        "sk": "Slovak",
        "sl": "Slovenian",
        "es": "Spanish",
        "sv": "Swedish",
    }

    def __init__(self, driver: Optional[WebDriver] = None):
        self.driver = driver
        if self.driver is None:
            proxy = create_proxy()
            self.driver = create_driver(proxy)

        logging.info(f"Going to {self.url}")
        self.driver.get(self.url)

        self.input_lang_from = TextArea(
            self.driver, "CLASS_NAME", "lmt__source_textarea"
        )
        self.input_destination_language = TextArea(
            self.driver, "CLASS_NAME", "lmt__target_textarea"
        )

    def _set_source_language(self, language: str) -> None:
        self._set_language(language, "lmt__language_select--source")

    def _set_destination_language(self, language: str) -> None:
        self._set_language(language, "lmt__language_select--target")

    def _set_language(self, language: str, dropdown_class: str) -> None:
        # Click the languages dropdown button
        Button(self.driver, "CLASS_NAME", dropdown_class).click()

        # Get the language button to click based on is dl-test property or the text in the button
        xpath_by_property = f"//button[@dl-test='translator-lang-option-{language}']"
        x_path_by_text = f"//button[text()='{self.languages[language]}']"
        xpath = f"{xpath_by_property} | {x_path_by_text}"

        # Click the wanted language button
        Button(self.driver, "XPATH", xpath).click()

    def _is_translated(self, original: str, translation: str) -> bool:
        return (
            len(translation) != 0
            and "[...]" not in translation
            and len(original.splitlines()) == len(translation.splitlines())
            and original != translation
        )

    def translate(self, text: str, source_language: str, destination_language: str):
        self._set_source_language(source_language)
        self._set_destination_language(destination_language)

        clean_text = text.replace("[...]", "@[.]@")

        self.input_lang_from.write((clean_text))

        # Maximun number of iterations 60 seconds
        for _ in range(60):
            translation = self.input_destination_language.value

            if self._is_translated(clean_text, translation):
                return translation.replace("@[.]@", "[...]")
            time.sleep(1)

        self.quit()
        raise TimeOutException("Translation timed out")

    def quit(self):
        self.driver.quit()
