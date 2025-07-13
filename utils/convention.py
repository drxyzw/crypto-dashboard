from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
from utils.config import * 
from utils.calendar import *

def IMM_date(year, month, must_be_business_day = True):
    d = dt(year=year, month=month, day=15)
    while d.weekday() != 2: # 0=Monday, 1=Tuesday, 2=Wednesday
        d += relativedelta(days=1)
    if must_be_business_day:
        cal = USCalendar(ql.UnitedStates.SOFR)
        ql_date = ql.Date(d.day, d.month, d.year)
        ql_date = cal.adjust(ql_date, ql.Preceding)
        d = ql_date.to_date()

    return d

def nbMonths(tenorStr):
    tenorStrStrip = tenorStr.strip()
    unit = tenorStrStrip[-1].upper()
    nb = int(tenorStrStrip[:-1])
    if unit == "M":
        return nb
    elif unit == "Y":
        return nb * 12
    else:
        raise ValueError(f"nbMonths function does not support a unit: {unit}")

def SOFR_futures_reference_peiord(ticker):
    periodMonths = expiry_months[ticker[:2]]
    expiry_year = int("20" + ticker[-2:])
    month_flag_dict_reverse = {v: k for k, v in month_flag_dict.items()}
    expiry_month = month_flag_dict_reverse[ticker[2:3]]

    deliveryDate = IMM_date(expiry_year, expiry_month, must_be_business_day=True)
    startDate = deliveryDate - relativedelta(months=periodMonths)
    startDate = IMM_date(startDate.year, startDate.month, must_be_business_day=False)

    return startDate, deliveryDate

def delta_months(datetime1, datetime2):
    delta = relativedelta(datetime2, datetime1)
    return delta.years * 12 + delta.months

def parseToRelativeDelta(tenorStr):
    tenorStrStrip = tenorStr.strip()
    unit = tenorStrStrip[-1].upper()
    nb = int(tenorStrStrip[:-1])
    if unit == "D":
        return relativedelta(days=nb)
    elif unit == "W":
        return relativedelta(days=nb * 7)
    elif unit == "M":
        return relativedelta(months=nb)
    elif unit == "Y":
        return relativedelta(years=nb)
    else:
        raise ValueError(f"nbMonths function does not support a unit: {unit}")
    