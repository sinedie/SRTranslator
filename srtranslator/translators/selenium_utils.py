import sys
import logging

from typing import Optional, List
from fp.fp import FreeProxy
from selenium import webdriver
from webdriverdownloader import GeckoDriverDownloader
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.support import expected_conditions as EC


def create_proxy(country_id: Optional[List[str]] = ["US"]) -> Proxy:
    """Creates a new proxy to use with a selenium driver and avoid get banned

    Args:
        country_id (Optional[List[str]], optional): Contry id to create proxy. Defaults to ['US'].

    Returns:
        Proxy: Selenium WebDriver proxy
    """
    i = 0
    while i < 3:
        try:
            logging.info("Getting a new Proxy from https://www.sslproxies.org/")
            proxy = FreeProxy(country_id=country_id).get()
            proxy = Proxy(
                dict(
                    proxyType=ProxyType.MANUAL,
                    httpProxy=proxy,
                    ftpProxy=proxy,
                    sslProxy=proxy,
                    noProxy="",
                )
            )
            return proxy
        except:
            logging.info("Exception while getting Proxy. Trying again")
            i += 1

    raise Exception("Unable to get proxy")


def create_driver(proxy: Optional[Proxy] = None) -> WebDriver:
    """Creates a new Firefox selenium webdriver. Install geckodriver if not in path

    Args:
        proxy (Optional[Proxy], optional): Selenium WebDriver proxy. Defaults to None.

    Returns:
        WebDriver: Selenium WebDriver
    """
    logging.info("Creating Selenium Webdriver instance")
    try:
        driver = webdriver.Firefox(proxy=proxy)
    except WebDriverException:
        logging.info("Installing Firefox GeckoDriver cause it isn't installed")
        gdd = GeckoDriverDownloader()
        gdd.download_and_install()

        driver = webdriver.Firefox(proxy=proxy)

    driver.maximize_window()
    return driver


class BaseElement:
    def __init__(
        self,
        driver: webdriver,
        locate_by: str,
        locate_value: str,
        multiple: bool = False,
        wait_time: int = 100,
        optional: bool = False,
    ) -> None:

        self.driver = driver
        locator = (getattr(By, locate_by.upper(), "id"), locate_value)
        find_element = driver.find_elements if multiple else driver.find_element
        try:
            WebDriverWait(driver, wait_time).until(
                lambda driver: EC.element_to_be_clickable(locator)
            )
            self.element = find_element(*locator)
        except:
            if optional:
                self.element = None
                return

            print(f"Timed out trying to get element ({locate_by} = {locate_value})")
            logging.info("Closing browser")
            driver.quit()
            sys.exit()


class Text(BaseElement):
    @property
    def text(self) -> str:
        if self.element is None:
            return ""

        return self.element.get_attribute("text")


class TextArea(BaseElement):
    def write(self, value: str) -> None:
        if self.element is None:
            return

        # Check OS to use Cmd or Ctrl keys
        cmd_ctrl = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL

        actions_handler = ActionChains(self.driver).move_to_element(self.element)
        actions_handler.click().key_down(cmd_ctrl).send_keys("a").perform()
        actions_handler.send_keys(Keys.CLEAR).key_up(cmd_ctrl).perform()
        actions_handler.send_keys(*value).perform()

    @property
    def value(self) -> None:
        if self.element is None:
            return ""

        return self.element.get_attribute("value")


class Button(BaseElement):
    def click(self) -> None:
        if self.element is None:
            return

        try:
            can_click = getattr(self.element, "click", None)
            if callable(can_click):
                self.element.click()
        except:
            # Using javascript if usual click function does not work
            self.driver.execute_script("arguments[0].click();", self.element)
