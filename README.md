# SRTranslator

> CLI-only subtitle translator for Linux and macOS.

## Install

- pipx (recommended for CLI use):
  ```bash
  pipx install srtranslator
  ```
- pipx from this fork (installs directly from `tinof/SRTranslator`):
  ```bash
  pipx install git+https://github.com/tinof/SRTranslator.git
  ```
- pip:
  ```bash
  pip install srtranslator
  ```

## Usage in Blender

[tin2tin](https://github.com/tin2tin) has made this [blender addon](https://github.com/tin2tin/import_subtitles). Check it out.

## Usage from script

Import stuff

```python
import os

# SRT File
from srtranslator import SrtFile
# ASS File
from srtranslator import AssFile

from srtranslator.translators.deepl_api import DeeplApi
from srtranslator.translators.deepl_scrap import DeeplTranslator
from srtranslator.translators.translatepy import TranslatePy
from srtranslator.translators.pydeeplx import PyDeepLX
```

Initialize translator. It can be any translator, even your own, check the docs, there are instructions per translator and how to create your own.

```python
translator = DeeplTranslator() # or TranslatePy() or DeeplApi(api_key) or DeepLX()
```

Load, translate and save. For multiple recursive files in folder, check `examples folder`

```python
filepath = "./filepath/to/srt"

# SRT File
sub = SrtFile(filepath)
# ASS File
sub = AssFile(filepath)

# Translate
sub.translate(translator, "en", "es")

# Making the result subtitles prettier
sub.wrap_lines()

sub.save(f"{os.path.splitext(filepath)[0]}_translated.srt")
```

Quit translator

```python
translator.quit()
```

## Usage command line

Supported platforms: Linux and macOS.

```bash
# SRT file
srtranslator ./filepath/to/srt -i SRC_LANG -o DEST_LANG

# ASS file
srtranslator ./filepath/to/ass -i SRC_LANG -o DEST_LANG
```

## Advanced usage

```
usage: srtranslator [-h] [-i SRC_LANG] [-o DEST_LANG] [-v] [-vv] [-s] [-w WRAP_LIMIT] [-t {deepl-scrap,translatepy,deepl-api,pydeeplx}] [--auth AUTH] [--proxies] [--context CONTEXT] [--model-type {quality_optimized,latency_optimized,prefer_quality_optimized}] [--instruction TEXT] path

Translate an .STR and .ASS file

positional arguments:
  path                  File to translate

options:
  -h, --help            show this help message and exit
  -i SRC_LANG, --src-lang SRC_LANG
                        Source language. Default: auto
  -o DEST_LANG, --dest-lang DEST_LANG
                        Destination language. Default: es (spanish)
  -v, --verbose         Increase output verbosity
  -vv, --debug          Increase output verbosity for debugging
  -s, --show-browser    Show browser window
  -w WRAP_LIMIT, --wrap-limit WRAP_LIMIT
                        Number of characters -including spaces- to wrap a line of text. Default: 50
  -t {deepl-scrap,translatepy,deepl-api}, --translator {deepl-scrap,translatepy,deepl-api,pydeeplx}
                        Built-in translator to use
  --auth AUTH           Api key if needed on translator
  --proxies             Use proxy by default for pydeeplx
  --context CONTEXT     Context for DeepL translation (only for deepl-api)
  --model-type {quality_optimized,latency_optimized,prefer_quality_optimized}
                        DeepL model type. Default: quality_optimized
  --instruction TEXT    DeepL custom instruction, repeatable (only for deepl-api)
```

### DeepL API options

The `deepl-api` translator uses DeepL's next-generation model
(`--model-type quality_optimized`) by default. Pass `--model-type
latency_optimized` for the faster classic model.

Every chunk is sent with a `context` parameter holding the surrounding dialogue
and the chunk's own lines in the source language. DeepL translates each line of
a chunk independently and shares only `context` between them, so repeating the
chunk there is what lets a line see its neighbours. Context characters are not
billed.

`--instruction` passes a DeepL custom instruction such as "Keep character names
untranslated". It can be repeated up to 10 times, each instruction at most 300
characters. DeepL supports it only for target languages de, en, es, fr, it, ja,
ko and zh; for any other target it is dropped with a warning. It cannot be
combined with `--model-type latency_optimized`.

```bash
srtranslator ./file.srt -i en -o es -t deepl-api --auth YOUR_API_KEY \
  --context "Sci-fi series, formal register" \
  --instruction "Keep character names untranslated"
```
