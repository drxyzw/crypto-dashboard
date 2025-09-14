import pandas as pd
from datetime import datetime as dt
import os

from utils.config import *
from utils.calendar import *
from utils.convention import *

RAW_DIR = "./data_raw"
BTC_FUTURES_FILE = RAW_DIR + "/CME_BTC_future_latest.xlsx"
PROCESSED_DIR = "./data_processed"

def prepare_BTCUSD_futures(marketDate, skipIfExist):
    marketDateStr = marketDate.strftime("%Y-%m-%d")
    marketDateStrNoHyphen = marketDate.strftime("%Y%m%d")
    PROCESSED_FILE = f"BTCUSDFUNDINGCSA_USD_{marketDateStrNoHyphen}.xlsx"
    directory = PROCESSED_DIR + f"./{marketDateStrNoHyphen}"
    output_file = directory + "/" + PROCESSED_FILE

    # if output file exists already, just skip
    if skipIfExist and os.path.isfile(output_file):
        print(f"Skipped exporting {PROCESSED_FILE} because output file exists already.")
        return

    BTC_FUTURES_raw = pd.read_excel(BTC_FUTURES_FILE)

    BTC_FUTURES_raw['Date'] = pd.to_datetime(BTC_FUTURES_raw['Date'])

    # df for config sheet
    df_config = pd.DataFrame({"Name": ["Date", "Type", "SubType", "CCY", "Name", "BaseDiscountingCurve", "Spot"],
                              "Value": [marketDateStr, "Market", "YieldCurve", "BTC", "BTC.FUNDING.CSA_USD", "USD.SOFR.CSA_USD", "BTCUSD.SPOT"]})

    # df for data part
    df_data = pd.DataFrame(columns=["Tenor", "Ticker", "Type", "Rate"])

    # process BTC
    df_BTC_FUTURES = BTC_FUTURES_raw[BTC_FUTURES_raw['Date'] == marketDate].copy()
    if not df_BTC_FUTURES.empty:
        df_BTC_FUTURES['Ticker'] = df_BTC_FUTURES['Expiry'].map(processBtcFutureExpiryToTicker)
        df_BTC_FUTURES['Tenor'] = df_BTC_FUTURES['Expiry'].map(processBtcFutureExpiryToExpiryDate)
        df_BTC_FUTURES['Type'] = "FXFUTURE"
        df_BTC_FUTURES.rename(columns={'SettlePrice': 'Rate'}, inplace=True)
        df_data = df_BTC_FUTURES[['Tenor', 'Ticker', 'Type', 'Rate']]
    
    if len(df_data):
        os.makedirs(directory, exist_ok=True)
        with pd.ExcelWriter(output_file) as ew:
            df_config.to_excel(ew, sheet_name="Config", index=False)
            df_data.to_excel(ew, sheet_name="Data", index=False)

        print(f"Exported {PROCESSED_FILE}.")
    else:
        print(f"Skipped exporting {PROCESSED_FILE} because fetched data is empty.")


if __name__ == "__main__":
    marketDate = dt(2025, 6, 13)
    # marketDate = dt(2025, 7, 14)
    while marketDate < dt.now():
        prepare_BTCUSD_futures(marketDate, skipIfExist=True)
        marketDate += relativedelta(days=1)
