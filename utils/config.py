from datetime import datetime

sofr_instrument_flags = [
    "SL", # 1-month SOFR futures
    "SQ", # 3-month SOFR futures
    ]
sofr_expiry_months = {
    "SL": 1,
    "SQ": 3,
}
sofr_expiry_year_limits = {
    "SL": 1,
    "SQ": 3,
}
sofr_futures_months_liquidity_limit = {
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

month_name_flag_dict = {
    1: "JAN", # Jan
    2: "FEB", # Feb
    3: "MAR", # Mar
    4: "APR", # Apr
    5: "MAR", # May
    6: "JUN", # Jun
    7: "JLY", # Jul
    8: "AUG", # Aug
    9: "SEP", # Sep
    10: "OCT", # Oct
    11: "NOV", # Nov
    12: "DEC", # Dec
}
month_name_flag__reverse_dict = {v: k for k, v in month_name_flag_dict.items()}
month_name_flag__reverse_dict["JUL"] = 7

weekday_flag = {
    "Sunday": 1,
    "Monday": 2,
    "Tuesday": 3,
    "Wednesday": 4,
    "Thursday": 5,
    "Friday": 6,
    "Saturday": 7,
}

def timestampToDatetime(timestamp_ms):
    return datetime.fromtimestamp(timestamp_ms / 1000)

def datetimeToTimestamp(dt):
    return int(dt.timestamp() * 1000)

