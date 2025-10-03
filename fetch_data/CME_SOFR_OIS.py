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
from io import StringIO

from utils.config import makeSeleniumOption

# Plan
# 1. Load latest data if existss. Get dates
# 2. From website, only fetch dates which are not covered in latest file #1
# 3. Export #1 and #2 to OUTPUT file with file name the latest timestamp
# 4. Copy #4 to overwrite the latest file

DIR = "./data_raw"
LATEST_FILE = "SOFR_OIS_latest.xlsx"
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
OUTPUT_FILE = "SOFR_OIS_" + loadDate + ".xlsx"

url = "https://www.cmegroup.com/trading/interest-rates/cleared-otc-sofr-swaps.html"

driver = webdriver.Chrome(options=makeSeleniumOption())

dates = []
tenors = []

rates = []
dfs = [] if df_latest is None else [df_latest]

# get date list
driver.get(url)
ret = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".date-value")))
options = ret.find_elements(By.TAG_NAME, "option")
dates_YYYYMMDD = [opt.get_attribute("value") for opt in options]
DateChoicesLabelRaw = [opt.text.strip() for opt in options]
DateChoicesRaw = [dt.strptime(date_YYYYMMDD, "%Y%m%d") for date_YYYYMMDD in dates_YYYYMMDD]
DateChoicesLabelSorted = [dcl for _, dcl in sorted(zip(DateChoicesRaw, DateChoicesLabelRaw))] # sort by ascending order
DateChoicesSorted = sorted(DateChoicesRaw) # sort by ascending order

# extract only new dates (not included in file)
DateChoices = [dc for dc in DateChoicesSorted if dc not in existing_dates]
DateChoicesLabel = [dcl for dc, dcl in zip(DateChoicesSorted, DateChoicesLabelSorted) if dc not in existing_dates]

if len(DateChoices) > 0:
    # for d in range(DAYS_BACK + 1):
    for i_date, evalDate in enumerate(DateChoices):
        select_elem = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "select.date-value")))
        # select
        target_value = dt.strftime(evalDate, "%Y%m%d")
        driver.execute_script(f"""
          const sel = document.querySelector('select.date-value');
          sel.value = '{target_value}';
          sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
        """)

        time.sleep(2)  # Let the table refresh

        # Step 3: Confirm the table loaded
        table = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".sofr-table")))
        html = table.get_attribute("outerHTML")
        df = pd.read_html(StringIO(html))[0]

        df.rename(columns={"TENOR": "Tenor", "OUTRIGHT SOFR RATE (%)": "Rate"}, inplace=True)
        df.drop("EFFR OIS - SOFR OIS Basis (bp)", axis=1, inplace=True)

        df['Tenor'] = df['Tenor'].map(lambda x: x.replace(' Year', 'Y'))
        df['Rate'] = df['Rate'].map(lambda x: x / 100.)
        evalDateStr = dt.strftime(evalDate, "%Y-%m-%d")
        df.insert(loc=0, column="Date", value=evalDateStr)
        dfs.append(df)

        time.sleep(2.0) # to avoid being blocked by server
        print("Finished for " + str(evalDate)) 

    result_df = pd.concat(dfs)
    os.makedirs(DIR, exist_ok=True)
    result_df.to_excel(DIR + "/" + OUTPUT_FILE, index=False)

    shutil.copy(DIR + "/" + OUTPUT_FILE, latest_full_path)

    print("Finished all")

else:
    print("Skipped due to no update on website.")
