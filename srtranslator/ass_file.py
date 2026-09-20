import os
import re
import pyass

from typing import Generator, List, Optional

from .translators.base import Translator
from .util import (
    CONTEXT_BUDGETS,
    MAX_REQUEST_BODY_BYTES,
    clean_context_line,
    show_progress,
)

# Translation engines drop a literal "\N", so it is swapped for a run of
# backslashes that survives the round trip, padded so it never glues to a word.
ASS_LINE_BREAK = "\\" * 4
ASS_LINE_BREAK_PADDED = f" {ASS_LINE_BREAK} "


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
        with open(self.backup_file, "r", encoding="utf-8", errors="ignore") as input_file:
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

            # Swap the ASS line break for a placeholder that survives
            # translation. Any whitespace already around it is absorbed by the
            # padding, and the neighbouring characters are left intact.
            # A lambda replacement avoids backslash escaping in re.sub.
            sub.text = re.sub(r"\s*\\N\s*", lambda _: ASS_LINE_BREAK_PADDED, sub.text)

            sub.text = sub.text.replace("\n", " ")
            sub.text = re.sub(r" {2,}", " ", sub.text).strip()

        return subtitles

    def wrap_lines(self, line_wrap_limit: int = 50) -> None:
        """

        Args:
            line_wrap_limit (int): Number of maximum characters in a line before wrap. Defaults to 50. (not used)
        """
        for sub in self.subtitles.events:
            sub.text = sub.text.replace("////", "\n")
            # Restore ASS line breaks. Translation can change the number of
            # backslashes and the spacing around them, so accept any run of two
            # or more. A lone backslash is left alone, it may be real dialogue.
            sub.text = re.sub(r"\s*\\{2,}\s*", lambda _: r"\N", sub.text)

    def _detect_scenes(self, scene_gap_seconds: float = 2.0):
        """Detect scene boundaries based on time gaps between subtitles."""
        scene_starts = [0]

        for i in range(1, len(self.subtitles.events)):
            prev_sub = self.subtitles.events[i - 1]
            curr_sub = self.subtitles.events[i]

            gap = (curr_sub.start - prev_sub.end).total_seconds()

            if gap >= scene_gap_seconds:
                scene_starts.append(i)

        return scene_starts

    def _build_deepl_context(
        self,
        scene_index: int,
        chunk_start_idx: int,
        chunk_end_idx: int,
        scene_start_idx: int,
        scene_end_idx: int,
        chunk_lines: Optional[List[str]] = None,
        max_history_chars_before: int = 4000,
        max_history_chars_after: int = 2000,
        max_summary_chars: int = 2000,
    ) -> Optional[str]:
        """Build the DeepL context parameter for one chunk.

        DeepL translates every entry of a text list independently, so entries
        never see each other. Only `context` is shared. The current chunk is
        therefore repeated here, alongside the surrounding dialogue, all in the
        source language. Context is not billed.

        Args:
            scene_index: Current scene number
            chunk_start_idx: First subtitle index in current chunk
            chunk_end_idx: Last subtitle index in current chunk
            scene_start_idx: First subtitle index in current scene
            scene_end_idx: Last subtitle index in current scene
            chunk_lines: Source lines of the current chunk
            max_history_chars_before: Max chars for previous dialogue
            max_history_chars_after: Max chars for upcoming dialogue
            max_summary_chars: Max chars for distant scene summary

        Returns:
            str: Formatted context string for DeepL, or None when empty
        """
        # Never use already translated lines (restored from a .tmp backup) as
        # source-language context.
        history_floor = max(scene_start_idx, self.start_from)

        # Build history_before: walk backwards from chunk_start_idx - 1
        history_before_lines = []
        current_before_chars = 0

        for i in range(chunk_start_idx - 1, history_floor - 1, -1):
            line_content = clean_context_line(self.subtitles.events[i].text)
            if not line_content or line_content == "...":
                continue

            # Format: "line_num. content"
            formatted_line = f"{i + 1}. {line_content}"
            line_length = len(formatted_line) + 1  # +1 for newline

            if current_before_chars + line_length > max_history_chars_before:
                break

            history_before_lines.insert(0, formatted_line)  # Prepend to keep chronological
            current_before_chars += line_length

        # Build history_after: walk forwards from chunk_end_idx + 1
        history_after_lines = []
        current_after_chars = 0

        for i in range(chunk_end_idx + 1, scene_end_idx + 1):
            line_content = clean_context_line(self.subtitles.events[i].text)
            if not line_content or line_content == "...":
                continue

            formatted_line = f"{i + 1}. {line_content}"
            line_length = len(formatted_line) + 1

            if current_after_chars + line_length > max_history_chars_after:
                break

            history_after_lines.append(formatted_line)
            current_after_chars += line_length

        # Optional: Build scene summary for very distant history
        scene_summary_lines = []
        if max_summary_chars and chunk_start_idx - history_floor > len(history_before_lines) + 5:
            # There's distant history not captured in history_before
            summary_chars = 0
            for i in range(history_floor, chunk_start_idx - len(history_before_lines)):
                line_content = clean_context_line(self.subtitles.events[i].text)
                if not line_content or line_content == "...":
                    continue

                # Truncate each line for summary (first 50 chars)
                truncated = line_content[:50] + ("..." if len(line_content) > 50 else "")
                summary_chars += len(truncated) + 1

                if summary_chars > max_summary_chars:
                    break

                scene_summary_lines.append(truncated)

        # Lines of the current chunk, so each independently translated entry
        # can see the rest of its own chunk.
        current_lines = []
        for offset, line in enumerate(chunk_lines or []):
            line_content = clean_context_line(line)
            if not line_content or line_content == "...":
                continue
            current_lines.append(f"{chunk_start_idx + offset + 1}. {line_content}")

        # Compose final context string
        context_parts = []
        context_parts.append(f"Scene {scene_index + 1}")

        # Add distant summary if available
        if scene_summary_lines:
            context_parts.append("\nEarlier in this scene:")
            context_parts.append("\n".join(scene_summary_lines))

        # Add previous dialogue
        if history_before_lines:
            context_parts.append("\nPrevious dialogue:")
            context_parts.append("\n".join(history_before_lines))

        # Add the chunk being translated
        if current_lines:
            context_parts.append("\nCurrent dialogue:")
            context_parts.append("\n".join(current_lines))

        # Add upcoming dialogue
        if history_after_lines:
            context_parts.append("\nUpcoming dialogue:")
            context_parts.append("\n".join(history_after_lines))

        return "\n".join(context_parts) if len(context_parts) > 1 else None

    def _context_for_chunk(
        self,
        scene_index: int,
        chunk_start_idx: int,
        chunk_end_idx: int,
        scene_start_idx: int,
        scene_end_idx: int,
        chunk_lines: List[str],
    ) -> Optional[str]:
        """Build context, shrinking it until the request body fits."""
        text_bytes = sum(len(line.encode("utf-8")) for line in chunk_lines)

        context = None
        for before, after, summary in CONTEXT_BUDGETS:
            context = self._build_deepl_context(
                scene_index,
                chunk_start_idx,
                chunk_end_idx,
                scene_start_idx,
                scene_end_idx,
                chunk_lines,
                before,
                after,
                summary,
            )
            if context is None:
                return None
            if text_bytes + len(context.encode("utf-8")) <= MAX_REQUEST_BODY_BYTES:
                return context

        return context

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

        # Detect scene boundaries
        scene_starts = self._detect_scenes()
        if os.environ.get("DEBUG_CONTEXT"):
            print(f"Detected {len(scene_starts)} scenes in subtitle file")

        # Build scene map
        scene_map = {}
        for scene_idx, start_idx in enumerate(scene_starts):
            end_idx = (
                scene_starts[scene_idx + 1] - 1
                if scene_idx + 1 < len(scene_starts)
                else len(self.subtitles.events) - 1
            )
            for sub_idx in range(start_idx, end_idx + 1):
                scene_map[sub_idx] = (scene_idx, start_idx, end_idx)

        # For each chunk of the file (based on the translator capabilities)
        chunk_num = 0
        current_subtitle_idx = self.start_from

        for subs_slice in self._get_next_chunk(translator.max_char):
            chunk_num += 1
            chunk_start_idx = current_subtitle_idx
            chunk_end_idx = current_subtitle_idx + len(subs_slice) - 1

            # Get scene info for this chunk
            scene_idx, scene_start_idx, scene_end_idx = scene_map.get(
                chunk_start_idx, (0, chunk_start_idx, chunk_end_idx)
            )

            # Build text array (only lines to translate)
            text = [sub.text for sub in subs_slice]

            # Build DeepL context (surrounding lines plus the current chunk)
            current_context = self._context_for_chunk(
                scene_idx,
                chunk_start_idx,
                chunk_end_idx,
                scene_start_idx,
                scene_end_idx,
                text,
            )

            if os.environ.get("DEBUG_CONTEXT") and current_context:
                print(f"\n{'=' * 60}")
                print(f"[Chunk {chunk_num}] Lines {chunk_start_idx + 1}-{chunk_end_idx + 1}")
                print(f"Context:\n{current_context}")
                print(f"{'=' * 60}")

            # Translate with context
            translation = translator.translate(
                text, source_language, destination_language, context=current_context
            )

            if isinstance(translation, str):
                translation = translation.splitlines()

            # Manage ASS commands
            # Insert the styles back in the text instead of |
            self.text_styles.reverse()

            final_translations = []
            for line in translation:
                line_with_styles = ""
                parts = line.split(r"|")
                for i, part in enumerate(parts):
                    line_with_styles += part
                    if i < len(parts) - 1:
                        try:
                            line_with_styles += self.text_styles.pop()
                        except IndexError:
                            pass
                final_translations.append(line_with_styles)

            translation = final_translations
            for i in range(len(subs_slice)):
                subs_slice[i].text = translation[i]
                self.current_subtitle += 1

            self.progress_callback(len(self.subtitles.events), progress=self.current_subtitle)

        print("... Translation done")

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
