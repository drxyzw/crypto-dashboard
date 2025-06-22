import requests
from datetime import datetime, timedelta
import pandas as pd
import os
import openpyxl

OUTPUT_DATA_DIR = "./data"

def timestampToDatetime(timestamp_ms):
    dt = datetime.fromtimestamp(int(timestamp_ms/1000))
    return dt

def datetimeToTimestamp(date_time):
    ts_ms = datetime.timestamp(date_time) * 1000
    return int(ts_ms)


url = "https://www.deribit.com/api/v2/public/get_instruments"
params = {
    "currency": "BTC",
    "kind": "option",
    "expired": "true"  # Include expired options
}
resp = requests.get(url, params=params)
data = resp.json()['result']

# # Filter an instrument, e.g. ATM call near a certain expiry
# for i in data:
#     if i['strike'] == 92000.0 and i['expiration_timestamp'] < 1680000000000:
#         print(i['instrument_name'])

print("deal data loaded")

data_dfs = []
trades_dfs = []
trades_merge_dfs = []
for k in range(len(data)):
    instrument_name = data[k]['instrument_name'] #"BTC-30JUN23-60000-C"  # Replace with desired
    url = "https://www.deribit.com/api/v2/public/get_last_trades_by_instrument_and_time"
    starttimestamp = int(data[k]['creation_timestamp'])
    end_timestamp = datetimeToTimestamp(datetime.now())
    params = {
        "instrument_name": instrument_name,
        "start_timestamp": starttimestamp,  # March 1, 2023
        "end_timestamp": end_timestamp,    # March 3, 2023
        "count": 1000
    }
    resp = requests.get(url, params=params)
    trades = resp.json()['result']['trades']

    # Print price and time
    for trade in trades:
        print(trade['price'], trade['timestamp'])
    
    # convert to DataFrame and merge
    if trades:
        data_df = pd.DataFrame(data[k])
        data_df['creation_timestamp'] = pd.to_datetime(data_df['creation_timestamp'], unit='ms').apply(lambda x: x.isoformat())
        data_df['expiration_timestamp'] = pd.to_datetime(data_df['expiration_timestamp'], unit='ms').apply(lambda x: x.isoformat())

        trade_df = pd.DataFrame(trades)
        trade_df['timestamp'] = pd.to_datetime(trade_df['timestamp'], unit='ms').apply(lambda x: x.isoformat())
        data_dfs.append(data_df)
        trades_dfs.append(trade_df)
        trade_merge_df = trade_df.merge(data_df, how="left", on="instrument_name")
        trades_merge_dfs.append(trade_merge_df)

historical_data_df = pd.concat(data_dfs, ignore_index=True)
historical_trade_df = pd.concat(trades_dfs, ignore_index=True)
historical_df = pd.concat(trades_merge_dfs, ignore_index=True)
os.makedirs(OUTPUT_DATA_DIR, exist_ok=True)
historical_df.to_excel(OUTPUT_DATA_DIR + "/historical.xlsx", index=False)
