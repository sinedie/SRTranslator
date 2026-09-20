from __future__ import annotations

import argparse
import logging
import os
import sys
import traceback
from typing import Dict, Type

from .ass_file import AssFile
from .srt_file import SrtFile
from .translators.base import Translator
from .translators.deepl_api import DeeplApi
from .translators.deepl_scrap import DeeplTranslator
from .translators.pydeeplx import PyDeepLX
from .translators.translatepy import TranslatePy

LOG = logging.getLogger("srtranslator")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="srtranslator",
        description="Translate .srt and .ass subtitle files from the command line",
    )

    parser.add_argument(
        "filepath",
        metavar="path",
        type=str,
        help="Subtitle file to translate",
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
        help="Destination language. Default: es (Spanish)",
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
        help="Show browser window (Selenium-based translators)",
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
        choices=["deepl-scrap", "translatepy", "deepl-api", "pydeeplx"],
        help="Built-in translator to use",
        default="deepl-scrap",
    )

    parser.add_argument(
        "--auth",
        type=str,
        help="API key if needed by the translator",
    )

    parser.add_argument(
        "--proxies",
        action="store_true",
        help="Use proxy by default for pydeeplx",
    )

    parser.add_argument(
        "--context",
        type=str,
        help="Context for DeepL translation (only for deepl-api)",
    )

    parser.add_argument(
        "--model-type",
        type=str,
        choices=["quality_optimized", "latency_optimized", "prefer_quality_optimized"],
        default="quality_optimized",
        help=(
            "DeepL model type (only for deepl-api). quality_optimized is the "
            "next-generation model and the default. latency_optimized is the "
            "faster classic model. prefer_quality_optimized is a legacy alias "
            "of quality_optimized. Default: quality_optimized"
        ),
    )

    parser.add_argument(
        "--instruction",
        type=str,
        action="append",
        dest="custom_instructions",
        metavar="TEXT",
        help=(
            "DeepL custom instruction, repeatable (only for deepl-api). At most "
            "10 instructions of 300 characters each. Supported for target "
            "languages de, en, es, fr, it, ja, ko and zh only; ignored with a "
            "warning for any other target. Cannot be combined with "
            "--model-type latency_optimized"
        ),
    )

    return parser


BUILTIN_TRANSLATORS: Dict[str, Type[Translator]] = {
    "deepl-scrap": DeeplTranslator,
    "deepl-api": DeeplApi,
    "translatepy": TranslatePy,
    "pydeeplx": PyDeepLX,
}


def configure_logging(level: int | None) -> None:
    logging.basicConfig(level=level or logging.WARNING, format="%(message)s")


def configure_headless(show_browser: bool) -> None:
    if show_browser:
        os.environ.pop("MOZ_HEADLESS", None)
        return
    os.environ["MOZ_HEADLESS"] = "1"


def load_subtitle(filepath: str):
    try:
        return AssFile(filepath)
    except AttributeError:
        LOG.info("Falling back to SRT parsing")
        return SrtFile(filepath)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if sys.platform.startswith("win"):
        parser.error("SRTranslator CLI supports Linux and macOS only.")

    configure_logging(args.loglevel)
    configure_headless(args.show_browser)

    translator_args = {}
    if args.auth:
        translator_args["api_key"] = args.auth

    if args.translator == "pydeeplx" and args.proxies:
        translator_args["proxies"] = args.proxies

    if args.translator == "deepl-api":
        if args.context:
            translator_args["context"] = args.context
        translator_args["model_type"] = args.model_type
        if args.custom_instructions:
            if len(args.custom_instructions) > 10:
                parser.error("--instruction can be used at most 10 times")
            translator_args["custom_instructions"] = args.custom_instructions
    elif args.custom_instructions:
        parser.error("--instruction is only supported by the deepl-api translator")

    try:
        translator = BUILTIN_TRANSLATORS[args.translator](**translator_args)
    except ValueError as error:
        parser.error(str(error))

    sub = None
    try:
        sub = load_subtitle(args.filepath)

        sub.translate(translator, args.src_lang, args.dest_lang)
        sub.wrap_lines(args.wrap_limit)

        dest_path = (
            f"{os.path.splitext(args.filepath)[0]}_{args.dest_lang}"
            f"{os.path.splitext(args.filepath)[1]}"
        )
        sub.save(dest_path)
        LOG.info("Translation completed. Saved to %s", dest_path)
        return 0
    except Exception:
        if sub:
            sub.save_backup()
            LOG.error("Translation failed. Backup saved to %s", sub.backup_file)
        else:
            LOG.error("Translation failed before processing the subtitle file.")
        LOG.debug(traceback.format_exc())
        return 1
    finally:
        translator.quit()


if __name__ == "__main__":
    sys.exit(main())
