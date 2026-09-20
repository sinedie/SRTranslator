# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SRTranslator is a Python library for translating subtitle files (.srt and .ass formats) using various translation services. It provides a CLI tool and a Python API (GUI removed).

## Installation & Setup

### Local Development

Install the package in development mode:
```bash
pip install -e .
```

Or install dependencies directly:
```bash
pip install -r requirements.txt
```

### Docker Support

Build and run via Docker:
```bash
docker build -t srtranslator .
docker run -v /path/to/subtitles:/app/subtitles srtranslator python -m srtranslator /app/subtitles/file.srt -i en -o es
```

## Common Commands

### CLI Usage (Linux/macOS)

**Basic translation:**
```bash
srtranslator ./path/to/file.srt -i SRC_LANG -o DEST_LANG
```

**With specific translator:**
```bash
srtranslator ./path/to/file.srt -i en -o es -t deepl-scrap
srtranslator ./path/to/file.srt -i en -o es -t deepl-api --auth YOUR_API_KEY
srtranslator ./path/to/file.srt -i en -o es -t translatepy
srtranslator ./path/to/file.srt -i en -o es -t pydeeplx --proxies
```

**With options:**
```bash
srtranslator ./file.srt -i en -o es -w 60 -v  # Custom wrap limit, verbose
srtranslator ./file.srt -i en -o es -s       # Show browser (for selenium translators)
```

### Testing and linting

```bash
pip install -r requirements-dev.txt
pytest                 # 25 tests in tests/
ruff check .           # CI gate; line-length 100, rules E+F, E501 ignored
```

CI (`.github/workflows`) runs `ruff check .` then `pytest` on Python 3.10 and 3.11.
Note `ruff format` has never been applied to this repo, so `ruff format --check .` fails on
pre-existing files. Only `ruff check` is a gate.

## Architecture

### Core Components

**1. Subtitle File Classes (`srtranslator/srt_file.py`, `srtranslator/ass_file.py`)**
- `SrtFile`: Handles .srt subtitle format using the `srt` library
- `AssFile`: Handles .ass subtitle format using the `pyass` library
- Both classes share similar interfaces:
  - `__init__(filepath)`: Load subtitle file
  - `translate(translator, source_lang, dest_lang)`: Translate using provided translator
  - `wrap_lines(line_wrap_limit)`: Format subtitles with line wrapping
  - `save(filepath)`: Save translated subtitles
  - `save_backup()`: Create backup during translation (used for resume on failure)
  - `_get_next_chunk(chunk_size)`: Generator that yields subtitle chunks based on translator's max character limit
  - `_load_backup()`: Resume from `.tmp` backup file if translation was interrupted

**2. Translator Architecture (`srtranslator/translators/`)**

All translators inherit from `base.Translator` abstract class:
```python
class Translator(ABC):
    max_char: int  # Maximum characters per translation request

    # Dispatches to translate_batch for a list, translate_single for a string
    def translate(text, source_language, destination_language, context=None)

    # Default implementation joins with newlines and splits the result
    def translate_batch(text: list, source_language, destination_language, context=None) -> list

    @abstractmethod
    def translate_single(text: str, source_language, destination_language, context=None) -> str

    def quit(self)  # Cleanup resources
```

`context` carries the per-chunk DeepL context. Translators that cannot use it ignore it.

Built-in translators:
- `deepl_scrap.DeeplTranslator`: Web scraping DeepL using Selenium (default, max_char=1500)
  - Includes proxy rotation on failure/ban detection
  - Uses `selenium_utils` for browser automation
  - Headless by default (controlled by `MOZ_HEADLESS` env var)
- `deepl_api.DeeplApi`: Official DeepL API via `deepl.DeepLClient` (requires API key, max_char=1500)
  - Defaults to the next-gen model (`model_type="quality_optimized"`); `--model-type` overrides
  - Sends a per-chunk `context` built by the subtitle classes; context is not billed
  - `custom_instructions` (CLI `--instruction`, max 10 x 300 chars) applies only to target
    languages de/en/es/fr/it/ja/ko/zh and is rejected with `latency_optimized`
  - Sums `billed_characters` and logs the total plus `model_type_used`
- `translatepy.TranslatePy`: Uses translatepy library (max_char=1e10)
- `pydeeplx.PyDeepLX`: DeepLX API wrapper with proxy support (max_char=1500)
  - Random wait times between requests (5-10 seconds)
  - Automatic retry with proxy rotation on failure (up to 10 retries)

**3. Translation Flow**

1. Load subtitle file (auto-detects .srt vs .ass)
2. Check for `.tmp` backup file to resume interrupted translation
3. Split subtitles into chunks based on translator's `max_char` limit
4. For each chunk:
   - Build the DeepL context from the surrounding scene plus the chunk itself
   - Send the chunk as a list (DeepL API) or newline-joined (other translators)
   - Map the response back onto the individual subtitles
   - Update progress
5. Optionally wrap lines for better readability
6. Save result with language suffix (e.g., `file_es.srt`)
7. Clean up backup file on success

**4. Special Handling**

