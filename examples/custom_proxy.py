import os
import glob

from srtranslator import SrtFile
from srtranslator.translators.deepl_scrap import DeeplTranslator
from srtranslator.translators.selenium_utils import create_proxy, create_driver

folder = "srt_test/"
for filepath in glob.glob(os.path.join(folder, "**/*.srt"), recursive=True):
    # The country ids are the ones in https://www.sslproxies.org/
    proxy = create_proxy(country_id=["US", "GB"])
    driver = create_driver(proxy)
    translator = DeeplTranslator(driver)

    srt = SrtFile(filepath)
    srt.translate(translator, "en", "es")
    srt.wrap_lines()
    srt.save(f"{os.path.splitext(filepath)[0]}_translated.srt")

    translator.quit()
