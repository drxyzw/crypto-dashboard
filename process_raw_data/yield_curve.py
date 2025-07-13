import pandas as pd
from datetime import datetime as dt
import numpy as np

from utils.config import *
from utils.calendar import *
from utils.convention import *

RAW_DIR = "./data_raw"
SOFR_FILE = RAW_DIR + "/SOFR_latest.xlsx"
SOFR_FUTURES_FILE = RAW_DIR + "/SOFR_futures_latest.xlsx"
SOFR_OIS_FILE = RAW_DIR + "/SOFR_OIS_latest.xlsx"
PROCESSED_DIR = "./data_processed"

def prepare_SOFR_market(marketDate):
    marketDateStr = marketDate.strftime("%Y-%m-%d")
    marketDateStrNoHyphen = marketDate.strftime("%Y%m%d")
    sofr_raw = pd.read_excel(SOFR_FILE)
    sofr_futures_raw = pd.read_excel(SOFR_FUTURES_FILE)
    sofr_ois_raw = pd.read_excel(SOFR_OIS_FILE)

    sofr_raw['Date'] = pd.to_datetime(sofr_raw['Date'])
    sofr_futures_raw['Date'] = pd.to_datetime(sofr_futures_raw['Date'])
    sofr_ois_raw['Date'] = pd.to_datetime(sofr_ois_raw['Date'])

    # df for config sheet
    df_config = pd.DataFrame({"Name": ["Date", "CCY", "Name"],
                              "Value": [marketDateStr, "USD", "USD.SOFR.CSA_USD"]})

    # df for data part
    df_data = pd.DataFrame(columns=["Tenor", "Ticker", "Type", "Rate"])
    dfs_data = []

    # process SOFR
    df_sofr = sofr_raw[sofr_raw['Date'] == marketDate]
    if not df_sofr.empty:
        sofr = df_sofr["Rate"].values[0]
        df_sofr = pd.DataFrame([["ON", "SOFRRATE", "ONRATE", sofr]], columns=df_data.columns, )
        dfs_data.append(df_sofr)
    
    # process futures
    sofr_futures_raw.rename(columns={"Last": "Rate"}, inplace=True)
    df_futures = sofr_futures_raw[sofr_futures_raw['Date'] == marketDate][["Date", "Ticker", "Rate"]].reset_index(drop = True)
    if not df_futures.empty:
        df_futures['StartDate'] = df_futures["Ticker"].map(lambda x: SOFR_futures_reference_peiord(ticker=x)[0])
        df_futures['EndDate'] = df_futures["Ticker"].map(lambda x: SOFR_futures_reference_peiord(ticker=x)[1])
        df_futures['liquidity_months_limit'] = df_futures["Ticker"].map(lambda x: futures_months_liquidity_limit[x[:2]])
        df_futures['liquidity_date_limit'] = df_futures.apply(lambda x: dt(x['Date'].year, x['Date'].month, x['Date'].day) + relativedelta(months=x['liquidity_months_limit']), axis=1)
        df_futures['Include'] = (df_futures['Date'] < df_futures['StartDate']) & (df_futures['EndDate'] < df_futures['liquidity_date_limit'])
        df_futures = df_futures[df_futures['Include']].reset_index(drop=True)
        df_futures['Tenor'] = df_futures.apply(lambda x: str(delta_months(x['Date'].to_pydatetime(), x['EndDate'])) + "M", axis=1)
        df_futures['Type'] = "FUTURE"
        df_futures_export = df_futures[["Tenor", "Ticker", "Type", "Rate"]].reset_index(drop=True)
        dfs_data.append(df_futures_export)
    
    # process OIS
    df_ois = sofr_ois_raw[sofr_ois_raw['Date'] == marketDate].copy()
    if not df_ois.empty:
        df_ois['EndDate'] = df_ois.apply(lambda x: x['Date'] + parseToRelativeDelta(x['Tenor']), axis=1)
        if not df_futures.empty:
            maxFutureEndDate = pd.to_datetime(df_futures['EndDate'].max())
            df_ois = df_ois[df_ois['EndDate'] > maxFutureEndDate]
        df_ois['Ticker'] = "SOFROIS"
        df_ois['Type'] = "OIS"
        df_ois_export = df_ois[['Tenor', 'Ticker', 'Type', 'Rate']]
        dfs_data.append(df_ois_export)

    df_data = pd.concat(dfs_data)
    PROCESSED_FILE = f"USDSOFRCSA_USD_{marketDateStrNoHyphen}.xlsx"
    if not df_data.empty:
        with pd.ExcelWriter(PROCESSED_DIR + "./" + PROCESSED_FILE) as ew:
            df_config.to_excel(ew, sheet_name="Config", index=False)
            df_data.to_excel(ew, sheet_name="Data", index=False)

        print(f"Exported {PROCESSED_FILE}.")
    else:
        print(f"Skipped exporting {PROCESSED_FILE} because fetched data is empty.")


if __name__ == "__main__":
    # marketDate = dt(2025, 6, 13)
    # prepare_SOFR_market(marketDate)
    marketDate = dt(2025, 7, 8)
    prepare_SOFR_market(marketDate)
