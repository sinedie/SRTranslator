import os
import argparse
import logging

from .srt_file import SrtFile
from .translators.deepl import DeeplTranslator
from .translators.translatepy import TranslatePy

parser = argparse.ArgumentParser(description="Translate an .STR file")

parser.add_argument(
    "filepath",
    metavar="path",
    type=str,
    help="File to translate",
)

parser.add_argument(
    "-i",
    "--src-lang",
    type=str,
    default="auto",
    help="Source language. Default: auto",
)

parser.add_argument(
    "-o",
    "--dest-lang",
    type=str,
    default="es",
    help="Destination language. Default: es (spanish)",
)

parser.add_argument(
    "-v",
    "--verbose",
    action="store_const",
    dest="loglevel",
    const=logging.INFO,
    help="Increase output verbosity",
)

parser.add_argument(
    "-vv",
    "--debug",
    action="store_const",
    dest="loglevel",
    const=logging.DEBUG,
    default=logging.WARNING,
    help="Increase output verbosity for debugging",
)

parser.add_argument(
    "-s",
    "--show-browser",
    action="store_true",
    help="Show browser window",
)

parser.add_argument(
    "-w",
    "--wrap-limit",
    type=int,
    default=50,
    help="Number of characters -including spaces- to wrap a line of text. Default: 50",
)

parser.add_argument(
    "-t",
    "--translator",
    type=str,
    choices=["deepl-web", "translatepy"],
    help="Built-in translator to use",
    default="deepl-web",
)

parser.add_argument(
    "-p",
    "--proxy",
    type=str,
    help="Default proxy to use",
)

builtin_translators = {
    "deepl-web": DeeplTranslator,
    "translatepy": TranslatePy,
}

args = parser.parse_args()
logging.basicConfig(level=args.loglevel)

try:
    os.environ.pop("MOZ_HEADLESS")
except:
    pass

if not args.show_browser:
    os.environ["MOZ_HEADLESS"] = "1"

translator = builtin_translators[args.translator]()

srt = SrtFile(args.filepath)
srt.translate(translator, args.src_lang, args.dest_lang)
srt.wrap_lines(args.wrap_limit)
srt.save(f"{os.path.splitext(args.filepath)[0]}_{args.dest_lang}.srt")

translator.quit()
