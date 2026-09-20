import textwrap

import pytest

from srtranslator.ass_file import AssFile

ASS_HEADER = """
[Script Info]
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_ass(tmp_path, *texts):
    lines = [
        f"Dialogue: 0,0:00:{i:02d}.00,0:00:{i + 1:02d}.00,Default,,0,0,0,,{text}"
        for i, text in enumerate(texts)
    ]
    path = tmp_path / "sample.ass"
    path.write_text(
        textwrap.dedent(ASS_HEADER).strip() + "\n" + "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return path


def texts(ass_file):
    return [event.text for event in ass_file.subtitles.events]


@pytest.mark.parametrize(
    "original",
    [
        r"The ship is ready\Nto sail.",
        r"Hello\NWorld",
        r"a\Nb",
        r"one\Ntwo\Nthree",
        r"spaced \N break",
    ],
)
def test_line_break_placeholder_round_trips(tmp_path, original):
    """\\N survives the encode/restore cycle without eating neighbours."""
    ass_file = AssFile(str(write_ass(tmp_path, original)))

    # Encoded for translation: no raw \N, neighbouring characters intact
    encoded = texts(ass_file)[0]
    assert r"\N" not in encoded
    for word in original.replace(r"\N", " ").split():
        assert word in encoded

    # Restored on the way out
    ass_file.wrap_lines()
    assert texts(ass_file)[0] == original.replace(" \\N ", "\\N")


def test_neighbouring_characters_are_not_eaten(tmp_path):
    ass_file = AssFile(str(write_ass(tmp_path, r"The ship is ready\Nto sail.")))

    encoded = texts(ass_file)[0]
    assert "ready" in encoded
    assert "to sail." in encoded
    assert "read " not in encoded


def test_restore_tolerates_collapsed_backslashes(tmp_path):
    """A translator may return fewer backslashes than were sent."""
    ass_file = AssFile(str(write_ass(tmp_path, r"Hello\NWorld")))
    ass_file.subtitles.events[0].text = "Hola \\\\ Mundo"

    ass_file.wrap_lines()

    assert texts(ass_file)[0] == r"Hola\NMundo"


def test_single_backslash_is_left_alone(tmp_path):
    ass_file = AssFile(str(write_ass(tmp_path, "path C:\\temp here")))

    ass_file.wrap_lines()

    assert "\\N" not in texts(ass_file)[0]


def test_dialog_markers_still_use_the_other_placeholder(tmp_path):
    ass_file = AssFile(str(write_ass(tmp_path, "-Yes\\N-No")))

    # All-dash lines keep the //// placeholder path
    ass_file.wrap_lines()
    assert texts(ass_file)[0] in ("-Yes\\N-No", "-Yes\n-No")


def test_context_has_no_placeholder_leftovers(tmp_path):
    ass_file = AssFile(str(write_ass(tmp_path, r"The ship is ready\Nto sail.", "Later.")))

    context = ass_file._build_deepl_context(
        scene_index=0,
        chunk_start_idx=0,
        chunk_end_idx=1,
        scene_start_idx=0,
        scene_end_idx=1,
        chunk_lines=texts(ass_file),
    )

    assert "\\" not in context
    assert "1. The ship is ready to sail." in context
