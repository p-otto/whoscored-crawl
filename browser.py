from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep

path_to_chromedriver = './chrome/chromedriver'
path_to_adblock = "./chrome/uBlock.crx"
chrome_options = Options()
chrome_options.add_extension(path_to_adblock)
chrome_options.add_argument("--disable-plugins​")
chrome_options.add_argument("--disable-bundled-ppapi-flash​")
browser = webdriver.Chrome(executable_path=path_to_chromedriver, chrome_options=chrome_options)
SLEEP_LENGTH = 5


def getPageSource(url: str):
    browser.get(url)
    sleep(SLEEP_LENGTH)
    source = browser.page_source
    return source


def close():
    browser.close()
