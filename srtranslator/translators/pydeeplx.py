from PyDeepLX import PyDeepLX as PDLX
from random import randint
from time import sleep

from .base import Translator as BaseTranslator
from fp.fp import FreeProxy


class PyDeepLX(BaseTranslator):
    max_char = 1500

    def __init__(self, proxies=None):
        self.proxies = proxies

        # Use proxy by default if self.proxies is True
        if self.proxies:
            print("...... Use proxy")
            self.proxies = FreeProxy(rand=True, timeout=1).get()

    def translate(self, text, source_language, destination_language):
        # Sleep a random number of seconds (between 5 and 10)
        # https://www.shellhacks.com/python-sleep-random-time-web-scraping/
        RANDOM_WAIT = randint(5, 10)
        print(f"...... Wait randomly {RANDOM_WAIT}s")
        sleep(RANDOM_WAIT)

        # Max retry 10
        RETRY_COUNTER = 10
        result = None

        while RETRY_COUNTER > 0 :
            try:
                result = PDLX.translate(
                    text,
                    source_language,
                    destination_language,
                    proxies=self.proxies
                )

                if result == None:
                  print("...... Exception: result is empty raise exception")
                  raise Exception("Result is empty")

                # Everyting alright
                break
            except Exception as e:
                print(f"...... Exception {e} with retry number {RETRY_COUNTER}")

                # Get a random proxy
                print("...... Use or change proxy")
                self.proxies = FreeProxy(rand=True, timeout=1).get()

                # Decrease RETRY_COUNTER
                RETRY_COUNTER -= 1

                # Raise error if RETRY_COUNTER is 0
                if RETRY_COUNTER == 0:
                    print("...... Exception RETRY_COUNTER reached 0")
                    raise

        return result
