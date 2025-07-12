import requests
from datetime import datetime
import pandas as pd
import os
import time
import openpyxl
from fetch_data.utils import datetimeToTimestamp, timestampToDatetime

OUTPUT_DATA_DIR = "./raw_data"
os.makedirs(OUTPUT_DATA_DIR, exist_ok=True)

# --- Fetch all BTC option instruments (include expired) ---
print("Loading instrument metadata...")
url = "https://www.deribit.com/api/v2/public/get_instruments"
params = {
    "currency": "BTC",
    "kind": "option",
    "expired": "true"
}
resp = requests.get(url, params=params)
data = resp.json()['result']
print(f"Total instruments loaded: {len(data)}")

# --- Initialize output storage ---
data_dfs = []
trades_dfs = []
trades_merge_dfs = []

# --- Loop through each instrument ---
for instrument in data:
    instrument_name = instrument['instrument_name']
    start_timestamp = instrument['creation_timestamp']
    end_timestamp = datetimeToTimestamp(datetime.now())

    print(f"\nFetching trades for: {instrument_name}")

    all_trades = []
    max_pages = 20  # Prevent infinite loop on very active options

    while True:
        url = "https://www.deribit.com/api/v2/public/get_last_trades_by_instrument_and_time"
        params = {
            "instrument_name": instrument_name,
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "count": 1000
        }
        try:
            resp = requests.get(url, params=params)
            result = resp.json().get('result', {})
            trades = result.get('trades', [])
        except Exception as e:
            print(f"Error fetching trades for {instrument_name}: {e}")
            break

        if not trades:
            break

        all_trades.extend(trades)

        # Step back in time
        min_timestamp = min(t['timestamp'] for t in trades)
        end_timestamp = min_timestamp - 1

        if end_timestamp < start_timestamp:
            break

        time.sleep(0.2)

    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], unit='ms')
        trades_df['instrument_name'] = instrument_name

        data_df = pd.DataFrame([instrument])
        data_df['creation_timestamp'] = pd.to_datetime(data_df['creation_timestamp'], unit='ms')
        data_df['expiration_timestamp'] = pd.to_datetime(data_df['expiration_timestamp'], unit='ms')

        merged_df = trades_df.merge(data_df, how='left', on='instrument_name')

        trades_dfs.append(trades_df)
        data_dfs.append(data_df)
        trades_merge_dfs.append(merged_df)

# --- Combine and export ---
if trades_merge_dfs:
    historical_df = pd.concat(trades_merge_dfs, ignore_index=True)
    print(f"\nTotal trades collected: {len(historical_df)}")
    historical_df.to_excel(os.path.join(OUTPUT_DATA_DIR, "historical_option_trades.xlsx"), index=False)
else:
    print("No trade data found.")
