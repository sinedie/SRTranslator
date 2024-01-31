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

_print = print

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

languages = [
    {"id": "auto", "name": "Any language (detect)"},
    {"id": "bg", "name": "Bulgarian"},
    {"id": "zh", "name": "Chinese"},
    {"id": "cs", "name": "Czech"},
    {"id": "da", "name": "Danish"},
    {"id": "nl", "name": "Dutch"},
    {"id": "en", "name": "English", "noDest": True},
    {"id": "en-US", "name": "English (American)", "noSrc": True},
    {"id": "en-GB", "name": "English (British)", "noSrc": True},
    {"id": "et", "name": "Estonian"},
    {"id": "fi", "name": "Finnish"},
    {"id": "fr", "name": "French"},
    {"id": "de", "name": "German"},
    {"id": "el", "name": "Greek"},
    {"id": "hu", "name": "Hungarian"},
    {"id": "id", "name": "Indonesian"},
    {"id": "it", "name": "Italian"},
    {"id": "ja", "name": "Japanese"},
    {"id": "ko", "name": "Korean"},
    {"id": "lv", "name": "Latvian"},
    {"id": "lt", "name": "Lithuanian"},
    {"id": "pl", "name": "Polish"},
    {"id": "pt", "name": "Portuguese", "noDest": True},
    {"id": "pt-PT", "name": "Portuguese", "noSrc": True},
    {"id": "pt-BR", "name": "Portuguese (Brazilian)", "noSrc": True},
    {"id": "ro", "name": "Romanian"},
    {"id": "ru", "name": "Russian"},
    {"id": "sk", "name": "Slovak"},
    {"id": "sl", "name": "Slovenian"},
    {"id": "es", "name": "Spanish"},
    {"id": "sv", "name": "Swedish"},
    {"id": "tr", "name": "Turkish"},
    {"id": "uk", "name": "Ukrainian"},
]


class Srtranslator(toga.App):
    filepath = ""

    def startup(self):
        main_box = toga.Box(
            children=[
                toga.Selection(
                    items=builtin_translators, accessor="name", id="translator"
                ),
                toga.Selection(
                    items=[lang for lang in languages if not lang.get("noSrc", False)],
                    accessor="name",
                    id="src-lang",
                ),
                toga.Selection(
                    items=[lang for lang in languages if not lang.get("noDest", False)],
                    accessor="name",
                    id="dest-lang",
                ),
                toga.Label(self.filepath, id="filepath-label"),
                toga.Button(
                    "Choose file",
                    on_press=self.set_filepath,
                ),
                toga.Button("Translate", on_press=self.translate_async),
                toga.Label("", id="terminal"),
            ],
            style=Pack(direction=COLUMN),
        )

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box

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
                for translator in builtin_translators
                if translator["id"] == self.widgets["translator"].value.id
            ),
            None,
        )

    async def translate_async(self, widget):
        self.disabled = True
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(None, self.translate)
        except:
            pass

        self.disabled = False

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
