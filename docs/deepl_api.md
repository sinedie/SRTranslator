# DeepL API translator

Uses the official DeepL API through the `deepl` Python client (`deepl.DeepLClient`). Needs an
API key. No browser, no driver and no proxies, unlike the `deepl-scrap` translator.

## Usage

```python
from srtranslator.translators.deepl_api import DeeplApi

translator = DeeplApi(
    api_key="your_api_key",          # keep it in .env and load with python-dotenv
    context="Action thriller film.",  # optional, prepended to every request
    model_type="quality_optimized",   # default
    custom_instructions=["Keep character names untranslated"],  # optional
)

translator.translate(text, source_language, destination_language)

translator.quit()  # optional; logs the billed character total
```

`text` may be a string or a list of strings. A list is sent to DeepL as a list, and each
entry is translated independently.

## From the CLI

```bash
srtranslator /path/to/file.srt -t deepl-api --auth YOUR_API_KEY -i en -o fi
```

With the DeepL-specific options:

```bash
srtranslator /path/to/file.srt \
  --translator deepl-api --auth YOUR_API_KEY \
  -i en -o es \
  --context "Sci-fi series, formal register" \
  --instruction "Keep character names untranslated" \
  --model-type quality_optimized
```

| Option | Meaning |
|---|---|
| `--context` | Global context string, prepended to the per-chunk context |
| `--model-type` | `quality_optimized` (default, next-gen), `latency_optimized` (classic), or the legacy alias `prefer_quality_optimized` |
| `--instruction` | DeepL custom instruction, repeatable up to 10 times, 300 characters each |

`--instruction` works only for target languages de, en, es, fr, it, ja, ko and zh. For any
other target it is dropped with a warning. It cannot be combined with `latency_optimized`.

The translator also builds a per-chunk context automatically from the surrounding subtitles.
See [CONTEXT_TRANSLATION.md](../CONTEXT_TRANSLATION.md).

## Supported languages

Refer to the DeepL API documentation. DeepL added a large number of languages through 2025
and 2026, so query the live list rather than assuming.

## Limitations

`max_char` is 1500, which sets the chunk size and therefore the number of API calls. Raise it
on a paid plan to send more text per request. Context characters are not billed, but the
whole request body must stay under DeepL's 128 KiB limit.
