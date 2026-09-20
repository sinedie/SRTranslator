import re
import sys


def show_progress(total: int, progress: int):
    """Displays or updates a console progress bar"""

    barLength, status = 20, ""
    progress = float(progress) / float(total)
    if progress >= 1.0:
        progress, status = 1, "\r\n"
    block = int(round(barLength * progress))
    text = "\r[{}] {:.0f}% {}".format(
        "#" * block + "-" * (barLength - block), round(progress * 100, 0), status
    )
    sys.stdout.write(text)
    sys.stdout.flush()


# DeepL rejects a request body over 128 KiB. Stay clear of the edge, because a
# chunk is measured in characters while the body is measured in bytes.
MAX_REQUEST_BODY_BYTES = 120_000

# Context budgets (before, after, summary) tried in order until the body fits.
CONTEXT_BUDGETS = (
    (4000, 2000, 2000),
    (2000, 1000, 0),
    (1000, 0, 0),
    (0, 0, 0),
)


def clean_context_line(text: str) -> str:
    """Strip subtitle placeholders so context reads as plain dialogue.

    The subtitle classes encode dialog markers as ``////`` and ASS line breaks
    as runs of backslashes. Those are meaningless to a translation engine, so
    they are replaced by spaces before a line is used as context. Only the
    context copy is cleaned; the text actually sent for translation keeps its
    placeholders.
    """
    text = text.replace("////", " ")
    # ASS line breaks survive as \N, or as mangled runs of backslashes
    text = re.sub(r"\\+N", " ", text)
    text = re.sub(r"\\+", " ", text)
    return " ".join(text.split())
