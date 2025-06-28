from datetime import datetime as dt
from selenium import webdriver
# from seleniumwire import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from tqdm import tqdm
import time
import os
import shutil
import pandas as pd

# Plan
# 1. Load latest data if existss. Get dates
# 2. From website, only fetch dates which are not covered in latest file #1
# 3. Export #1 and #2 to OUTPUT file with file name the latest timestamp
# 4. Copy #4 to overwrite the latest file

DIR = "./data"
LATEST_FILE = "CME_BTC_Future_latest.xlsx"
latest_full_path = DIR + "/" + LATEST_FILE
existing_dates = []
df_latest = None
if os.path.exists(latest_full_path):
    df_latest = pd.read_excel(latest_full_path)
    existing_dates_str = df_latest["Date"]
    existing_dates = pd.to_datetime(existing_dates_str, format="%Y-%m-%dT%H:%M:%S").unique()

loadDate = dt.now().isoformat().replace(":", "")
loadDate=loadDate[:17] # YYYY-MM-DDTHHMMSS
OUTPUT_FILE = "CME_BTC_Future_" + loadDate + ".xlsx"

keepOpen = True

url_base = "https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin.settlements.html"

options = webdriver.ChromeOptions()
options.add_experimental_option("detach", False)
# options.add_argument("headless")
# options.add_argument("disable-gui")

driver = webdriver.Chrome(options=options)

dates = []
expiries = []

opens = []
highs = []
lows = []
lasts = []
changes = []
settles = []
estimated_volumes = []
prior_day_ois = [] # open interest
dfs = [] if df_latest is None else [df_latest]

# get date list
driver.get(url_base)
ret = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".trade-date-row.row")))
labelDate = driver.find_element(By.XPATH, "//label[contains(@class, 'form-label') and normalize-space(text())='Trade date']")
DateItems = labelDate.find_element(By.XPATH, "..").find_elements(By.CSS_SELECTOR, ".dropdown-item.dropdown-item")
DateChoices = [dt.strptime(item.get_attribute("data-value").strip(), "%m/%d/%Y") for item in DateItems]
DateChoices.sort() # sort by ascending order

# extract only new dates (not included in file)
DateChoices = [dc for dc in DateChoices if dc not in existing_dates]

if len(DateChoices) > 0:
    # for d in range(DAYS_BACK + 1):
    for i_date, evalDate in enumerate(DateChoices):
        dd = f'{evalDate.day:02d}'
        mm = f'{evalDate.month:02d}'
        yyyy = f'{evalDate.year:04d}'
        url_date = url_base + f'#tradeDate={dd}%2F{mm}%2F{yyyy}'
        driver.get(url_date)
        if i_date != 0:
            driver.refresh()


        ret = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "main-table-wrapper")))

        trs = driver.execute_script(
            """
            const rows = document.querySelectorAll(".main-table-wrapper table tbody tr");
            return Array.from(rows).map(row =>
                Array.from(row.querySelectorAll("td")).map(td => td.innerText.trim())
            );
            """)
        for tds in trs:
            dates.append(evalDate.isoformat())
            expiries.append(tds[0])
            opens.append(tds[1])
            highs.append(tds[2])
            lows.append(tds[3])
            lasts.append(tds[4])
            changes.append(tds[5])
            settles.append(tds[6])
            estimated_volumes.append(tds[7])
            prior_day_ois.append(tds[8])

        time.sleep(2.0) # to avoid being blocked by server
        print("Finished for " + str(evalDate)) 

    # export to file
    dic = {
        "Date": dates,
        "Expiry": expiries,
        "OpenPrice": opens,
        "HighPrice": highs,
        "LowPrice": lows,
        "LastPrice": lasts,
        "SettlePrice": settles,
        "SettlePriceChange": changes,
        "EstimatedVolume": estimated_volumes,
        "PriorDayOpenInterest": prior_day_ois,
        }
    dfs.append(pd.DataFrame(dic))
    df = pd.concat(dfs)
    os.makedirs(DIR, exist_ok=True)
    df.to_excel(DIR + "/" + OUTPUT_FILE, index=False)

    shutil.copy(DIR + "/" + OUTPUT_FILE, latest_full_path)

    print("Finished all")

else:
    print("Skipped due to no update on website.")
