import time
import logging

from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.proxy import Proxy
from selenium.webdriver.common.keys import Keys

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
    max_char = 1500
    languages = {
        "auto": "Any language (detect)",
        "bg": "Bulgarian",
        "zh": "Chinese",  # Only usable for source language
        "zh-Hans": "Chinese (Simplified)",  # Only usable for destination language
        "zh-Hant": "Chinese (Traditional)",  # Only usable for destination language
        "zh": "Chinese",
        "cs": "Czech",
        "da": "Danish",
        "nl": "Dutch",
        "en": "English",  # Only usable for source language
        "en-US": "English (American)",  # Only usable for destination language
        "en-GB": "English (British)",  # Only usable for destination language
        "et": "Estonian",
        "fi": "Finnish",
        "fr": "French",
        "de": "German",
        "el": "Greek",
        "hu": "Hungarian",
        "id": "Indonesian",
        "it": "Italian",
        "ja": "Japanese",
        "ko": "Korean",
        "lv": "Latvian",
        "lt": "Lithuanian",
        "pl": "Polish",
        "pt": "Portuguese",  # Only usable for source language
        "pt-PT": "Portuguese",  # Only usable for destination language
        "pt-BR": "Portuguese (Brazilian)",  # Only usable for destination language
        "ro": "Romanian",
        "ru": "Russian",
        "sk": "Slovak",
        "sl": "Slovenian",
        "es": "Spanish",
        "sv": "Swedish",
        "tr": "Turkish",
        "uk": "Ukrainian",
    }

    def __init__(self, driver: Optional[WebDriver] = None):
        self.last_translation_failed = False
        self.driver = driver

        if self.driver is None:
            self._rotate_proxy()
            return

        self._reset()

    def _reset(self):
        logging.info(f"Going to {self.url}")
        self.driver.get(self.url)
        self.driver.implicitly_wait(5)
        self._closePopUp()

        self.input_lang_from = TextArea(
            self.driver, "XPATH", "//*[@data-testid='translator-source-input']"
        )
        self.input_destination_language = TextArea(
            self.driver, "XPATH", "//*[@data-testid='translator-target-input']"
        )

        self.src_lang = None
        self.target_lang = None

    def _rotate_proxy(self):
        if self.driver is not None:
            logging.info(" ======= Translation failed. Probably got banned. ======= ")
            logging.info("Rotating proxy")
            self.quit()

        proxy = create_proxy()
        self.driver = create_driver(proxy)
        self._reset()

    def _closePopUp(self):
        Button(
            self.driver,
            "CSS_SELECTOR",
            "[aria-label=Close]",
            wait_time=5,
            optional=True,
        ).click()

    def _set_source_language(self, language: str) -> None:
        self._set_language(language, "//*[@data-testid='translator-source-lang']")
        self.src_lang = language

    def _set_destination_language(self, language: str) -> None:
        self._set_language(language, "//*[@data-testid='translator-target-lang']")
        self.target_lang = language

    def _set_language(self, language: str, xpath: str) -> None:
        # Click the languages dropdown button
        Button(self.driver, "XPATH", xpath).click()

        # Get the language button to click based on is dl-test property or the text in the button
        xpath_by_property = (
            f"//button[@data-testid='translator-lang-option-{language}']"
        )
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
        if source_language != self.src_lang:
            self._set_source_language(source_language)
        if destination_language != self.target_lang:
            self._set_destination_language(destination_language)

        clean_text = text.replace("[...]", "@[.]@")

        self.input_lang_from.write((clean_text.replace("\n", Keys.ENTER)))

        # Maximun number of iterations 60 seconds
        for _ in range(60):
            translation = self.input_destination_language.value

            if self._is_translated(clean_text, translation):
                time.sleep(2)
                translation = self.input_destination_language.value

                # Reset the proxy flag
                self.last_translation_failed = False
                return translation.replace("@[.]@", "[...]")
            time.sleep(1)

        # Maybe proxy got banned, so we try with a new proxy, but just once.
        if not self.last_translation_failed:
            self.last_translation_failed = True
            self._rotate_proxy()
            return self.translate(text, source_language, destination_language)

        self.quit()
        raise TimeOutException("Translation timed out")

    def quit(self):
        self.driver.quit()
