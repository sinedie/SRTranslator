import os
import glob

from srtranslator import SrtFile
from srtranslator.translators.translatepy import TranslatePy


folder = "srt_test/"
translator = TranslatePy()

for filepath in glob.glob(os.path.join(folder, "**/*.srt"), recursive=True):
    srt = SrtFile(filepath)
    srt.translate(translator, "en", "es")
    srt.wrap_lines()
    srt.save(f"{os.path.splitext(filepath)[0]}_translated.srt")

translator.quit()
