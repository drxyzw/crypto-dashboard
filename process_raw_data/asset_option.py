import pandas as pd
from datetime import datetime as dt
import numpy as np
import os
from joblib import Memory

from utils.config import *
from utils.calendar import *
from utils.convention import *

memory = Memory(location='./.joblib_cache', verbose=0)

RAW_DIR = "./data_raw"
BTC_OPTION_FILE = RAW_DIR + "/CME_BTC_option_latest.xlsx"
PROCESSED_DIR = "./data_processed"

@memory.cache
def load_excel_with_cache(file_path):
    return pd.read_excel(file_path)

def prepare_BTCUSD_options(marketDate):
    marketDateStr = marketDate.strftime("%Y-%m-%d")
    marketDateStrNoHyphen = marketDate.strftime("%Y%m%d")
    BTC_OPTIONS_raw = load_excel_with_cache(BTC_OPTION_FILE)

    BTC_OPTIONS_raw['Date'] = pd.to_datetime(BTC_OPTIONS_raw['Date'])

    # df for config sheet
    df_config = pd.DataFrame({"Name": ["Date", "Type", "SubType", "CCY", "Spot", "Name", "DomesticDiscountingCurve", "ForeignDiscountingCurve", "Underlying"],
                              "Value": [marketDateStr, "Market", "Option", "BTC", "BTCUSD.SPOT", "BTCUSD.OPTION", "USD.SOFR.CSA_USD", "BTC.FUNDING.CSA_USD", "Future"]})

    # df for data part
    df_data = pd.DataFrame(columns=["ExpiryDate", "FutureExpiryDate", "Ticker", "Type", "Rate"])

    # process BTC
    df_BTC_OPTIONS = BTC_OPTIONS_raw[BTC_OPTIONS_raw['Date'] == marketDate].copy()
    if not df_BTC_OPTIONS.empty:
        df_BTC_OPTIONS['ExpiryDate'] = df_BTC_OPTIONS.apply(lambda x: processBtcOptionExpiryToExpiryDate(x['OptionType'], x['Expiry']), axis=1)
        df_BTC_OPTIONS['FutureExpiryDate'] = df_BTC_OPTIONS['ExpiryDate'].map(processBtcOptionNearestFutureExpiryDate)
        df_BTC_OPTIONS_melt = pd.melt(df_BTC_OPTIONS, id_vars=['ExpiryDate', 'FutureExpiryDate', 'Strike'], value_vars=['SettleCallPrice', 'SettlePutPrice'], var_name="CallPut", value_name="Price")
        df_BTC_OPTIONS_melt.rename(columns={'CallPut': 'OptionType'}, inplace=True)
        df_BTC_OPTIONS_melt['OptionType'] = np.where(df_BTC_OPTIONS_melt['OptionType'] == "SettleCallPrice", "Call", "Put")
        df_BTC_OPTIONS_melt['Price'] = df_BTC_OPTIONS_melt['Price'].map(lambda x: 0.0 if x == "CAB" or x == "-" else float(x))
        df_data = df_BTC_OPTIONS_melt.copy()
    
    PROCESSED_FILE = f"BTCUSDOPTION_{marketDateStrNoHyphen}.xlsx"
    if len(df_data):
        directory = PROCESSED_DIR + f"./{marketDateStrNoHyphen}"
        os.makedirs(directory, exist_ok=True)
        with pd.ExcelWriter(directory + "/" + PROCESSED_FILE) as ew:
            df_config.to_excel(ew, sheet_name="Config", index=False)
            df_data.to_excel(ew, sheet_name="Data", index=False)

        print(f"Exported {PROCESSED_FILE}.")
    else:
        print(f"Skipped exporting {PROCESSED_FILE} because fetched data is empty.")


if __name__ == "__main__":
    marketDate = dt(2025, 6, 13)
    while marketDate < dt.now():
        prepare_BTCUSD_options(marketDate)
        marketDate += relativedelta(days=1)
