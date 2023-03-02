import requests
from .base import Translator


class DeeplApi(Translator):
    max_char = 3000

    def __init__(self, api_url, api_key):
        url = api_url
        api = api_key

    def translate(self, text: str, source_language: str, destination_language: str):

        headers = {"Authorization": self.api_key}
        response = requests.post(
            self.url,
            headers=headers,
            json={
                "text": text,
                "source_lang": source_language.upper(),
                "target_lang": destination_language.upper(),
                "split_senteces": 0,
            },
        )

        translation = response.json()

        return translation["traslations"][0]["text"]
