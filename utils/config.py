from datetime import datetime

instrument_flags = [
    "SL", # 1-month SOFR futures
    "SQ", # 3-month SOFR futures
    ]
expiry_months = {
    "SL": 1,
    "SQ": 3,
}
expiry_year_limits = {
    "SL": 1,
    "SQ": 3,
}
futures_months_liquidity_limit = {
    "SL": 3,
    "SQ": 18,
}
month_flag_dict = {
    1: "F", # Jan
    2: "G", # Feb
    3: "H", # Mar
    4: "J", # Apr
    5: "K", # May
    6: "M", # Jun
    7: "N", # Jul
    8: "Q", # Aug
    9: "U", # Sep
    10: "V", # Oct
    11: "X", # Nov
    12: "Z", # Dec
}

def timestampToDatetime(timestamp_ms):
    return datetime.fromtimestamp(timestamp_ms / 1000)

def datetimeToTimestamp(dt):
    return int(dt.timestamp() * 1000)