- **HTML tags**: Removed from subtitle content with regex `<.*?>`
- **ASS styles**: Extracted and preserved using `|` placeholder during translation, then restored
- **Line breaks**:
  - SRT: Converted to spaces before translation, restored with wrapping
  - ASS: `\N` converted to a space-padded four-backslash placeholder, restored by
    `wrap_lines`
- **Dialog markers**: Lines starting with `-` preserved with `////` placeholder
- **Resume capability**: `.tmp` backup files allow resuming failed translations

**5. Scene-Aware DeepL Context**

Both `SrtFile` and `AssFile` carry their own copy of the same three methods. Keep the two
copies in step when editing either.

- `_detect_scenes(scene_gap_seconds=2.0)`: scene boundaries from timing gaps
- `_build_deepl_context(...)`: composes the context string. Blocks are "Earlier in this
  scene", "Previous dialogue", "Current dialogue" and "Upcoming dialogue"
- `_context_for_chunk(...)`: calls the builder with progressively smaller budgets from
  `util.CONTEXT_BUDGETS` until the request body fits `util.MAX_REQUEST_BODY_BYTES`

Three rules drive the design, and each one is easy to break by accident:

- **The current chunk is included in its own context on purpose.** DeepL translates every
  entry of a text list independently and shares only `context` between them. Removing the
  "Current dialogue" block is what the code used to do, and it left each line blind to its
  neighbours.
- **Never feed translated text back as context.** The backward walk stops at
  `self.start_from`, because a resumed run holds target-language text below that index.
- **Context is not billed**, so budgets are generous. The only hard ceiling is DeepL's
  128 KiB request body.

Inspect it with `DEBUG_CONTEXT=1`. See [CONTEXT_TRANSLATION.md](CONTEXT_TRANSLATION.md).

### Entry Points

- **CLI**: `srtranslator/__main__.py` exposed via `srtranslator` console script
- **Python API**: Import `SrtFile`, `AssFile` from `srtranslator` package

### Examples Directory

The `examples/` folder contains patterns for:
- `recursive_folder.py`: Processing multiple subtitle files in a directory tree
- `custom_translator.py`: How to implement custom translator classes
- `deep_api.py`: Using DeepL API with authentication
- `custom_proxy.py`: Custom proxy configuration
- `tor_service.py`: Using Tor for anonymity

## Development Notes

### Python Requirements

- Python 3.9+ required by `deepl`; `pyass` needs 3.10+, and CI tests 3.10 and 3.11 (CLI-only, Linux/macOS)
- Key dependencies: deepl, selenium, srt, pyass, translatepy, PyDeepLX, free_proxy, webdriverdownloader

### Selenium/Browser Requirements

For web scraping translators (deepl-scrap):
- Firefox browser (geckodriver)
- Headless mode enabled by default via `MOZ_HEADLESS=1` environment variable
- Use `-s` flag to show browser window for debugging
- Docker image includes Firefox ESR and geckodriver v0.34.0

### Creating Custom Translators

Extend `srtranslator.translators.base.Translator`:
1. Set `max_char` class variable (chunk size limit)
2. Implement `translate(text, source_language, destination_language)` method
3. Optionally implement `quit()` for cleanup
4. See `examples/custom_translator.py` for reference

### Language Codes

Language codes must match the translator being used:
- DeepL: Uses ISO codes like "en", "es", "de", with variants like "en-US", "en-GB", "pt-BR"
- TranslatePy: More flexible, supports various formats
- Use "auto" for automatic source language detection (where supported)

### Error Handling

- Translation failures trigger backup save to `.tmp` file
- Selenium-based translators auto-rotate proxies on ban detection
- PyDeepLX includes retry logic with proxy rotation
- TimeOutException raised after 60 seconds without translation response

GUI components have been removed; focus on CLI and API only.

## Gotchas

- **ASS line breaks travel as a backslash placeholder.** `ass_file._clean_subs_content`
  swaps `\N` for `ASS_LINE_BREAK_PADDED` (four backslashes, space padded) and `wrap_lines`
  restores any run of two or more backslashes back to `\N`. Use a lambda replacement in
  `re.sub` for both, because a literal replacement string re-escapes the backslashes. The
  older character-class version ate the characters next to the placeholder and never
  restored `\N`; `tests/test_ass_file.py` guards against a regression.
- **`SrtFile` and `AssFile` duplicate their chunking and context logic.** A fix applied to
  one almost always belongs in the other.
- **`load_subtitle` tries ASS first** and falls back to SRT on `AttributeError`, so every run
  logs a "Loading as ASS" line even for an SRT file. That is not an error.
- **`ruff format` was never run on this repo.** Do not reformat whole files; it buries real
  changes in unrelated churn.

## Documentation Layout

| File | Purpose |
|---|---|
| `CLAUDE.md` | This file. Single source of agent guidance |
| `AGENTS.md` | Pointer to this file, for non-Claude agents |
| `README.md` | User-facing install and CLI usage |
| `CONTEXT_TRANSLATION.md` | How DeepL context is built and tuned |
| `docs/*.md` | One page per translator backend |

`LLM_SUBTRANS_CONTEXT.md` and `CONFIGURATION.md` were merged into `CONTEXT_TRANSLATION.md`
and deleted. Do not recreate them.
