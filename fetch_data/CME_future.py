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

loadDate = dt.now()
OUTPUT_FILE = "CME_BTC_Future_" + loadDate.isoformat() + ".xlsx"
OUTPUT_FILE = OUTPUT_FILE.replace(":", "")
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
dfs = []

# get date list
driver.get(url_base)
ret = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".trade-date-row.row")))
labelDate = driver.find_element(By.XPATH, "//label[contains(@class, 'form-label') and normalize-space(text())='Trade date']")
DateItems = labelDate.find_element(By.XPATH, "..").find_elements(By.CSS_SELECTOR, ".dropdown-item.dropdown-item")
DateChoices = [dt.strptime(item.get_attribute("data-value").strip(), "%m/%d/%Y") for item in DateItems]

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
df = pd.DataFrame(dic)
os.makedirs("./data", exist_ok=True)
df.to_excel("./data/" + OUTPUT_FILE, index=False)

print("Finished all")
