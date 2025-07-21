from datetime import datetime as dt
from market.load_market import loadMarket
from market.volatility.volatility_surface import *

    
if __name__ == "__main__":
    py_date = dt(2025, 6, 13)
    # py_date = dt(2025, 7, 14)
    while py_date < dt.now():
        market = loadMarket(py_date)
        market = build_volatility_surface(market)
        py_date += relativedelta(days=1)

