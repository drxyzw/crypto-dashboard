from workalendar.usa import UnitedStates
import QuantLib as ql
HOLIDAY_YEARS = list(range(2020, 2080 + 1))

def USCalendar(subType = ql.UnitedStates.SOFR):
    cal = ql.WeekendsOnly()
    us_cal = UnitedStates()
    us_holidays = [us_cal.holidays(y) for y in HOLIDAY_YEARS]
    us_holidays = sum(us_holidays, []) # make it flat
    for d, _ in us_holidays:
        cal.addHoliday(ql.Date(d.day, d.month, d.year))

    return cal

    # def __init__(self, *args, **kwargs):
    #     super().__init__(args, kwargs)

    # def name(self):
    #     return "US Calendar from workalendar"
    
    # def isWeekend(self, w):
    #     return w == ql.Saturday or w == ql.Sunday
    
    # def isBusinessDay(self, date):
    #     py_date = date.to_date()
    #     us_holidays = workalendar.US(years=[py_date.year])

    #     return not (self.isWeekend(date.weekday()) or py_date in us_holidays)

    # def isBusinessPyDay(self, py_date):
    #     us_holidays = workalendar.US(years=[py_date.year])
    #     ql_date = ql.Date(py_date.year, py_date.month, py_date.day)

    #     return not (self.isWeekend(ql_date.weekday()) or py_date in us_holidays)
