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
