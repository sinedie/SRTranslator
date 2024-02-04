import os
import glob
import toga
import asyncio
import builtins
import traceback
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from srtranslator.srt_file import SrtFile
from srtranslator.ass_file import AssFile
from srtranslator.translators.deepl_api import DeeplApi
from srtranslator.translators.deepl_scrap import DeeplTranslator
from srtranslator.translators.translatepy import TranslatePy
from srtranslator.translators.pydeeplx import PyDeepLX
from togax_xml_layout import parse_layout

_print = print


class Srtranslator(toga.App):
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
        self.widgets["filepath"].value = await self.open_file_dialog()

    async def set_folder(self, widget):
        self.widgets["filepath"].value = await self.open_file_dialog(folder=True)

    async def open_file_dialog(self, folder=False):
        if folder:
            return await self.main_window.select_folder_dialog(
                "Select folder",
            )

        return await self.main_window.open_file_dialog(
            "Select file",
            file_types=["srt", "ass"],
        )

    def handle_translator_change(self, widget):
        try:
            self.widgets["api-token"].enabled = widget.value.id == "deepl-api"
        except:
            pass

    def get_translator(self):
        translator_args = {}
        if self.widgets["translator"].value.id == "deepl-api":
            translator_args["api_key"] = self.widgets["api-token"].value

        return next(
            (
                translator["handler"](**translator_args)
                for translator in self.builtin_translators
                if translator["id"] == self.widgets["translator"].value.id
            ),
            None,
        )

    async def translate_async(self, widget):
        filepath = self.widgets["filepath"].value
        if not filepath or not os.path.exists(filepath):
            return

        self.set_loading(True)

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.translate)
        except:
            traceback.print_exc()

        self.set_loading(False)

    def set_loading(self, loading):
        if loading:
            self.widgets["loading-indicator"].start()
        else:
            self.widgets["loading-indicator"].stop()

        for widget in self.widgets:
            widget.enabled = not loading

    def translate_file(self, translator, filepath):
        src_lang = self.widgets["src-lang"].value.id
        dest_lang = self.widgets["dest-lang"].value.id
        wrap_limit = self.widgets["wrap_limit"].value

        try:
            sub = AssFile(filepath)
        except AttributeError:
            print("... Exception while loading as ASS try as SRT")
            sub = SrtFile(filepath)

        try:
            sub.translate(translator, src_lang, dest_lang)
            sub.wrap_lines(wrap_limit)

            filename = os.path.splitext(filepath)
            sub.save(f"{filename[0]}_{dest_lang}{filename[1]}")
        except:
            sub.save_backup()
            traceback.print_exc()

    def translate(self):
        translator = self.get_translator()
        if translator is None:
            return

        filepath = self.widgets["filepath"].value

        if os.path.isdir(filepath):
            for f in glob.glob(os.path.join(filepath, "**/*.ass"), recursive=True):
                self.translate_file(translator, f)
            for f in glob.glob(os.path.join(filepath, "**/*.srt"), recursive=True):
                self.translate_file(translator, f)
        else:
            self.translate_file(translator, filepath)

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
