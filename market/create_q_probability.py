from datetime import datetime as dt
import pandas as pd

from market.load_market import loadMarket
from market.volatility.q_probability import *
from dateutil.relativedelta import relativedelta

PROCESSED_DIR = "./data_processed"

if __name__ == "__main__":
    py_date = dt(2025, 6, 13)
    # py_date = dt(2025, 7, 14)

    dfs_mkt_list = []
    while py_date < dt.now():
        market = loadMarket(py_date)
        market_qprob = build_q_probability(market)
        if not market_qprob is None:
            market = market_qprob

        if not market is None:
            str_date = py_date.strftime("%Y-%m-%d")
            df_mkt_list = pd.DataFrame({"Date": [str_date], "MarketObjects": [str(list(market.keys()))]})
            dfs_mkt_list.append(df_mkt_list)
        py_date += relativedelta(days=1)

    if len(dfs_mkt_list) > 0:
        df_mkt_list = pd.concat(dfs_mkt_list)
        df_mkt_list.to_excel(PROCESSED_DIR + "/market_qprobability.xlsx", index=False)
