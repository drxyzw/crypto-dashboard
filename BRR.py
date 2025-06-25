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
import time
import os
import pandas as pd
import json
from utils import datetimeToTimestamp, timestampToDatetime

loadDate = dt.now()
OUTPUT_FILE = "CME_BTC_Future_" + loadDate.isoformat() + ".xlsx"
OUTPUT_FILE = OUTPUT_FILE.replace(":", "")
keepOpen = True

url_dict = {
    "BRR": "https://www.cfbenchmarks.com/data/indices/BRR",
    "BRRNY": "https://www.cfbenchmarks.com/data/indices/BRRNY",
    "BRRAP": "https://www.cfbenchmarks.com/data/indices/BRRAP"
    }

options = webdriver.ChromeOptions()
options.add_experimental_option("detach", False)
# options.add_argument("headless")
# options.add_argument("disable-gui")

driver = webdriver.Chrome(options=options)

# get date list
for indexName, url in url_dict.items():
    driver.get(url)
    ret = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "__NEXT_DATA__")))
    innerJsonString = ret.get_attribute("innerHTML")
    innerJson = json.loads(innerJsonString)
    price_dict_list = innerJson['props']['pageProps']['indexConfig']['rrs']
    price_df = pd.DataFrame(price_dict_list)
    price_df = price_df[["time", "value"]].copy()
    price_df['time'] = price_df['time'].map(lambda x: timestampToDatetime(x).isoformat())

    os.makedirs("./data", exist_ok=True)
    price_df.to_excel(f"./data/historical_{indexName}.xlsx", index=False)
    print(f"finished {indexName}")

print("Finished all")
