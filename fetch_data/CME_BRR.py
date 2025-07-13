from datetime import datetime as dt
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import os
import pandas as pd
import shutil

import json
from utils.config import datetimeToTimestamp, timestampToDatetime

DIR = "./data_raw"
LATEST_FILE = "CME_BRR_latest.xlsx"
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
OUTPUT_FILE = "CME_BRR_" + loadDate + ".xlsx"

url_dict = {
    "BRR": "https://www.cfbenchmarks.com/data/indices/BRR",
    "BRRNY": "https://www.cfbenchmarks.com/data/indices/BRRNY",
    "BRRAP": "https://www.cfbenchmarks.com/data/indices/BRRAP"
    }

options = webdriver.ChromeOptions()
options.add_experimental_option("detach", False)
driver = webdriver.Chrome(options=options)

result_dfs = [] if df_latest is None else [df_latest]

new_dfs = []
# get date list
for indexName, url in url_dict.items():
    driver.get(url)
    ret = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "__NEXT_DATA__")))
    innerJsonString = ret.get_attribute("innerHTML")
    innerJson = json.loads(innerJsonString)
    price_dict_list = innerJson['props']['pageProps']['indexConfig']['rrs']
    price_df = pd.DataFrame(price_dict_list)
    price_df = price_df.rename(columns={"time": "Date", "value": indexName})
    price_df = price_df[["Date", indexName]].copy()
    price_df['Date'] = price_df['Date'].map(lambda x: timestampToDatetime(x).isoformat())

    # if price_dfs has element, remove time
    if len(new_dfs) == 0:
       new_dfs.append(price_df)
    else:
       new_dfs.append(price_df[[indexName]])

    print(f"finished {indexName}")

new_df = pd.concat(new_dfs, axis=1)
new_df['Date'] = pd.to_datetime(new_df.Date)
new_df['Date'] = new_df['Date'].map(lambda x: dt.strftime(x, "%Y-%m-%d")) # correct date format
new_df = new_df[~new_df.Date.isin(existing_dates)] # remove dates which already exists in previous latest data

if len(new_df) > 0:
    result_dfs.append(new_df)
    result_df = pd.concat(result_dfs)

    os.makedirs(DIR, exist_ok=True)
    result_df.to_excel(DIR + "/" + OUTPUT_FILE, index=False)

    shutil.copy(DIR + "/" + OUTPUT_FILE, latest_full_path)

    print("Finished all and exported to a file")
else:
    print("Skipped file export because no new data on website.")

