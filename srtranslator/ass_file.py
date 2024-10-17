import os
import re
import pyass

from typing import List, Generator

from .translators.base import Translator
from .util import show_progress


class AssFile:
    """ASS file class abstraction

    Args:
        filepath (str): file path of ass
    """

    def __init__(self, filepath: str, progress_callback=show_progress) -> None:
        self.filepath = filepath
        self.backup_file = f"{self.filepath}.tmp"
        self.subtitles = []
        self.start_from = 0
        self.current_subtitle = 0
        self.text_styles = []
        self.progress_callback = progress_callback

        print(f"Loading {filepath} as ASS")
        with open(filepath, "r", encoding="utf-8", errors="ignore") as input_file:
            self.subtitles = self.load_from_file(input_file)

        self._load_backup()

    def _load_backup(self):
        if not os.path.exists(self.backup_file):
            return

        print(f"Backup file found = {self.backup_file}")
        with open(
            self.backup_file, "r", encoding="utf-8", errors="ignore"
        ) as input_file:
            subtitles = self.load_from_file(input_file)

            self.start_from = len(subtitles.events)
            self.current_subtitle = self.start_from
            print(f"Starting from subtitle {self.start_from}")
            self.subtitles.events = [
                *subtitles.events,
                *self.subtitles.events[self.start_from :],
            ]

    def load_from_file(self, input_file):
        ass_file = pyass.load(input_file)
        ass_file.events = sorted(ass_file.events, key=lambda e: (e.start))
        return self._clean_subs_content(ass_file)

    def _get_next_chunk(self, chunk_size: int = 4500) -> Generator:
        """Get a portion of the subtitles at the time based on the chunk size

        Args:
            chunk_size (int, optional): Maximum number of letter in text chunk. Defaults to 4500.

        Yields:
            Generator: Each chunk at the time
        """
        portion = []

        for subtitle in self.subtitles.events[self.start_from :]:
            # Manage ASS styles for subtitle before add it to the portion
            # Extract a list of styles
            # Replace the styles by |

            # Each style starts with { and end with }
            # If we have an "}" then we can split and keep the part on the left and keep it in our list
            for i in subtitle.text.split("{"):
                if "}" in i:
                    self.text_styles.append("{" + i.split("}")[0] + "}")

            subtitle.text = re.sub(r"{.*?}", r"|", subtitle.text)

            # Calculate new chunk size if subtitle content is added to actual chunk
            n_char = (
                sum(len(sub.text) for sub in portion)  # All subtitles in chunk
                + len(subtitle.text)  # New subtitle
                + len(portion)  # Break lines in chunk
                + 1  # New breakline
            )

            # If chunk goes beyond the limit, yield it
            if n_char >= chunk_size and len(portion) != 0:
                yield portion
                portion = []

            # Put subtitle content in chunk
            portion.append(subtitle)

        # Yield last chunk
        yield portion

    def _clean_subs_content(self, subtitles):
        """Cleans subtitles content and delete line breaks

        Args:
            subtitles List of subtitles

        Returns:
            Same list of subtitles, but cleaned
        """
        cleanr = re.compile("<.*?>")

        for sub in subtitles.events:
            sub.text = cleanr.sub("", sub.text)
            # No real equivalent in ASS
            # sub.text = srt.make_legal_content(sub.content)
            sub.text = sub.text.strip()

            if sub.text == "":
                sub.text = "..."

            if all(sentence.startswith("-") for sentence in sub.text.split("\n")):
                sub.text = sub.text.replace("\n", "////")
                continue

            # It looks like \N is removed by the translation so we replace them by \\\\
            sub.text = sub.text.replace(r"\N", r"\\\\")

            # The \\\\ must be separated from the words to avoid weird conversions
            sub.text = re.sub(r"[aA0-zZ9]\\\\", r" \\\\", sub.text)
            sub.text = re.sub(r"\\\\[aA0-zZ9]", r"\\\\ ", sub.text)

            sub.text = sub.text.replace("\n", " ")

        return subtitles

    def wrap_lines(self, line_wrap_limit: int = 50) -> None:
        """

        Args:
            line_wrap_limit (int): Number of maximum characters in a line before wrap. Defaults to 50. (not used)
        """
        for sub in self.subtitles.events:
            sub.text = sub.text.replace("////", "\n")
            sub.text = sub.text.replace(r" \\\\ ", r"\N")

    def translate(
        self,
        translator: Translator,
        source_language: str,
        destination_language: str,
    ) -> None:
        """Translate ASS file using a translator of your choose

        Args:
            translator (Translator): Translator object of choose
            destination_language (str): Destination language (must be coherent with your translator)
            source_language (str): Source language (must be coherent with your translator)
        """
        print("Starting translation")

        # For each chunk of the file (based on the translator capabilities)
        for subs_slice in self._get_next_chunk(translator.max_char):
            # Put chunk in a single text with break lines
            text = [sub.text for sub in subs_slice]
            text = "\n".join(text)

            # Translate
            translation = translator.translate(
                text, source_language, destination_language
            )

            # Manage ASS commands
            # Insert the styles back in the text instead of |
            self.text_styles.reverse()
            translation_with_styles = ""
            for i in translation.split(r"|"):
                try:
                    # We set i at the left part because the style must "replace" the "|"
                    translation_with_styles += i + self.text_styles.pop()
                except IndexError:
                    translation_with_styles += i

            # Break each line back into subtitle content
            translation = translation_with_styles.splitlines()
            for i in range(len(subs_slice)):
                subs_slice[i].text = translation[i]
                self.current_subtitle += 1

            self.progress_callback(
                len(self.subtitles.events), progress=self.current_subtitle
            )

        print(f"... Translation done")

    def save_backup(self):
        self.subtitles.events = self.subtitles.events[: self.current_subtitle]
        self.save(self.backup_file)

    def _delete_backup(self):
        if os.path.exists(self.backup_file):
            os.remove(self.backup_file)

    def save(self, filepath: str) -> None:
        """Saves ASS to file

        Args:
            filepath (str): Path of the new file
        """
        self._delete_backup()

        print(f"Saving {filepath}")
        with open(filepath, "w", encoding="utf-8") as file_out:
            pyass.dump(self.subtitles, file_out)
