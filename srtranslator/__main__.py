import os
import argparse
import logging
import traceback

from .srt_file import SrtFile
from .translators.deepl_api import DeeplApi
from .translators.deepl_scrap import DeeplTranslator
from .translators.translatepy import TranslatePy
from .translators.pydeeplx import PyDeepLX

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
    choices=["deepl-scrap", "translatepy", "deepl-api", "deeplx"],
    help="Built-in translator to use",
    default="deepl-scrap",
)

parser.add_argument(
    "--auth",
    type=str,
    help="Api key if needed on translator",
)

parser.add_argument(
    "--proxies",
    action="store_true",
    help="Use proxy by default for pydeeplx",
)

builtin_translators = {
    "deepl-scrap": DeeplTranslator,
    "deepl-api": DeeplApi,
    "translatepy": TranslatePy,
    "pydeeplx": PyDeepLX,
}

args = parser.parse_args()
logging.basicConfig(level=args.loglevel)

try:
    os.environ.pop("MOZ_HEADLESS")
except:
    pass

if not args.show_browser:
    os.environ["MOZ_HEADLESS"] = "1"

translator_args = {}
if args.auth:
    translator_args["api_key"] = args.auth
if args.proxies:
    translator_args["proxies"] = args.proxies    

translator = builtin_translators[args.translator](**translator_args)

srt = SrtFile(args.filepath)

try:
    srt.translate(translator, args.src_lang, args.dest_lang)
    srt.wrap_lines(args.wrap_limit)
    srt.save(f"{os.path.splitext(args.filepath)[0]}_{args.dest_lang}.srt")
except:
    srt.save_backup()
    traceback.print_exc()

translator.quit()
