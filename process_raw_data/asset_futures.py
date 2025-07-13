import pandas as pd
from datetime import datetime as dt
import os

from utils.config import *
from utils.calendar import *
from utils.convention import *

RAW_DIR = "./data_raw"
BTC_FUTURES_FILE = RAW_DIR + "/CME_BTC_future_latest.xlsx"
PROCESSED_DIR = "./data_processed"

def prepare_BTCUSD_futures(marketDate):
    marketDateStr = marketDate.strftime("%Y-%m-%d")
    marketDateStrNoHyphen = marketDate.strftime("%Y%m%d")
    BTC_FUTURES_raw = pd.read_excel(BTC_FUTURES_FILE)

    BTC_FUTURES_raw['Date'] = pd.to_datetime(BTC_FUTURES_raw['Date'])

    # df for config sheet
    df_config = pd.DataFrame({"Name": ["Date", "Type", "SubType", "CCY", "Name", "BaseDiscountingCureve"],
                              "Value": [marketDateStr, "Market", "YieldCurve", "BTC", "BTC.FUNDING.CSA_USD", "USD.SOFR.CSA_USD"]})

    # df for data part
    df_data = pd.DataFrame(columns=["Tenor", "Ticker", "Type", "Rate"])

    # process BTC
    def processExpiryToTicker(expiry_str):
        expiry_str_strip = expiry_str.strip().replace(" ", "")
        year_str = expiry_str_strip[3:]
        month_str = expiry_str_strip[:3]
        month_number = month_name_flag__reverse_dict[month_str]
        month_flag = month_flag_dict[month_number]
        flag = "BTC" + month_flag + year_str
        return flag
    def processExpiryToExpiryDate(expiry_str):
        expiry_str_strip = expiry_str.strip().replace(" ", "")
        year_str = "20" + expiry_str_strip[3:]
        month_str = expiry_str_strip[:3]
        month_number = month_name_flag__reverse_dict[month_str]
        cal = ql.JointCalendar(USCalendar(), UKCalendar())
        ql_date = ql.Date.endOfMonth(ql.Date(1, month_number, int(year_str)))
        ql_date = cal.adjust(ql_date, ql.Preceding)
        while ql_date.weekday() != ql.Friday:
            ql_date = cal.advance(ql_date, -1, ql.Days, ql.Preceding)
        py_date = ql_date.to_date()
        py_date_str = datetime.strftime(py_date, "%Y-%m-%d")
        return py_date_str
        
    df_BTC_FUTURES = BTC_FUTURES_raw[BTC_FUTURES_raw['Date'] == marketDate].copy()
    if not df_BTC_FUTURES.empty:
        df_BTC_FUTURES['Ticker'] = df_BTC_FUTURES['Expiry'].map(processExpiryToTicker)
        df_BTC_FUTURES['Tenor'] = df_BTC_FUTURES['Expiry'].map(processExpiryToExpiryDate)
        df_BTC_FUTURES['Type'] = "FUTURE"
        df_BTC_FUTURES.rename(columns={'SettlePrice': 'Rate'}, inplace=True)
        df_data = df_BTC_FUTURES[['Tenor', 'Ticker', 'Type', 'Rate']]
    
    PROCESSED_FILE = f"BTCUSDFUNDINGCSA_USD_{marketDateStrNoHyphen}.xlsx"
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
    prepare_BTCUSD_futures(marketDate)
    # marketDate = dt(2025, 6, 13)
    # while marketDate < dt.now():
    #     prepare_BTCUSD_futures(marketDate)
    #     marketDate += relativedelta(days=1)
