import pandas as pd
from datetime import datetime as dt
import os

from utils.config import *
from utils.calendar import *
from utils.convention import *

RAW_DIR = "./data_raw"
BTC_SPOT_FILE = RAW_DIR + "/CME_BRR_latest.xlsx"
PROCESSED_DIR = "./data_processed"

def prepare_BTCUSD_spot(marketDate):
    marketDateStr = marketDate.strftime("%Y-%m-%d")
    marketDateStrNoHyphen = marketDate.strftime("%Y%m%d")
    BTC_SPOT_raw = pd.read_excel(BTC_SPOT_FILE)

    BTC_SPOT_raw['Date'] = pd.to_datetime(BTC_SPOT_raw['Date'])

    # df for config sheet
    df_config = pd.DataFrame({"Name": ["Date", "Type", "SubType", "CCY", "Name", "DomesticDiscountingCurve", "ForeignDiscountingCurve"],
                              "Value": [marketDateStr, "Market", "Spot", "BTC", "BTCUSD.SPOT", "USD.SOFR.CSA_USD", "BTC.FUNDING.CSA_USD"]})

    df_data = None

    # process BTC
    df_BTC_SPOT = BTC_SPOT_raw[BTC_SPOT_raw['Date'] == marketDate]
    if not df_BTC_SPOT.empty:
        BTC_SPOT = df_BTC_SPOT["BRR"].values[0]
        df_data = pd.DataFrame({"Name": ["Spot"],
                              "Value": [BTC_SPOT]})
    
    PROCESSED_FILE = f"BTCUSDSPOT_{marketDateStrNoHyphen}.xlsx"
    if (not df_data is None) and (len(df_data)):
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
        prepare_BTCUSD_spot(marketDate)
        marketDate += relativedelta(days=1)
