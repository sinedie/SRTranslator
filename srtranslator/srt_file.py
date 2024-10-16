import os
import re
import srt

from srt import Subtitle
from typing import List, Generator

from .translators.base import Translator
from .util import show_progress


class SrtFile:
    """SRT file class abstraction

    Args:
        filepath (str): file path of srt
    """

    def __init__(self, filepath: str, progress_callback=show_progress) -> None:
        self.filepath = filepath
        self.backup_file = f"{self.filepath}.tmp"
        self.subtitles = []
        self.start_from = 0
        self.current_subtitle = 0
        self.progress_callback = progress_callback

        print(f"Loading {filepath} as SRT")
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

            self.start_from = len(subtitles)
            self.current_subtitle = self.start_from
            print(f"Starting from subtitle {self.start_from}")
            self.subtitles = [
                *subtitles,
                *self.subtitles[self.start_from :],
            ]

    def load_from_file(self, input_file):
        srt_file = srt.parse(input_file)
        subtitles = list(srt_file)
        subtitles = list(srt.sort_and_reindex(subtitles))
        return self._clean_subs_content(subtitles)

    def _get_next_chunk(self, chunk_size: int = 4500) -> Generator:
        """Get a portion of the subtitles at the time based on the chunk size

        Args:
            chunk_size (int, optional): Maximum number of letter in text chunk. Defaults to 4500.

        Yields:
            Generator: Each chunk at the time
        """
        portion = []

        for subtitle in self.subtitles[self.start_from :]:
            # Calculate new chunk size if subtitle content is added to actual chunk
            n_char = (
                sum(len(sub.content) for sub in portion)  # All subtitles in chunk
                + len(subtitle.content)  # New subtitle
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

    def _clean_subs_content(self, subtitles: List[Subtitle]) -> List[Subtitle]:
        """Cleans subtitles content and delete line breaks

        Args:
            subtitles (List[Subtitle]): List of subtitles

        Returns:
            List[Subtitle]: Same list of subtitles, but cleaned
        """
        cleanr = re.compile("<.*?>")

        for sub in subtitles:
            sub.content = cleanr.sub("", sub.content)
            sub.content = srt.make_legal_content(sub.content)
            sub.content = sub.content.strip()

            if sub.content == "":
                sub.content = "..."

            if all(sentence.startswith("-") for sentence in sub.content.split("\n")):
                sub.content = sub.content.replace("\n", "////")
                continue

            sub.content = sub.content.replace("\n", " ")

        return subtitles

    def wrap_lines(self, line_wrap_limit: int = 50) -> None:
        """Wrap lines in all subtitles in file

        Args:
            line_wrap_limit (int): Number of maximum characters in a line before wrap. Defaults to 50.
        """
        for sub in self.subtitles:
            sub.content = sub.content.replace("////", "\n")

            content = []
            for line in sub.content.split("\n"):
                if len(line) > line_wrap_limit:
                    line = self.wrap_line(line, line_wrap_limit)
                content.append(line)

            sub.content = "\n".join(content)

    def wrap_line(self, text: str, line_wrap_limit: int = 50) -> str:
        """Wraps a line of text without breaking any word in half

        Args:
            text (str): Line text to wrap
            line_wrap_limit (int): Number of maximum characters in a line before wrap. Defaults to 50.

        Returns:
            str: Text line wraped
        """
        wraped_lines = []
        for word in text.split():
            # Check if inserting a word in the last sentence goes beyond the wrap limit
            if (
                len(wraped_lines) != 0
                and len(wraped_lines[-1]) + len(word) < line_wrap_limit
            ):
                # If not, add it to it
                wraped_lines[-1] += f" {word}"
                continue

            # Insert a new sentence
            wraped_lines.append(f"{word}")

        # Join sentences with line break
        return "\n".join(wraped_lines)

    def translate(
        self,
        translator: Translator,
        source_language: str,
        destination_language: str,
    ) -> None:
        """Translate SRT file using a translator of your choose

        Args:
            translator (Translator): Translator object of choose
            destination_language (str): Destination language (must be coherent with your translator)
            source_language (str): Source language (must be coherent with your translator)
        """
        print("Starting translation")

        # For each chunk of the file (based on the translator capabilities)
        for subs_slice in self._get_next_chunk(translator.max_char):
            # Put chunk in a single text with break lines
            text = [sub.content for sub in subs_slice]
            text = "\n".join(text)

            # Translate
            translation = translator.translate(
                text, source_language, destination_language
            )

            # Break each line back into subtitle content
            translation = translation.splitlines()
            for i in range(len(subs_slice)):
                subs_slice[i].content = translation[i]
                self.current_subtitle += 1

            self.progress_callback(len(self.subtitles), progress=self.current_subtitle)

        print(f"... Translation done")

    def save_backup(self):
        self.subtitles = self.subtitles[: self.current_subtitle]
        self.save(self.backup_file)

    def _delete_backup(self):
        if os.path.exists(self.backup_file):
            os.remove(self.backup_file)

    def save(self, filepath: str) -> None:
        """Saves SRT to file

        Args:
            filepath (str): Path of the new file
        """
        self._delete_backup()

        print(f"Saving {filepath}")
        subtitles = srt.compose(self.subtitles)
        with open(filepath, "w", encoding="utf-8") as file_out:
            file_out.write(subtitles)
