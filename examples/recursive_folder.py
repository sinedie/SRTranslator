import os
import glob

from srtranslator import SrtFile
from srtranslator.translators.deepl_scrap import DeeplTranslator

folder = "srt_test/"
for filepath in glob.glob(os.path.join(folder, "**/*.srt"), recursive=True):
    # Creates a new translator each time in case you dont provide a driver, this way,
    # DeeplTranslator creates a proxy and avoid getting banned
    translator = DeeplTranslator()

    srt = SrtFile(filepath)
    srt.translate(translator, "en", "es")
    srt.wrap_lines()
    srt.save(f"{os.path.splitext(filepath)[0]}_translated.srt")

    translator.quit()
