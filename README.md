# SRTranslator

## Install

[PyPI](https://pypi.org/project/srtranslator/)

```
pip install srtranslator
```

## Usage from script

Import stuff

```
from srtranslator import SrtFile
from srtranslator.translators.deepl import DeeplTranslator
from srtranslator.translators.translatepy import TranslatePy
```

Initialize translator. It can be any translator, even your own, check the docs, there are instructions per translator and how to create your own.

```
translator = DeeplTranslator() # or TranslatePy()
```

Load, translate and save. For multiple recursive files in folder, check `examples folder`

```
filepath = "./filepath/to/srt"
srt = SrtFile(filepath)
srt.translate(translator, "en", "es")

# Making the result subtitles prettier
srt.wrap_lines()

srt.save(f"{os.path.splitext(filepath)[0]}_translated.srt")
```

Quit translator

```
translator.quit()
```

## Usage from GUI

[KryptoST](https://github.com/KryptoST) has made a C# graphical user interface. You can check it out [here](https://github.com/KryptoST/SRTranslatorGUI)

## Usage command line

```
python -m srtranslator ./filepath/to/srt -i SRC_LANG -o DEST_LANG
```

## Advanced usage

```
usage: __main__.py [-h] [-i SRC_LANG] [-o DEST_LANG] [-v] [-vv] [-s] [-w WRAP_LIMIT] path

Translate an .STR file

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
```
