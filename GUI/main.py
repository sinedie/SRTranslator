import os
import glob
import json
import flet as ft
import traceback
import asyncio
from srtranslator.srt_file import SrtFile
from srtranslator.ass_file import AssFile
from srtranslator.translators.deepl_api import DeeplApi
from srtranslator.translators.deepl_scrap import DeeplTranslator
from srtranslator.translators.pydeeplx import PyDeepLX
from srtranslator.translators.translatepy import TranslatePy

builtin_translators = [
    {
        "id": "deepl-scrap",
        "name": "DeepL Scraper",
        "description": "Web scraper with selenium. Opens Gecodriver (firefox) to translate chunks of 1500 lines",
        "handler": DeeplTranslator,
    },
    # {
    #     "id": "deepl-api",
    #     "name": "DeepL API",
    #     "description": "Uses a paid DeepL subscription to translate the files",
    #     "handler": DeeplApi,
    # },
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


def vertical_app(*children):
    return ft.SafeArea(column(*children))


def column(*children):
    return ft.Column(children)


def row(*children):
    return ft.Row(children)


def pick_files_result(e: ft.FilePickerResultEvent, selected_files: ft.TextField):
    if e.files:
        value = ", ".join(map(lambda f: f.path, e.files))
        selected_files.value = value
        selected_files.update()


def get_directory_result(e: ft.FilePickerResultEvent, directory_path: ft.TextField):
    if e.path:
        directory_path.value = e.path
        directory_path.update()


def counter(value_container: ft.Text):
    def minus_click(e):
        try:
            new_value = str(int(txt_number.value) - 1)
            update(e, new_value)
        except:
            update(e, value_container.value)

    def plus_click(e):
        try:
            new_value = str(int(txt_number.value) + 1)
            update(e, new_value)
        except:
            update(e, value_container.value)

    def handle_input_change(e):
        try:
            txt_number.value = txt_number.value or "0"
            new_value = str(int(e.control.value))
            update(e, new_value)
        except:
            update(e, value_container.value)

    def update(e, new_value: str):
        txt_number.value = new_value
        value_container.value = new_value
        e.page.update()

    txt_number = ft.TextField(
        label="Wrap lines limit",
        value=value_container.value,
        text_align=ft.TextAlign.CENTER,
        on_change=handle_input_change,
    )

    return ft.Row(
        [
            ft.IconButton(ft.icons.REMOVE, on_click=minus_click),
            ft.Container(expand=1, content=txt_number),
            ft.IconButton(ft.icons.ADD, on_click=plus_click),
        ],
    )


def folder_picker_dialog(path_field: ft.TextField):
    pick_folder_dialog = ft.FilePicker(
        on_result=lambda e: get_directory_result(e, path_field)
    )

    pick_folder_trigger = ft.ElevatedButton(
        "Open directory",
        icon=ft.icons.FOLDER_OPEN,
        on_click=lambda _: pick_folder_dialog.get_directory_path(),
    )

    return pick_folder_trigger, pick_folder_dialog


def file_picker_dialog(path_field: ft.TextField):
    pick_files_dialog = ft.FilePicker(
        on_result=lambda e: pick_files_result(e, path_field)
    )

    pick_files_trigger = ft.ElevatedButton(
        "Pick files",
        icon=ft.icons.UPLOAD_FILE,
        on_click=lambda _: pick_files_dialog.pick_files(
            allow_multiple=True, allowed_extensions=["srt", "ass"]
        ),
    )

    return pick_files_trigger, pick_files_dialog


def translators_dropdown():
    return ft.Dropdown(
        label="Translator",
        value=builtin_translators[0]["id"],
        options=[
            ft.dropdown.Option(key=option["id"], text=option["name"])
            for option in builtin_translators
        ],
    )


def source_language_dropdown():
    with open("./assets/source_languages.json") as f:
        source_languages = json.load(f)

    return ft.Dropdown(
        label="Source language",
        value=source_languages[0]["id"],
        options=[
            ft.dropdown.Option(key=option["id"], text=option["name"])
            for option in source_languages
        ],
    )


def destination_language_dropdown():
    with open("./assets/destination_languages.json") as f:
        destination_languages = json.load(f)

    return ft.Dropdown(
        label="Destination language",
        value=destination_languages[0]["id"],
        options=[
            ft.dropdown.Option(key=option["id"], text=option["name"])
            for option in destination_languages
        ],
    )


def get_translator(translator_id: str):
    translator = next(
        (
            translator
            for translator in builtin_translators
            if translator["id"] == translator_id
        ),
        {},
    )

    handler = translator.get("handler", None)

    return handler() if handler is not None else None


class TranslationProgress(ft.Container):
    def __init__(
        self,
        filepath: str,
        translator_id: str,
        src_lang: str,
        dest_lang: str,
        wrap_limit: int,
    ):
        super().__init__()
        self.filepath = filepath
        self.translator_id = translator_id
        self.src_lang = src_lang
        self.dest_lang = dest_lang
        self.wrap_limit = int(wrap_limit)
        self.cancelled = False

        self.progress_bar = ft.ProgressBar()
        self.close_button = ft.IconButton(
            icon=ft.icons.CLOSE,
            icon_size=20,
            tooltip="Cancel",
            on_click=self.remove,
        )
        self.content = row(
            ft.Container(expand=2, content=ft.Text(self.filepath)),
            ft.Container(
                expand=1,
                content=ft.Text(self.src_lang, text_align=ft.TextAlign.CENTER),
            ),
            ft.Container(
                expand=1,
                content=ft.Text(self.dest_lang, text_align=ft.TextAlign.CENTER),
            ),
            ft.Container(expand=2, content=self.progress_bar),
            self.close_button,
        )

    def remove(self, e):
        self.cancelled = True
        self.page.controls.remove(self)
        self.page.update()

    def show_progress(self, total: float, progress: float):
        self.progress_bar.value = min(1, float(progress) / float(total))
        self.page.update()

    def translate(self):
        if self.cancelled:
            return

        self.close_button.disabled = True
        self.page.update()

        translator = get_translator(self.translator_id)
        if translator is None:
            raise Exception("Translator is None")

        if self.filepath.endswith("ass"):
            sub = AssFile(self.filepath, self.show_progress)
        elif self.filepath.endswith("srt"):
            sub = SrtFile(self.filepath, self.show_progress)
        else:
            raise Exception("File type not supported")

        try:
            sub.translate(translator, self.src_lang, self.dest_lang)
            sub.wrap_lines(self.wrap_limit)

            filename = os.path.splitext(self.filepath)
            sub.save(f"{filename[0]}_{self.dest_lang}{filename[1]}")
        except:
            sub.save_backup()
            traceback.print_exc()
            raise Exception("Error while translating")

        translator.quit()
        self.close_button.disabled = False
        self.page.update()


def handle_translation(
    page: ft.Page,
    path_field_input: ft.TextField,
    translator: str,
    src_lang: str,
    dest_lang: str,
    wrap_limit: str,
):
    if not path_field_input.value:
        return

    files = []
    for filepath in path_field_input.value.split(","):
        if not os.path.isdir(filepath):
            files.append(filepath)
            continue

        get_all_files = lambda ext: glob.glob(
            os.path.join(glob.escape(filepath), f"**/*.{ext}"), recursive=True
        )
        files.extend(get_all_files("ass"))
        files.extend(get_all_files("srt"))

    translations = [
        TranslationProgress(file, translator, src_lang, dest_lang, int(wrap_limit))
        for file in files
    ]

    path_field_input.value = ""
    page.add(*translations)

    for process in translations:
        try:
            process.translate()
        except:
            process.close_button.disabled = False
            process.progress_bar.value = 1
            process.progress_bar.color = "red"
            page.update()


def main(page: ft.Page):
    page.theme_mode = "dark"

    wrap_limit = ft.Text(value=50)
    path_field = ft.TextField(label="Path")
    pick_folder_trigger, pick_folder_dialog = folder_picker_dialog(path_field)
    pick_files_trigger, pick_files_dialog = file_picker_dialog(path_field)
    translator_dropdown = translators_dropdown()
    source_lang_dropdown = source_language_dropdown()
    dest_lang_dropdown = destination_language_dropdown()
    submit_button = ft.OutlinedButton(
        "Translate",
        on_click=lambda x: handle_translation(
            page,
            path_field,
            translator_dropdown.value,
            source_lang_dropdown.value,
            dest_lang_dropdown.value,
            wrap_limit.value,
        ),
    )

    page.overlay.extend([pick_files_dialog, pick_folder_dialog])
    page.add(
        vertical_app(
            ft.Row(
                [ft.Text("SRTranslatorGUI")],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            row(
                ft.Container(expand=1, content=path_field),
                pick_files_trigger,
                pick_folder_trigger,
            ),
            translator_dropdown,
            source_lang_dropdown,
            dest_lang_dropdown,
            counter(wrap_limit),
            row(ft.Container(expand=1, content=submit_button)),
        )
    )


ft.app(target=main)
