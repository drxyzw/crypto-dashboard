from datetime import datetime as dt
from dateutil import relativedelta
import pandas as pd
from market.load_market import loadMarket
from market.volatility.volatility_surface import *

PROCESSED_DIR = "./data_processed"
    
if __name__ == "__main__":
    py_date = dt(2025, 6, 13)
    # py_date = dt(2025, 6, 20)
    # py_date = dt(2025, 7, 14)

    dfs_mkt_list = []
    # while py_date == dt(2025, 6, 20):
    while py_date < dt.now():
        for regularize_vol in [True, False]:
            market = loadMarket(py_date)
            market_vol = build_volatility_surface(market, regularize_vol=regularize_vol)
            market = None
            market_vol = None
            if not market_vol is None:
                market = market_vol

            if not market is None:
                str_date = py_date.strftime("%Y-%m-%d")
                df_mkt_list = pd.DataFrame({"Date": [str_date], "MarketObjects": [str(list(market.keys()))]})
                dfs_mkt_list.append(df_mkt_list)
            py_date += relativedelta(days=1)

        if len(dfs_mkt_list) > 0:
            file_name = "market_objects_regularized_vol.xlsx" if regularize_vol else "market_objects.xlsx" 
            df_mkt_list = pd.concat(dfs_mkt_list)
            df_mkt_list.to_excel(f"{PROCESSED_DIR}/{file_name}", index=False)
