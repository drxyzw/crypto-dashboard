from datetime import datetime as dt
from datetime import timedelta
from selenium import webdriver
# from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

loadDate = dt.now()
keepOpen = True

# url = "https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin.settlements.options.html#optionProductId=8875&tradeDate=06%2F01%2F2025"
url_base = "https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin.settlements.options.html#optionProductId=8875&tradeDate="

options = webdriver.ChromeOptions()
options.add_experimental_option("detach", False)
# options.add_argument("headless")
# options.add_argument("disable-gui")

driver = webdriver.Chrome(options=options)
# driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

DAYS_BACK = 90
for d in range(DAYS_BACK + 1):
    td = timedelta(days=d)
    loadDate -= td

    dd = f'{loadDate.day:02d}'
    mm = f'{loadDate.month:02d}'
    yyyy = f'{loadDate.year:04d}'
    url = url_base + f'{dd}%2F{mm}%2F{yyyy}'
    driver.get(url)

    ret = WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.CLASS_NAME, "main-table-wrapper")))
    textBeforeLoadAll = ret.text
    loadAllButton = WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".primary.load-all.btn.btn-")))
    # loadAllButton.click() fails due to overlay issue
    driver.execute_script("arguments[0].click();", loadAllButton)
    ret = WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.CLASS_NAME, "main-table-wrapper")))
    WebDriverWait(driver, 60).until(lambda x: ret.text != textBeforeLoadAll)

#     # WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.ID, "productTabData")))
#     print(ret.text)
# # primary load-all btn btn-
    print("Finished for " + str(loadDate))
