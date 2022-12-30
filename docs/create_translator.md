# Create your own translator

Just create a class whit a translate and quit method.

you can put more methods here, even a constructor, but `translate` and `quit` are mandatory

```
from stranslator.translators.base import Translator

class CustomTranslator(Translator):
    # This is a limitation cause not all translators can translate more than a few characters
    max_char: int = 5000

    def translate(self, text: str, source_language: str, destination_language: str):
        print("Do your magic here. Call an API, piglatin it, whatever, do WTF you want")

    def quit(self):
        print("No need to do anything here, built in translators needed, so, deal with it")
```

And use it the same way that the built in translators.
