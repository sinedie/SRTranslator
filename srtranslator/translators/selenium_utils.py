import sys
import logging

from typing import Optional
from fp.fp import FreeProxy
from selenium import webdriver
from webdriverdownloader import GeckoDriverDownloader
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import TimeoutException


def create_proxy() -> Proxy:
    """Creates a new proxy to use with a selenium driver and avoid get banned

    Returns:
        Proxy: Selenium WebDriver proxy
    """
    logging.info("Getting a new Proxy from https://www.sslproxies.org/")
    proxy = FreeProxy().get()
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
    ) -> None:

        self.driver = driver
        locator = (getattr(By, locate_by.upper(), "id"), locate_value)
        find_element = driver.find_elements if multiple else driver.find_element
        try:
            WebDriverWait(driver, wait_time).until(
                lambda driver: find_element(*locator)
            )
            self.element = find_element(*locator)
        except TimeoutException:
            print(f"Timed out trying to get element ({locate_by} = {locate_value})")
            logging.info("Closing browser")
            driver.quit()
            sys.exit()


class Text(BaseElement):
    @property
    def text(self) -> str:
        return self.element.get_attribute("text")


class TextArea(BaseElement):
    def write(self, value: str) -> None:
        self.element.clear()
        self.element.send_keys(*value)

    @property
    def value(self) -> None:
        return self.element.get_attribute("value")


class Button(BaseElement):
    def click(self) -> None:
        try:
            can_click = getattr(self.element, "click", None)
            if callable(can_click):
                self.element.click()
        except:
            # Using javascript if usual click function does not work
            self.driver.execute_script("arguments[0].click();", self.element)
