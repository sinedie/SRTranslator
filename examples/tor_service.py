import os
import glob

from selenium import webdriver
from srtranslator import SrtFile, srt_files_in_folder
from srtranslator.translators.deepl_scrap import DeeplTranslator

profile = webdriver.FirefoxProfile()
profile.set_preference("network.proxy.type", 1)
profile.set_preference("network.proxy.socks", "127.0.0.1")
profile.set_preference("network.proxy.socks_port", 9050)
profile.set_preference("network.proxy.socks_version", 5)
profile.update_preferences()

driver = webdriver.Firefox(firefox_profile=profile)
translator = DeeplTranslator(driver=driver)

folder = "srt_test/"
for filepath in glob.glob(os.path.join(folder, "**/*.srt"), recursive=True):
    srt = SrtFile(filepath)
    srt.translate(translator, "en", "es")
    srt.wrap_lines(50)
    srt.save(f"{os.path.splitext(filepath)[0]}_translated.srt")

translator.quit()
