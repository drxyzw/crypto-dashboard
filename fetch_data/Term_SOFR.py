from datetime import datetime as dt
from selenium import webdriver
# from seleniumwire import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import os
import shutil
import pandas as pd
from bs4 import BeautifulSoup 
from io import StringIO

def convertRate(x):
    x = x.strip()
    try:
        if '%' in x:
            value = x[:-1]
            value = float(value) * 0.01
        else:
            value = float(x)
    except Exception as e:
        value = None
    return value

# Plan
# 1. Load latest data if existss. Get dates
# 2. From website, only fetch dates which are not covered in latest file #1
# 3. Export #1 and #2 to OUTPUT file with file name the latest timestamp
# 4. Copy #4 to overwrite the latest file

DIR = "./raw_data"
LATEST_FILE = "Term_SOFR_latest.xlsx"
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
OUTPUT_FILE = "Term_SOFR_" + loadDate + ".xlsx"

keepOpen = True

url_base = "https://www.global-rates.com/en/interest-rates/cme-term-sofr/"

options = webdriver.ChromeOptions()
options.add_experimental_option("detach", False)
# options.add_argument("headless")
# options.add_argument("disable-gui")

driver = webdriver.Chrome(options=options)

dfs = [] if df_latest is None else [df_latest]

# get date list
driver.get(url_base)
ret = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH, "//caption[normalize-space(text())='Latest CME Term SOFR rates']")))
table = ret.find_element(By.XPATH, "..")
tableHTML = table.get_attribute("outerHTML")
soup = BeautifulSoup(tableHTML, "html.parser")
df = pd.read_html(StringIO(str(soup)))[0]
df = df.transpose()

# column in html is assigned to the first row of DataFrame, so adjust it
df.columns = df.iloc[0]
df = df[1:]
df = df.map(convertRate) # convert rate format ('4.32887 %')

df.index = df.index.map(lambda x: dt.strptime(x, "%m-%d-%Y")) # correct date format
df.index = df.index.map(lambda x: dt.strftime(x, "%Y-%m-%d")) # correct date format
df.index.name = "Date"
df = df.sort_index() # date by ascending 
df = df.reset_index() # move the date index to column 

df = df[~df.Date.isin(existing_dates)] # remove dates which already exists in previous latest data

if len(df) > 0:
    dfs.append(df)
    result_df = pd.concat(dfs)
    result_df.to_excel(DIR + "/" + OUTPUT_FILE, index=False)

    shutil.copy(DIR + "/" + OUTPUT_FILE, latest_full_path)

    print("Finished all")

else:
    print("Skipped due to no update on website.")
