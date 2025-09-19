from datetime import datetime as dt
import pandas as pd

from market.load_market import loadMarket
from analyze_data.moment.momentFromProbability import *
from dateutil.relativedelta import relativedelta

ANALYZED_DIR = "./data_analyzed"
    
if __name__ == "__main__":
    py_date = dt(2025, 6, 13)
    # py_date = dt(2025, 8, 15)
    # py_date = dt(2025, 7, 14)

    dfs_moment = []
    while py_date < dt.now():
        market = loadMarket(py_date)
        if not market is None:
            df = compute_moment(market)
            if not df is None:
               df.insert(loc=0, column="Date", value=[py_date.strftime("%Y-%m-%d")] * len(df))
               dfs_moment.append(df)
        py_date += relativedelta(days=1)

    if len(dfs_moment) > 0:
        df_moment = pd.concat(dfs_moment)
        df_moment.to_excel(ANALYZED_DIR + "/moment.xlsx", index=False)
