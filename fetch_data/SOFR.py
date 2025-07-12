from datetime import datetime as dt
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import os
import pandas as pd
import shutil
from io import StringIO

import json
from fetch_data.utils import datetimeToTimestamp, timestampToDatetime

DIR = "./data"
LATEST_FILE = "SOFR_latest.xlsx"
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
year = int(loadDate[:4])
OUTPUT_FILE = "SOFR_" + loadDate + ".xlsx"

url = "https://www.newyorkfed.org/markets/reference-rates/sofr"

options = webdriver.ChromeOptions()
options.add_experimental_option("detach", False)
driver = webdriver.Chrome(options=options)

result_dfs = [] if df_latest is None else [df_latest]

# fetch table from FED website
driver.get(url)
table_element = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".p-datatable-wrapper")))
html = table_element.get_attribute("outerHTML")
df = pd.read_html(StringIO(html))[0]
df.rename(columns={'DATE': 'Date'}, inplace=True)

# determine latest year
latest_mm_dd_str = df.iloc[0]['Date']
latest_date_str_test = str(year) + "/" + latest_mm_dd_str
while dt.strptime(latest_date_str_test, "%Y/%m/%d") > dt.now():
    year -= 1
    latest_date_str_test = str(year) + "/" + latest_mm_dd_str
date_strs = df["Date"]
dates = [dt.strptime(latest_date_str_test, "%Y/%m/%d")]
for i in range(1, len(date_strs)):
    date_str_test = str(year) + "/" + date_strs[i]
    while dt.strptime(date_str_test, "%Y/%m/%d") > dates[-1]:
        year -= 1
        date_str_test = str(year) + "/" + date_strs[i]
    date_determined = dt.strptime(date_str_test, "%Y/%m/%d")
    dates.append(date_determined)
df['Date'] = dates
df.sort_values("Date", ascending=True, inplace=True)
mask_to_include = [not (d in existing_dates) for d in df['Date']]
df = df[mask_to_include]

if len(df) > 0:
    result_dfs.append(df)
    result_df = pd.concat(result_dfs)
    result_df.sort_values("Date", ascending=True, inplace=True)
    result_df['Date'] = result_df['Date'].map(lambda x: dt.strftime(x, "%Y-%m-%d"))

    os.makedirs(DIR, exist_ok=True)
    result_df.to_excel(DIR + "/" + OUTPUT_FILE, index=False)

    shutil.copy(DIR + "/" + OUTPUT_FILE, latest_full_path)

    print("Finished all and exported to a file")
else:
    print("Skipped file export because no new data on website.")

