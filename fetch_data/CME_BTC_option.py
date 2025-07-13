from datetime import datetime as dt
from selenium import webdriver
# from seleniumwire import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import os
import shutil
import pandas as pd

# Plan
# 1. Load latest data if existss. Get dates
# 2. From website, only fetch dates which are not covered in latest file #1
# 3. Export #1 and #2 to OUTPUT file with file name the latest timestamp
# 4. Copy #4 to overwrite the latest file

DIR = "./data_raw"
LATEST_FILE = "CME_BTC_Option_latest.xlsx"
latest_full_path = DIR + "/" + LATEST_FILE
existing_dates = []
df_latest = None
if os.path.exists(latest_full_path):
    df_latest = pd.read_excel(latest_full_path)
    existing_dates_str = df_latest["Date"]
    existing_dates = pd.to_datetime(existing_dates_str, format="%Y-%m-%d").unique()
    # existing_dates = pd.to_datetime(existing_dates_str, format="%Y-%m-%dT%H:%M:%S").unique()

loadDate = dt.now().isoformat().replace(":", "")
loadDate=loadDate[:17] # YYYY-MM-DDTHHMMSS
OUTPUT_FILE = "CME_BTC_Option_" + loadDate + ".xlsx"

url_base = "https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin.settlements.options.html"

options = webdriver.ChromeOptions()
options.add_experimental_option("detach", False)
# options.add_argument("headless")
# options.add_argument("disable-gui")

driver = webdriver.Chrome(options=options)

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
counts = []
count = 0
dfs = [] if df_latest is None else [df_latest]

# In options, dates are given per expiry (no date is shown after expiry)
# So, first select by expiry. Then, select date.
# get date list
driver.get(url_base)

# first load to get option type choices
ret = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "main-table-wrapper")))
labelType = driver.find_element(By.XPATH, "//span[contains(@class, 'button-text') and normalize-space(text())='Options']")
typeItems = labelType.find_element(By.XPATH, "../..").find_elements(By.CSS_SELECTOR, ".dropdown-item.dropdown-item")
typeChoices = [item.get_attribute("textContent").strip() for item in typeItems]
typeChoiceIDs = [item.get_attribute("data-value").strip() for item in typeItems]

for i_type, typeChoiceID in enumerate(typeChoiceIDs):
    url_type = url_base + f'#strikeRange=ALL&optionProductId={typeChoiceID}'
    driver.get(url_type)
    if i_type != 0:
        driver.refresh()
    # second load to get expiry choices
    ret = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "main-table-wrapper")))
    labelExpiry = driver.find_element(By.XPATH, "//label[contains(@class, 'form-label') and normalize-space(text())='Expiration']")
    expiryItems = labelExpiry.find_element(By.XPATH, "..").find_elements(By.CSS_SELECTOR, ".dropdown-item.dropdown-item")
    expiryChoices = [item.get_attribute("textContent").strip() for item in expiryItems]
    expiryChoiceIDs = [item.get_attribute("data-value").strip() for item in expiryItems]
    for i_exp, expiryChoiceID in enumerate(expiryChoiceIDs):
        url_type_expiry = url_type + f'&optionExpiration={expiryChoiceID}'
        driver.get(url_type_expiry)
        driver.refresh()

        ret = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".trade-date-row.row")))
        labelDate = driver.find_element(By.XPATH, "//label[contains(@class, 'form-label') and normalize-space(text())='Trade date']")
        DateItems = labelDate.find_element(By.XPATH, "..").find_elements(By.CSS_SELECTOR, ".dropdown-item.dropdown-item")
        DateChoices = [dt.strptime(item.get_attribute("data-value").strip(), "%m/%d/%Y") for item in DateItems]
        DateChoices.sort() # sort by ascending order

        # extract only new dates (not included in file)
        DateChoices = [dc for dc in DateChoices if dc not in existing_dates]

        if len(DateChoices) > 0:
            for i_date, evalDate in enumerate(DateChoices):
                dd = f'{evalDate.day:02d}'
                mm = f'{evalDate.month:02d}'
                yyyy = f'{evalDate.year:04d}'
                url_type_expiry_date = url_type_expiry + f'&tradeDate={dd}%2F{mm}%2F{yyyy}'
                driver.get(url_type_expiry_date)
                driver.refresh()
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
                trs = driver.execute_script(
                    """
                    const rows = document.querySelectorAll(".main-table-wrapper table tbody tr");
                    return Array.from(rows).map(row =>
                        Array.from(row.querySelectorAll("td")).map(td => td.innerText.trim())
                    );
                    """)
                for tds in trs:
                    dates.append(dt.strftime(evalDate, "%Y-%m-%d"))
                    optionTypes.append(typeChoices[i_type])
                    expiries.append(expiryChoices[i_exp])

                    calls_estimated_volume.append(tds[0])
                    calls_prior_day_oi.append(tds[1])
                    call_high, call_low = tds[2].split('\n')
                    calls_high.append(call_high)
                    calls_low.append(call_low)
                    call_open, call_last = tds[3].split('\n')
                    calls_open.append(call_open)
                    calls_last.append(call_last)
                    calls_settle.append(tds[4])
                    calls_change.append(tds[5])
                    strikes.append(tds[6])
                    puts_change.append(tds[7])
                    puts_settle.append(tds[8])
                    put_open, put_last = tds[9].split('\n')
                    puts_open.append(put_open)
                    puts_last.append(put_last)
                    put_high, put_low = tds[10].split('\n')
                    puts_high.append(put_high)
                    puts_low.append(put_low)
                    puts_prior_day_oi.append(tds[11])
                    puts_estimated_volume.append(tds[12])
                    counts.append(count)
                    count += 1

                    # dfs.append(pd.DataFrame(dic))
                print("Finished for " + typeChoices[i_type] + ", " + expiryChoices[i_exp] + ", expiry date:" + str(evalDate))
                time.sleep(2.0) # to avoid being blocked by server
        else:
            print("Skipped due to no update on website for " + typeChoices[i_type] + ", " + expiryChoices[i_exp])

if len(counts) > 0:
    # export to file
    dic = {
        "Count": counts,
        "Date": dates,
        "OptionType": optionTypes,
        "Expiry": expiries,
        "Strike": strikes,
        "OpenCallPrice": calls_open,
        "HighCallPrice": calls_high,
        "LowCallPrice": calls_low,
        "LastCallPrice": calls_last,
        "SettleCallPrice": calls_settle,
        "SettleCallPriceChange": calls_change,
        "CallPriorDayOpenInterest": calls_prior_day_oi,
        "CallEstimatedVolume": calls_estimated_volume,
        "OpenPutPrice": puts_open,
        "HighPutPrice": puts_high,
        "LowPutPrice": puts_low,
        "LastPutPrice": puts_last,
        "SettlePutPrice": puts_settle,
        "SettlePutPriceChange": puts_change,
        "PutPriorDayOpenInterest": puts_prior_day_oi,
        "PutEstimatedVolume": puts_estimated_volume,
        }
    df_new = pd.DataFrame(dic)
    df_new = df_new.sort_values(by=['Date', 'Count'], ascending=[True, True])
    df_new_removed_count = df_new.drop(columns='Count')
    dfs.append(df_new_removed_count)
    df = pd.concat(dfs)
    os.makedirs(DIR, exist_ok=True)
    df.to_excel(DIR + "/" + OUTPUT_FILE, index=False)

    shutil.copy(DIR + "/" + OUTPUT_FILE, latest_full_path)

    print("Finished all")

else:
    print("Skipped due to no update on website.")
