# -*- coding: utf-8 -*-
import sys, datetime as dt
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
import engine as E
from korean_lunar_calendar import KoreanLunarCalendar

E.selftest()
for y in range(2024, 2031):
    hs = E.holidays_of(y)
    non_sun = [h for h in hs if h["date"].weekday() != 6]
    print(y, "공휴일", len(hs), "일요일제외", len(non_sun), "대체", sum(1 for h in hs if h["sub"]))
    if y in (2025, 2026, 2027):
        for h in hs:
            print("  ", h["date"], E.WD[h["date"].weekday()], h["name"])
# 2027 월력요항: 일요일 겹침 4일 포함 24일
hs27 = E.holidays_of(2027)
print("2027 total", len(hs27), "(기대 24)")

# 절기: 2027
for t in E.terms_of_year(2027)[:6]:
    print(t["name"], t["at"].strftime("%Y-%m-%d %H:%M"))
for t in E.terms_of_year(2027):
    if t["name"] in ("소서", "대서"): print(t["name"], t["at"].strftime("%m-%d %H:%M"))

# 라이브러리의 간지(월·일)와 비교
c = KoreanLunarCalendar()
bad_day = bad_mon = 0
d0 = dt.date(2020, 1, 1)
n = 0
for i in range(0, 365 * 11):
    d = d0 + dt.timedelta(days=i)
    c.setSolarDate(d.year, d.month, d.day)
    g = c.getGapJaString()  # "갑자년 을축월 병인일"
    parts = g.split()
    dayg = parts[2][:2]; mong = parts[1][:2]
    if dayg != E.ganzhi(E.day_index(d)): bad_day += 1
    # 월간지의 지지가 우리 월지와 같은지
    if mong[1] != E.BRANCHES[E.month_branch_for(d)]:
        bad_mon += 1
        if bad_mon <= 8: print("월지 불일치", d, g, E.BRANCHES[E.month_branch_for(d)])
    n += 1
print("일진 불일치", bad_day, "월지 불일치", bad_mon, "/", n)
# 예: 오늘
for d in (dt.date(2027, 2, 6), dt.date(2027, 3, 12)):
    print(d, E.lunar_of(d), E.ganzhi(E.day_index(d)), E.shin12_of(d), E.hwangdo_of(d), E.is_sonnopneun(d),
          [E.judge(d, p)[0] for p in E.PURPOSE])
