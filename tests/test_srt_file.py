import srt
import textwrap
from datetime import timedelta

from srtranslator.srt_file import SrtFile


def write_sample_srt(tmp_path, content: str):
    path = tmp_path / "sample.srt"
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    return path


def test_clean_subtitles_and_dialog_markers(tmp_path):
    path = write_sample_srt(
        tmp_path,
        """
        1
        00:00:00,000 --> 00:00:01,000
        Hello <b>world</b>

        2
        00:00:01,500 --> 00:00:02,500
        -Yes
        -No
        """,
    )

    srt_file = SrtFile(str(path))

    assert srt_file.subtitles[0].content == "Hello world"
    # Dialog markers should be preserved with placeholder
    assert srt_file.subtitles[1].content == "-Yes////-No"


def test_wrap_line_preserves_words(tmp_path):
    path = write_sample_srt(
        tmp_path,
        """
        1
        00:00:00,000 --> 00:00:01,000
        Just a placeholder
        """,
    )
    srt_file = SrtFile(str(path))

    wrapped = srt_file.wrap_line(
        "This is a long line that should wrap nicely", line_wrap_limit=12
    ).split("\n")

    assert all(len(line) <= 12 for line in wrapped)
    # Ensure no words are broken
    for line in wrapped:
        for word in line.split():
            assert word in "This is a long line that should wrap nicely"


def test_get_next_chunk_respects_limit(tmp_path):
    # Build three short subtitles so total length forces two chunks
    subtitles = [
        srt.Subtitle(1, timedelta(seconds=0), timedelta(seconds=1), "AAA"),
        srt.Subtitle(2, timedelta(seconds=1), timedelta(seconds=2), "BBBB"),
        srt.Subtitle(3, timedelta(seconds=2), timedelta(seconds=3), "CCCCC"),
    ]
    content = srt.compose(subtitles)
    path = write_sample_srt(tmp_path, content)

    srt_file = SrtFile(str(path))

    chunks = list(srt_file._get_next_chunk(chunk_size=10))
    assert len(chunks) == 2
    assert [sub.content for sub in chunks[0]] == ["AAA", "BBBB"]
    assert [sub.content for sub in chunks[1]] == ["CCCCC"]


def test_build_deepl_context_includes_neighbors(tmp_path):
    subtitles = [
        srt.Subtitle(1, timedelta(seconds=0), timedelta(seconds=1), "Intro"),
        srt.Subtitle(2, timedelta(seconds=1), timedelta(seconds=2), "Question"),
        # Gap of 3 seconds starts new scene
        srt.Subtitle(3, timedelta(seconds=5), timedelta(seconds=6), "Answer"),
        srt.Subtitle(4, timedelta(seconds=6.5), timedelta(seconds=7), "Follow up"),
    ]
    content = srt.compose(subtitles)
    path = write_sample_srt(tmp_path, content)
    srt_file = SrtFile(str(path))

    scenes = srt_file._detect_scenes()
    assert scenes == [0, 2]

    # Build context for second subtitle (index 1) inside first scene
    context = srt_file._build_deepl_context(
        scene_index=0,
        chunk_start_idx=1,
        chunk_end_idx=1,
        scene_start_idx=0,
        scene_end_idx=1,
    )

    assert context is not None
    assert "Previous dialogue" in context
    assert "1. Intro" in context
    assert "Upcoming dialogue" not in context

    # Context for first subtitle of second scene should include upcoming line
    context_scene_two = srt_file._build_deepl_context(
        scene_index=1,
        chunk_start_idx=2,
        chunk_end_idx=2,
        scene_start_idx=2,
        scene_end_idx=3,
    )

    assert context_scene_two is not None
    assert "Upcoming dialogue" in context_scene_two
    assert "4. Follow up" in context_scene_two


def build_scene_srt(tmp_path):
    subtitles = [
        srt.Subtitle(1, timedelta(seconds=0), timedelta(seconds=1), "Intro"),
        srt.Subtitle(2, timedelta(seconds=1), timedelta(seconds=2), "Question"),
        srt.Subtitle(3, timedelta(seconds=2), timedelta(seconds=3), "Answer"),
        srt.Subtitle(4, timedelta(seconds=3), timedelta(seconds=4), "Follow up"),
    ]
    path = write_sample_srt(tmp_path, srt.compose(subtitles))
    return SrtFile(str(path))


def test_context_includes_current_chunk(tmp_path):
    srt_file = build_scene_srt(tmp_path)

    context = srt_file._build_deepl_context(
        scene_index=0,
        chunk_start_idx=1,
        chunk_end_idx=2,
        scene_start_idx=0,
        scene_end_idx=3,
        chunk_lines=["Question", "Answer"],
    )

    assert "Current dialogue" in context
    assert "2. Question" in context
    assert "3. Answer" in context
    # Surrounding lines are still there
    assert "1. Intro" in context
    assert "4. Follow up" in context


def test_context_at_scene_start_is_not_none(tmp_path):
    srt_file = build_scene_srt(tmp_path)

    context = srt_file._build_deepl_context(
        scene_index=0,
        chunk_start_idx=0,
        chunk_end_idx=0,
        scene_start_idx=0,
        scene_end_idx=0,
        chunk_lines=["Intro"],
    )

    assert context is not None
    assert "1. Intro" in context


def test_context_strips_dialog_placeholder(tmp_path):
    subtitles = [
        srt.Subtitle(1, timedelta(seconds=0), timedelta(seconds=1), "-Yes\n-No"),
        srt.Subtitle(2, timedelta(seconds=1), timedelta(seconds=2), "Later"),
    ]
    path = write_sample_srt(tmp_path, srt.compose(subtitles))
    srt_file = SrtFile(str(path))

    context = srt_file._build_deepl_context(
        scene_index=0,
        chunk_start_idx=1,
        chunk_end_idx=1,
        scene_start_idx=0,
        scene_end_idx=1,
        chunk_lines=["Later"],
    )

    assert "////" not in context
    assert "1. -Yes -No" in context


def test_context_skips_already_translated_lines_on_resume(tmp_path):
    srt_file = build_scene_srt(tmp_path)
    # Simulate a resumed run: the first two lines hold translated text
    srt_file.start_from = 2

    context = srt_file._build_deepl_context(
        scene_index=0,
        chunk_start_idx=2,
        chunk_end_idx=2,
        scene_start_idx=0,
        scene_end_idx=3,
        chunk_lines=["Answer"],
    )

    assert "Previous dialogue" not in context
    assert "Intro" not in context
    assert "Question" not in context
    assert "3. Answer" in context


def test_context_for_chunk_shrinks_to_fit_request_body(tmp_path):
    long_line = "A" * 5000
    subtitles = [
        srt.Subtitle(i + 1, timedelta(seconds=i), timedelta(seconds=i + 0.5), long_line)
        for i in range(40)
    ]
    path = write_sample_srt(tmp_path, srt.compose(subtitles))
    srt_file = SrtFile(str(path))

    chunk_lines = [long_line]
    context = srt_file._context_for_chunk(0, 30, 30, 0, 39, chunk_lines)

    body = len(context.encode("utf-8")) + len(long_line.encode("utf-8"))
    assert body <= 120_000


def test_clean_context_line_strips_ass_line_breaks():
    from srtranslator.util import clean_context_line

    assert clean_context_line("Hello\\Nworld") == "Hello world"
    # Mangled backslash run produced by the ASS cleaner
    assert clean_context_line("read \\\\ \\to sail.") == "read to sail."
    assert clean_context_line("-Yes////-No") == "-Yes -No"
