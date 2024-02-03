import os
import toga
import asyncio
import builtins
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from srtranslator.srt_file import SrtFile
from srtranslator.ass_file import AssFile
from srtranslator.translators.deepl_api import DeeplApi
from srtranslator.translators.deepl_scrap import DeeplTranslator
from srtranslator.translators.translatepy import TranslatePy
from srtranslator.translators.pydeeplx import PyDeepLX
from .toga_from_xml import parse_layout

_print = print


class Srtranslator(toga.App):
    filepath = ""
    builtin_translators = [
        {
            "id": "deepl-scrap",
            "name": "DeepL Scraper",
            "description": "Web scraper with selenium. Opens Gecodriver (firefox) to translate chunks of 1500 lines",
            "handler": DeeplTranslator,
        },
        {
            "id": "deepl-api",
            "name": "DeepL API",
            "description": "Uses a paid DeepL subscription to translate the files",
            "handler": DeeplApi,
        },
        {
            "id": "translatepy",
            "name": "TranslatePy",
            "description": "Uses TranslatePy library to translate from DeepL REST free api",
            "handler": TranslatePy,
        },
        {
            "id": "pydeeplx",
            "name": "PyDeepLX",
            "description": "Uses PyDeepLX library to translate from DeepL REST free api",
            "handler": PyDeepLX,
        },
    ]

    def startup(self):
        with open(f"{self.paths.app}/resources/layout.xml", "r") as f:
            self.main_window = parse_layout(self, f.read())
            self.main_window.show()

    async def set_filepath(self, widget):
        self.filepath = await self.open_file_dialog()
        self.widgets["filepath-label"].text = self.filepath

    async def open_file_dialog(self):
        return await self.main_window.open_file_dialog(
            "title",
            initial_directory=None,
            multiple_select=False,
            file_types=["srt", "ass"],
        )

    def get_source_language(self):
        return self.widgets["src-lang"].value.id

    def get_target_language(self):
        return self.widgets["dest-lang"].value.id

    def get_translator(self):
        return next(
            (
                translator["handler"]()
                for translator in self.builtin_translators
                if translator["id"] == self.widgets["translator"].value.id
            ),
            None,
        )

    async def translate_async(self, widget):
        if not self.filepath:
            return

        self.widgets["loading-indicator"].start()
        for widget in self.widgets:
            widget.enabled = False

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.translate)
        except:
            pass

        self.widgets["loading-indicator"].stop()
        for widget in self.widgets:
            widget.enabled = True

    def translate(self):
        translator = self.get_translator()
        if translator is None:
            return

        wrap_limit = 50
        src_lang = self.get_source_language()
        dest_lang = self.get_target_language()

        try:
            sub = AssFile(self.filepath)
        except AttributeError:
            print("... Exception while loading as ASS try as SRT")
            sub = SrtFile(self.filepath)

        try:
            sub.translate(translator, src_lang, dest_lang)
            sub.wrap_lines(wrap_limit)

            filename = os.path.splitext(self.filepath)
            sub.save(f"{filename[0]}_{dest_lang}{filename[1]}")
        except:
            sub.save_backup()
            traceback.print_exc()

        translator.quit()


def main():
    app = Srtranslator()

    builtins.print = lambda *args, **kwargs: xprint(*args, **kwargs)

    def xprint(*args, **kwargs):
        _print(*args, **kwargs)
        for arg in args:
            try:
                app.widgets["terminal"].text += arg + "\n"
            except:
                pass

    return app
