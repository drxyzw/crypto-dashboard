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
    df_config = pd.DataFrame({"Name": ["Date", "Type", "SubType", "CCY", "Name", "DomesticDiscountingCurve", "ForeignDiscountingCurve", "Underlying"],
                              "Value": [marketDateStr, "Market", "Option", "BTC", "BTCUSD.OPTION", "USD.SOFR.CSA_USD", "BTC.FUNDING.CSA_USD", "Future"]})

    # df for data part
    df_data = pd.DataFrame(columns=["Tenor", "Ticker", "Type", "Rate"])

    # process BTC
    def processExpiryToExpiryDate(option_type_str, expiry_str):
        expiry_str_strip = expiry_str.strip().replace(" ", "")
        cal = UKorUSCalendar()
        if option_type_str == "European Options":
            year_str = expiry_str_strip[3:]
            month_str = expiry_str_strip[:3].upper()
            month_number = month_name_flag__reverse_dict[month_str]
            ql_date = ql.Date.endOfMonth(ql.Date(1, month_number, int(year_str)))
            ql_date = cal.adjust(ql_date, ql.Preceding)
            while ql_date.weekday() != ql.Friday:
                ql_date = cal.advance(ql_date, -1, ql.Days, ql.Preceding)
        elif "Weekly " in option_type_str:
            option_types = option_type_str.split(" ")
            dayOfWeek = weekday_flag[option_types[1]]
            expiry_strs = expiry_str.split(" ") # expiry_str is "Week n-MMM YYYY"
            nth_week = int(expiry_strs[1][0])
            expiry_month = month_name_flag__reverse_dict[expiry_strs[1][2:].upper()]
            expiry_year = int(expiry_strs[2])
            ql_date = ql.Date.nthWeekday(nth_week, dayOfWeek, expiry_month, expiry_year)
            while not cal.isBusinessDay(ql_date):
                nth_week += 1
                ql_date = ql.Date.nthWeekday(nth_week, dayOfWeek, expiry_month, expiry_year)

        py_date = ql_date.to_date()
        py_date_str = datetime.strftime(py_date, "%Y-%m-%d")
        return py_date_str
        
    df_BTC_OPTIONS = BTC_OPTIONS_raw[BTC_OPTIONS_raw['Date'] == marketDate].copy()
    if not df_BTC_OPTIONS.empty:
        df_BTC_OPTIONS['Tenor'] = df_BTC_OPTIONS.apply(lambda x: processExpiryToExpiryDate(x['OptionType'], x['Expiry']), axis=1)
        df_BTC_OPTIONS_melt = pd.melt(df_BTC_OPTIONS, id_vars=['Tenor', 'Strike'], value_vars=['SettleCallPrice', 'SettlePutPrice'], var_name="CallPut", value_name="Price")
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
