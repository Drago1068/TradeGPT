from __future__ import annotations
import calendar
from dataclasses import dataclass
from datetime import date,datetime,time,timedelta
from zoneinfo import ZoneInfo
EASTERN=ZoneInfo("America/New_York")
PRODUCTION_SCAN_IDS=("daily-discovery","primary-qualification","late-day-discovery")
@dataclass(frozen=True)
class ScanSchedule:
    id:str; label:str; time_et:time; enabled:bool=True
    @classmethod
    def from_time_string(cls,scan_id,label,time_et,enabled=True):
        parsed=time.fromisoformat(time_et)
        if parsed.second or parsed.microsecond: raise ValueError(f"scan time must be HH:MM for {scan_id}")
        return cls(scan_id,label,parsed,enabled)
def _observed_fixed_holiday(y,m,d):
    x=date(y,m,d)
    return x-timedelta(days=1) if x.weekday()==5 else x+timedelta(days=1) if x.weekday()==6 else x
def _nth_weekday(y,m,w,n):
    first=date(y,m,1); return first+timedelta(days=(w-first.weekday())%7+7*(n-1))
def _last_weekday(y,m,w):
    last=date(y,m,calendar.monthrange(y,m)[1]); return last-timedelta(days=(last.weekday()-w)%7)
def _easter_sunday(y):
    a=y%19;b=y//100;c=y%100;d=b//4;e=b%4;f=(b+8)//25;g=(b-f+1)//3;h=(19*a+b-d-g+15)%30;i=c//4;k=c%4;l=(32+2*e+2*i-h-k)%7;m=(a+11*h+22*l)//451;mo=(h+l-7*m+114)//31;da=((h+l-7*m+114)%31)+1
    return date(y,mo,da)
def nyse_holidays(y):
    return frozenset({_observed_fixed_holiday(y,1,1),_nth_weekday(y,1,0,3),_nth_weekday(y,2,0,3),_easter_sunday(y)-timedelta(days=2),_last_weekday(y,5,0),_observed_fixed_holiday(y,6,19),_observed_fixed_holiday(y,7,4),_nth_weekday(y,9,0,1),_nth_weekday(y,11,3,4),_observed_fixed_holiday(y,12,25)})
def is_market_holiday(day): return day in nyse_holidays(day.year)
def validate_production_schedule(schedules):
    if len(schedules)!=3 or {s.id for s in schedules}!=set(PRODUCTION_SCAN_IDS): raise ValueError("production schedule ids do not match the production contract")
    if len({s.id for s in schedules})!=3: raise ValueError("production schedule contains duplicate scan ids")
    enabled={s.time_et for s in schedules if s.enabled}
    if len(enabled)!=sum(s.enabled for s in schedules): raise ValueError("enabled production scans cannot share a scheduled time")
    return tuple(sorted(schedules,key=lambda s:s.time_et))
def is_scan_day(moment):
    d=moment.astimezone(EASTERN).date(); return d.weekday()<5 and not is_market_holiday(d)
def scheduled_datetime(moment,schedule):
    local=moment.astimezone(EASTERN); return datetime.combine(local.date(),schedule.time_et,tzinfo=EASTERN)
def due_scans(now,schedules,last_run=None):
    validate_production_schedule(list(schedules)); local=now.astimezone(EASTERN)
    if not is_scan_day(local): return ()
    last_run=last_run or {}; due=[]
    for s in schedules:
        if not s.enabled: continue
        if local>=scheduled_datetime(local,s) and (s.id not in last_run or last_run[s.id].astimezone(EASTERN).date()!=local.date()): due.append(s)
    return tuple(sorted(due,key=lambda s:s.time_et))
def next_run(now,schedules):
    ordered=validate_production_schedule(list(schedules)); local=now.astimezone(EASTERN); cursor=local
    for _ in range(8):
        if is_scan_day(cursor):
            for s in ordered:
                if s.enabled:
                    c=scheduled_datetime(cursor,s)
                    if c>local:return s,c
        cursor=datetime.combine(cursor.date()+timedelta(days=1),time.min,tzinfo=EASTERN)
    return None
def default_production_schedule():
    return validate_production_schedule([
        ScanSchedule.from_time_string("daily-discovery","Daily Sniper Discovery","08:00"),
        ScanSchedule.from_time_string("primary-qualification","Daily Trade Qualification","10:15"),
        ScanSchedule.from_time_string("late-day-discovery","Late Day Discovery","15:00")])