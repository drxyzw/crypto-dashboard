from datetime import datetime as dt
from datetime import timedelta
from selenium import webdriver
# from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from tqdm import tqdm

loadDate = dt.now()
keepOpen = True

# url = "https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin.settlements.options.html#optionProductId=8875&tradeDate=06%2F01%2F2025"
url_base = "https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin.settlements.options.html"

options = webdriver.ChromeOptions()
options.add_experimental_option("detach", False)
# options.add_argument("headless")
# options.add_argument("disable-gui")

driver = webdriver.Chrome(options=options)
# driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

DAYS_BACK = 90
dates = []
optionTypes = []
expiries = []

calls_estimated_volume = []
calls_prior_day_oi = [] # open interest
calls_high = []
calls_low = []
calls_open = []
calls_last = []
calls_settle = []
calls_change = []
strikes = []
puts_change = []
puts_settle = []
puts_last = []
puts_open = []
puts_low = []
puts_high = []
puts_prior_day_oi = [] # open interest
puts_estimated_volume = []

for d in range(DAYS_BACK + 1):
    td = timedelta(days=d)
    loadDate -= td

    dd = f'{loadDate.day:02d}'
    mm = f'{loadDate.month:02d}'
    yyyy = f'{loadDate.year:04d}'
    url_date = url_base + f'#tradeDate={dd}%2F{mm}%2F{yyyy}'
    driver.get(url_date)

    # first load to get option type choices
    ret = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "main-table-wrapper")))
    labelType = driver.find_element(By.XPATH, "//span[contains(@class, 'button-text') and normalize-space(text())='Options']")
    typeItems = labelType.find_element(By.XPATH, "../..").find_elements(By.CSS_SELECTOR, ".dropdown-item.dropdown-item")
    typeChoices = [item.get_attribute("textContent").strip() for item in typeItems]
    typeChoiceIDs = [item.get_attribute("data-value").strip() for item in typeItems]

    for i_type, typeChoiceID in enumerate(typeChoiceIDs):
        url_date_type = url_date + f'&optionProductId={typeChoiceID}'
        driver.get(url_date_type)
#
        # second load to get expiry choices
        ret = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "main-table-wrapper")))
        labelExpiry = driver.find_element(By.XPATH, "//label[contains(@class, 'form-label') and normalize-space(text())='Expiration']")
        expiryItems = labelExpiry.find_element(By.XPATH, "..").find_elements(By.CSS_SELECTOR, ".dropdown-item.dropdown-item")
        expiryChoices = [item.get_attribute("textContent").strip() for item in expiryItems]
        expiryChoiceIDs = [item.get_attribute("data-value").strip() for item in expiryItems]

        for i_exp, expiryChoiceID in enumerate(expiryChoiceIDs):
            url_date_type_expiry = url_date_type + f'&optionExpiration={expiryChoiceID}'
            driver.get(url_date_type_expiry)
            # if i_exp != 0:
            #     labelExpiry = driver.find_element(By.XPATH, "//label[contains(@class, 'form-label') and normalize-space(text())='Expiration']")
            #     expiryItems = labelExpiry.find_element(By.XPATH, "..").find_elements(By.CSS_SELECTOR, ".dropdown-item.dropdown-item")
            #     expiryChoices = [item.get_attribute("textContent").strip() for item in expiryItems]
            # driver.execute_script("arguments[0].click();", expiryItems[i_exp])

            ret = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "main-table-wrapper")))
            n_tr_table_before_load_all = len(ret.find_elements(By.TAG_NAME, "tr"))
            # textBeforeLoadAll = ret.text
            # textBeforeLoadAll = ret.text
            loadAllButtons = driver.find_elements(By.CSS_SELECTOR, ".primary.load-all.btn.btn-")
            if loadAllButtons:
                loadAllButton = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".primary.load-all.btn.btn-")))
                # loadAllButton.click() fails due to overlay issue
                driver.execute_script("arguments[0].click();", loadAllButton)
                # ret = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "main-table-wrapper")))
                # WebDriverWait(driver, 20).until(lambda x: ret.text != textBeforeLoadAll)
                def isNumTrTableChange(dr):
                    r = dr.find_elements(By.CLASS_NAME, "main-table-wrapper")
                    if len(r) > 0:
                        n_tr_table_after_load_all = len(r[0].find_elements(By.TAG_NAME, "tr"))
                        return n_tr_table_after_load_all > n_tr_table_before_load_all
                    else:
                        return False
                # WebDriverWait(driver, 20).until(lambda dr: len(dr.find_element(By.CLASS_NAME, "main-table-wrapper").text) > len(textBeforeLoadAll))
                WebDriverWait(driver, 20).until(isNumTrTableChange)
            ret = driver.find_element(By.CLASS_NAME, "main-table-wrapper")
            
            table = ret.find_element(By.TAG_NAME, "table")
            tbody = table.find_element(By.TAG_NAME, "tbody")
            trs = tbody.find_elements(By.TAG_NAME, "tr")
            for tr in tqdm(trs):
                tds = tr.find_elements(By.TAG_NAME, "td")

                dates.append(loadDate.isoformat())
                optionTypes.append(typeChoices[i_type])
                expiries.append(expiryChoices[i_exp])

                calls_estimated_volume.append(tds[0].text)
                calls_prior_day_oi.append(tds[1].text)
                call_high, call_low = tds[2].text.split('\n')
                calls_high.append(call_high)
                calls_low.append(call_low)
                call_open, call_last = tds[3].text.split('\n')
                calls_open.append(call_open)
                calls_last.append(call_last)
                calls_settle.append(tds[4].text)
                calls_change.append(tds[5].text)
                strikes.append(tds[6].text)
                puts_change.append(tds[7].text)
                puts_settle.append(tds[8].text)
                put_open, put_last = tds[9].text.split('\n')
                puts_open.append(put_open)
                puts_last.append(put_last)
                put_high, put_low = tds[10].text.split('\n')
                puts_high.append(put_high)
                puts_low.append(put_low)
                puts_prior_day_oi.append(tds[11].text)
                puts_estimated_volume.append(tds[12].text)
            print("Finished for " + typeChoices[i_type] + ", " + expiryChoices[i_exp])
    print("Finished for " + str(loadDate))

print("Finished all")
