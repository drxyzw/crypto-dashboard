from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import os
import pandas as pd
import time
import shutil

import requests
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta

from utils.config import *

def scroll_to_load_all(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollBy(0, window.innerHeight);")
        # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3.0)  # wait for data to load
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

DIR = "./data_raw"
LATEST_FILE = "SOFR_futures_latest.xlsx"
latest_full_path = DIR + "/" + LATEST_FILE
existing_dates = []
df_latest = None
if os.path.exists(latest_full_path):
    df_latest = pd.read_excel(latest_full_path)
    existing_dates_str = df_latest["Date"]
    existing_dates = pd.to_datetime(existing_dates_str, format="%Y-%m-%dT%H:%M:%S").unique()

loadDate = dt.now()
loadDateStr = loadDate.isoformat().replace(":", "")
loadDateStr = loadDateStr[:17] # YYYY-MM-DDTHHMMSS
OUTPUT_FILE = "SOFR_futures_" + loadDateStr + ".xlsx"

driver = webdriver.Chrome(options=selenium_options)

dfs = [] if df_latest is None else [df_latest]
count = 0
counts = []
closes = []
volumes = []
openIntersts = []

startDate = dt(2025, 6, 1)
fetchDataMonths = 3 # free data is up to 3 months in Barchart
bufferWeeks = 2
earliestDateNeeded = loadDate - relativedelta(months=fetchDataMonths) + relativedelta(weeks=bufferWeeks)

# loop over future tenors
for instrument_flag in sofr_instrument_flags:
    expiryLimitDate = startDate + relativedelta(years=sofr_expiry_year_limits[instrument_flag])
    month_count = 0
    expiryDate = startDate
    # loop over future expiry dates
    while expiryDate <= expiryLimitDate:
        expiryDate = startDate + relativedelta(months=month_count)
        year = expiryDate.year
        year_flag = str(year % 100)
        month = expiryDate.month
        month_flag = month_flag_dict[month]
        ticker = instrument_flag + month_flag + year_flag

        url = f"https://www.barchart.com/futures/quotes/{ticker}/price-history/historical"
        response = requests.get(url)
        print(f"HTTP status code: {response.status_code}")
        if response.status_code in [404]:
            print(f"Error in URL {url}")
            break

        # # Wait for page to load and scroll to trigger lazy loading
        # time.sleep(5)  # or use WebDriverWait if needed
        # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        # time.sleep(3)

        # Locate the shadow host
        try:
            driver.get(url)
            shadow_host = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "bc-data-grid"))
            )
        except TimeoutException as e:
            print(f"Ticker: {ticker}: Timeout exception.")
            month_count += 1
            continue
        except TimeoutError as e:
            print(f"Ticker: {ticker}: Timeout error.")
            month_count += 1
            continue
        except BaseException as e:
            print(f"Ticker: {ticker}: Other error.")
            month_count += 1
            continue


        earliestFetchedDate = None
        
        # Wait for page to load and scroll to trigger lazy loading
        # scroll_to_load_all(driver)
        # Access shadow root
        shadow_root = driver.execute_script("return arguments[0].shadowRoot", shadow_host)
        time.sleep(3)
        earliestFetchedDatePrevious = None
        c = 0

        while (earliestFetchedDate == None or
               (earliestFetchedDate > earliestDateNeeded and earliestFetchedDatePrevious != earliestFetchedDate)):
            if earliestFetchedDate == None:
                if c == 0:
                    print(f"Ticker: {ticker}, Started")
                else:
                    print(f"Ticker: {ticker}, No data")
                    break
            else:
                print(f"Ticker: {ticker}, Earliest Fetched Date: {str(earliestFetchedDate)}")

            earliestFetchedDatePrevious = earliestFetchedDate

            scroll_to_load_all(driver)
            shadow_root = driver.execute_script("return arguments[0].shadowRoot", shadow_host)
            time.sleep(3)
            # Get the table element inside shadow root
            grid_element = shadow_root.find_element(By.CSS_SELECTOR, "div._grid")

            # Extract and clean text
            raw = grid_element.text.strip().split("\n")

            # First 9 lines are headers
            columns = raw[:9]
            data_rows = raw[9:]

            # Group into records (chunks of 9)
            records = [data_rows[i:i+9] for i in range(0, len(data_rows), 9) if len(data_rows[i:i+9]) == 9]

            if len(records) > 0:
                # Create DataFrame
                df = pd.DataFrame(records, columns=columns)
    
                # Convert 'Time' column to datetime and search
                df['Time'] = pd.to_datetime(df['Time'].str.strip(), format="%m/%d/%Y")
                earliestFetchedDate = pd.to_datetime(df["Time"].values[-1])
            

                df.rename(columns={'Time': 'Date'}, inplace=True)
                df.sort_values(by='Date', ascending=True, inplace=True)
                latest_date = None
                if not df_latest is None:
                    df_ticker = df_latest[df_latest.Ticker == ticker]
                    if not df_ticker.empty:
                        latest_date = df_ticker['Date'].max()
                if not latest_date is None:
                    df = df[df.Date > latest_date]
                # convert "unch" to 0 in Change and %Chg columns
                df['Change'] = df["Change"].map(lambda x: 0.0 if x == "unch" else float(x) if x.isdigit() else x)
                df.rename(columns={"%Change": '%Chg'}, inplace=True)
                df['%Chg'] = df["%Chg"].map(lambda x: 0.0 if x == "unch" else float(x[:-1]) if x[:-1] == "%" else float(x) if x.isdigit() else x)

                # insert Ticker column in front
                df.insert(loc=0, column="Ticker", value=ticker)

                dfs.append(df)
            c = c + 1

        print(f"Ticker: {ticker}: Finished.")
        month_count += 1
    print(f"Future tenor type: {instrument_flag}: Finished.")

result_df = pd.concat(dfs, axis=0)
if len(df) > 0:
    result_df = result_df.drop_duplicates(['Ticker', 'Date'])
    result_df.to_excel(DIR + "/" + OUTPUT_FILE, index=False)

    shutil.copy(DIR + "/" + OUTPUT_FILE, latest_full_path)

    print("Finished all")

else:
    print("Skipped due to no update on website.")
