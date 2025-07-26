from datetime import datetime as dt
from market.load_market import loadMarket
from market.volatility.volatility_surface import *

PROCESSED_DIR = "./data_processed"
    
if __name__ == "__main__":
    py_date = dt(2025, 6, 13)
    # py_date = dt(2025, 7, 14)

    dfs_mkt_list = []
    while py_date < dt.now():
        market = loadMarket(py_date)
        build_volatility_surface(market)

        if not market is None:
            str_date = py_date.strftime("%Y-%m-%d")
            df_mkt_list = pd.DataFrame({"Date": [str_date], "MarketObjects": [str(list(market.keys()))]})
            dfs_mkt_list.append(df_mkt_list)
        py_date += relativedelta(days=1)

    if len(dfs_mkt_list) > 0:
        df_mkt_list = pd.concat(dfs_mkt_list)
        df_mkt_list.to_excel(PROCESSED_DIR + "/market_objects.xlsx", index=False)
