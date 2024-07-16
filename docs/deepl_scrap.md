# DeepL translator

## Usage

Driver is optional, if not passed as argument the code will create a new firefox driver with geckodriver (and yes, it install it and put in path if needed) and setup free proxies to avoid getting banned

```
from srtranslator.translators.deepl_scrap import DeeplTranslator

translator = DeeplTranslator(driver=driver)

translator.translate(text, source_language, destination_language)

translator.quit()
```

### From CLI:

(this is the default translator)

```
python -m srtranslator -i src_lang -o target_lang /path/to/srt
```

or

```
python -m srtranslator --translator deepl-scrap -i src_lang -o target_lang /path/to/srt
```

## Supported languages

```
auto : Any language (detect)
bg : Bulgarian
zh : Chinese -Only for source language-
zh-Hans : Chinese (Simplified) -Only usable for destination language-
zh-Hant : Chinese (Traditional) -Only usable for destination language-
cs : Czech
da : Danish
nl : Dutch
en: English -Only for source language-
en-US : English (American) -Only usable for destination language-
en-GB : English (British) -Only usable for destination language-
et : Estonian
fi : Finnish
fr : French
de : German
el : Greek
hu : Hungarian
id : Indonesian
it : Italian
ja : Japanese
ko : Korean
lv : Latvian
lt : Lithuanian
pl : Polish
pt : Portuguese  -Only for source language-
pt-PT : Portuguese  -Only usable for destination language-
pt-BR : Portuguese (Brazilian,  -Only usable for destination language-
ro : Romanian
ru : Russian
sk : Slovak
sl : Slovenian
es : Spanish
sv : Swedish
tr : Turkish
uk : Ukrainian
```

## Limitations

DeepL won't let you translate more than 1500 characters at the same time so it will be slow
