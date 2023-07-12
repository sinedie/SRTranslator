# DeepL translator

## Usage

Driver is optional, if not passed as argument the code will create a new firefox driver with geckodriver (and yes, it install it and put in path if needed) and setup free proxies to avoid getting banned

```
from srtranslator.translators.deepl_api import DeeplApi

translator = DeeplApi(api_key='your_api_key') # As a recomendation, put in in a .env file and load it with python-dotenv

translator.translate(text, source_language, destination_language)

translator.quit() # Totally optional
```

### From CLI:

```
python -m srtranslator --t deepl-api --auth YOUR_API_KEY -i src_lang -o target_lang /path/to/srt
```

or

```
python -m srtranslator --translator deepl-api --auth YOUR_API_KEY -i src_lang -o target_lang /path/to/srt
```

## Supported languages

`Refer to deepl-api docs, but should be the same ones in the scraper`

## Limitations

Change the translator character limit (set in 1500 by default) if use a paid API version. You can translate more than that at once.
