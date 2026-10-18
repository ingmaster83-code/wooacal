# -*- coding: utf-8 -*-
"""우아달력 계산 엔진 — 음력(한국천문연구원 표 기반 korean_lunar_calendar), 24절기(ephem 태양 시황경),
일진·건제12신·황도일, 법정공휴일/대체공휴일 규칙, 손 없는 날, 이사·결혼·개업 택일 판정."""
import datetime as dt, math
import ephem
from korean_lunar_calendar import KoreanLunarCalendar

KST = dt.timezone(dt.timedelta(hours=9))
WD = ["월", "화", "수", "목", "금", "토", "일"]
STEMS = "갑을병정무기경신임계"
BRANCHES = "자축인묘진사오미신유술해"
STEM_H = "甲乙丙丁戊己庚辛壬癸"
BRANCH_H = "子丑寅卯辰巳午未申酉戌亥"
ANIMAL = ["쥐", "소", "호랑이", "토끼", "용", "뱀", "말", "양", "원숭이", "닭", "개", "돼지"]

# ── 24절기 ───────────────────────────────────────────
# (이름, 한자, 태양 시황경 도, 절/중기)
TERMS = [("소한","小寒",285,"절"),("대한","大寒",300,"중"),("입춘","立春",315,"절"),("우수","雨水",330,"중"),
         ("경칩","驚蟄",345,"절"),("춘분","春分",0,"중"),("청명","淸明",15,"절"),("곡우","穀雨",30,"중"),
         ("입하","立夏",45,"절"),("소만","小滿",60,"중"),("망종","芒種",75,"절"),("하지","夏至",90,"중"),
         ("소서","小暑",105,"절"),("대서","大暑",120,"중"),("입추","立秋",135,"절"),("처서","處暑",150,"중"),
         ("백로","白露",165,"절"),("추분","秋分",180,"중"),("한로","寒露",195,"절"),("상강","霜降",210,"중"),
         ("입동","立冬",225,"절"),("소설","小雪",240,"중"),("대설","大雪",255,"절"),("동지","冬至",270,"중")]

_APPROX = {285:(1,6),300:(1,20),315:(2,4),330:(2,19),345:(3,6),0:(3,20),15:(4,5),30:(4,20),45:(5,5),60:(5,21),
           75:(6,6),90:(6,21),105:(7,7),120:(7,23),135:(8,7),150:(8,23),165:(9,8),180:(9,23),195:(10,8),
           210:(10,23),225:(11,7),240:(11,22),255:(12,7),270:(12,22)}

def _sun_lon(d):
    s = ephem.Sun(); s.compute(d)
    ecl = ephem.Ecliptic(ephem.Equatorial(s.g_ra, s.g_dec, epoch=d), epoch=d)
    return math.degrees(ecl.lon) % 360

def term_time(year, lon):
    """해당 연도(양력)에 태양 시황경이 lon 이 되는 순간(KST datetime)."""
    m, dd = _APPROX[lon]
    c = dt.datetime(year, m, dd)
    lo = ephem.Date(c - dt.timedelta(days=3))
    hi = ephem.Date(c + dt.timedelta(days=3))
    for _ in range(60):
        mid = (lo + hi) / 2
        v = (_sun_lon(mid) - lon + 180) % 360 - 180
        if v < 0: lo = mid
        else: hi = mid
    utc = ephem.Date((lo + hi) / 2).datetime().replace(tzinfo=dt.timezone.utc)
    k = utc.astimezone(KST)
    return (k + dt.timedelta(seconds=30)).replace(second=0, microsecond=0)

_term_cache = {}
def terms_of_year(year):
    if year not in _term_cache:
        _term_cache[year] = [dict(idx=i, name=n, hanja=h, lon=lon, kind=kind, at=term_time(year, lon))
                             for i, (n, h, lon, kind) in enumerate(TERMS)]
    return _term_cache[year]

# ── 음력 ────────────────────────────────────────────
_lc = KoreanLunarCalendar()
_lunar_cache = {}
def lunar_of(d):
    """(음력연, 음력월, 음력일, 윤달여부)"""
    if d not in _lunar_cache:
        _lc.setSolarDate(d.year, d.month, d.day)
        _lunar_cache[d] = (_lc.lunarYear, _lc.lunarMonth, _lc.lunarDay, bool(_lc.isIntercalation))
    return _lunar_cache[d]

def solar_of(ly, lm, ld, leap=False):
    _lc.setLunarDate(ly, lm, ld, leap)
    return dt.date(_lc.solarYear, _lc.solarMonth, _lc.solarDay)

# ── 일진·월건 ───────────────────────────────────────
def day_index(d):  # 0..59, 갑자=0
    return (d.toordinal() + 14) % 60

def ganzhi(i): return STEMS[i % 10] + BRANCHES[i % 12]
def ganzhi_h(i): return STEM_H[i % 10] + BRANCH_H[i % 12]

_JEOL_BRANCH = {285:1,315:2,345:3,15:4,45:5,75:6,105:7,135:8,165:9,195:10,225:11,255:0}
_cuts_cache = {}
def _cuts(y):
    if y not in _cuts_cache:
        cuts = []
        for yy in (y - 1, y, y + 1):
            for t in terms_of_year(yy):
                if t["kind"] == "절":
                    cuts.append((t["at"].date(), _JEOL_BRANCH[t["lon"]]))
        cuts.sort()
        _cuts_cache[y] = cuts
    return _cuts_cache[y]

def month_branch_for(d):
    """절기(節) 기준 월지(0=자..11=해). 절입일(KST 날짜) 당일부터 새 달."""
    cur = None
    for cd, br in _cuts(d.year):
        if cd <= d: cur = br
        else: break
    return cur

SHIN12 = ["건","제","만","평","정","집","파","위","성","수","개","폐"]
SHIN12_H = ["建","除","滿","平","定","執","破","危","成","收","開","閉"]
SHIN12_DESC = {
 "건":"만물이 기운을 얻어 일어서는 날. 새 출발·입학·취임 같은 시작에 쓰이지만 땅을 파거나 장례는 꺼립니다.",
 "제":"묵은 것을 덜어내는 날. 청소·치료·정리에는 좋고, 혼례·이사 같은 경사는 보통으로 봅니다.",
 "만":"가득 차는 날. 혼례·이사·개업·입주 등 경사에 두루 길한 날로 꼽습니다.",
 "평":"평탄한 날. 큰 길흉이 없어 무난하며 길 닦기·담 쌓기 같은 일에 씁니다.",
 "정":"안정되는 날. 혼례·계약·입주·이사처럼 자리를 잡는 일에 길하다고 봅니다.",
 "집":"붙잡아 거두는 날. 계약·수확·집짓기는 좋으나 이사·여행은 평범하게 봅니다.",
 "파":"깨지는 날. 혼례·이사·개업·계약 등 큰일은 모두 피하는 흉일입니다.",
 "위":"위태로운 날. 높은 곳 작업·여행·큰 결정을 조심하고 경사는 피합니다.",
 "성":"이루어지는 날. 혼례·이사·개업·입학 등 거의 모든 일이 잘 맺어진다고 보는 길일입니다.",
 "수":"거두어들이는 날. 수금·수확·저축에 좋고 개업에도 무난하나 장례·출행은 꺼립니다.",
 "개":"열리는 날. 개업·개점·이사·혼례처럼 문을 여는 일에 대표적인 길일입니다.",
 "폐":"닫히는 날. 막고 닫는 일에만 좋고 개업·이사·혼례 등은 피합니다.",
}
def shin12_of_idx(d):
    return (day_index(d) % 12 - month_branch_for(d)) % 12

def shin12_of(d):
    return SHIN12[shin12_of_idx(d)]

HWANGDO = ["청룡","명당","천형","주작","금궤","천덕","백호","옥당","천뢰","현무","사명","구진"]
HWANGDO_GOOD = {"청룡","명당","금궤","천덕","옥당","사명"}
_HW_START = {2:0, 8:0, 3:2, 9:2, 4:4, 10:4, 5:6, 11:6, 0:8, 6:8, 1:10, 7:10}
def hwangdo_of(d):
    k = (day_index(d) % 12 - _HW_START[month_branch_for(d)]) % 12
    return HWANGDO[k]

# ── 법정공휴일 ──────────────────────────────────────
ELECTIONS = {dt.date(2024,4,10):"제22대 국회의원선거", dt.date(2025,6,3):"제21대 대통령선거",
             dt.date(2026,6,3):"제9회 전국동시지방선거", dt.date(2028,4,12):"제23대 국회의원선거",
             dt.date(2030,6,5):"제10회 전국동시지방선거"}
TEMP = {dt.date(2024,10,1):"국군의 날(임시공휴일)", dt.date(2025,1,27):"임시공휴일"}

def _lunar_days(year):
    """양력 year 안에 들어오는 음력 명절 날짜. 설 연휴 첫날이 전년 12월에 걸릴 수 있어 전후년 포함 반환."""
    out = {}
    for y in (year - 1, year, year + 1):
        seol = solar_of(y, 1, 1)
        for off, nm in ((-1, "설날 연휴"), (0, "설날"), (1, "설날 연휴")):
            out[seol + dt.timedelta(days=off)] = (nm, "seol")
        out[solar_of(y, 4, 8)] = ("부처님오신날", "buddha")
        ch = solar_of(y, 8, 15)
        for off, nm in ((-1, "추석 연휴"), (0, "추석"), (1, "추석 연휴")):
            out[ch + dt.timedelta(days=off)] = (nm, "chuseok")
    return out

def holidays_of(year):
    """[{date,name,key,sub,orig}] 날짜순. 관공서의 공휴일에 관한 규정(2026년 개정 반영) 기준."""
    base = {}
    fixed = [(1,1,"신정","sinjeong"),(3,1,"삼일절","samil"),(5,5,"어린이날","children"),(6,6,"현충일","hyunchung"),
             (8,15,"광복절","gwangbok"),(10,3,"개천절","gaecheon"),(10,9,"한글날","hangeul"),(12,25,"성탄절","christmas")]
    if year >= 2026:
        fixed += [(5,1,"노동절","labor"),(7,17,"제헌절","jeheon")]
    for m, dd, n, k in fixed: base[dt.date(year, m, dd)] = (n, k)
    lun = _lunar_days(year)
    collide = []
    overlap_days = set()
    for d, (n, k) in lun.items():
        if d.year == year:
            if d in base and k == "buddha":
                collide.append((d, base[d][0] + "·" + n))   # 어린이날과 부처님오신날이 같은 날
            elif d in base and k in ("seol", "chuseok"):
                overlap_days.add(d)                           # 설·추석 연휴가 다른 공휴일(예: 2028 추석·개천절)과 겹침
                base[d] = (n + " · " + base[d][0] if n in ("설날", "추석") else n, k)
            else:
                base[d] = (n, k)
    for d, n in ELECTIONS.items():
        if d.year == year: base[d] = (n, "election")
    for d, n in TEMP.items():
        if d.year == year: base[d] = (n, "temp")
    # 대체공휴일 판정은 전후 연도 연휴까지 고려(연말 설 연휴·연초 성탄절 대체 등) — 연휴 그룹 단위로
    taken = set(base)
    subs = {}
    # 전년도 12월 성탄절 대체 등은 다음 해 1월로 넘어갈 수 있으므로 이전 해 대체일도 taken 에 반영
    prev = _raw_subs_cache.get(year - 1)
    # 설·추석: 연휴(3일) 중 일요일이 있거나 다른 공휴일과 겹치면 연휴 다음 첫 비공휴일
    for key, nm in (("seol","설날"),("chuseok","추석")):
        grp = sorted(d for d, (n, k) in lun.items() if k == key and d.year == year or (k == key and d.year != year and False))
        # 연휴 전체(전년 12월 포함)를 같은 그룹으로 본다
        allg = sorted(d for d, (n, k) in lun.items() if k == key)
        for i in range(0, len(allg), 3):
            g = allg[i:i+3]
            if len(g) < 3: continue
            if g[1].year != year: continue
            overlap = any(x.weekday() == 6 for x in g) or any(x in overlap_days for x in g)
            if overlap:
                c = g[-1] + dt.timedelta(days=1)
                while c in taken or c.weekday() >= 5: c += dt.timedelta(days=1)
                subs[c] = ("대체공휴일(%s)" % nm, "sub_" + key, nm); taken.add(c)
    rules = []
    for d, (n, k) in sorted(base.items()):
        if k in ("children","samil","gwangbok","gaecheon","hangeul"): rules.append((d, n, k))
        elif k in ("buddha","christmas") and year >= 2023: rules.append((d, n, k))
        elif k in ("labor","jeheon") and year >= 2026: rules.append((d, n, k))
    for d, n, k in rules:
        if d.weekday() >= 5:
            c = d + dt.timedelta(days=1)
            while c in taken or c.weekday() >= 5: c += dt.timedelta(days=1)
            subs[c] = ("대체공휴일(%s)" % n, "sub_" + k, n); taken.add(c)
    for d, lbl in collide:
        c = d + dt.timedelta(days=1)
        while c in taken or c.weekday() >= 5: c += dt.timedelta(days=1)
        subs[c] = ("대체공휴일(%s 겹침)" % lbl, "sub_overlap", lbl); taken.add(c)
    res = [dict(date=d, name=n, key=k, sub=False, orig=None) for d, (n, k) in base.items()]
    res += [dict(date=d, name=n, key=k, sub=True, orig=o) for d, (n, k, o) in subs.items()]
    res.sort(key=lambda x: x["date"])
    return res

_raw_subs_cache = {}
_hol_cache = {}
def holiday_map(year):
    """date -> holiday dict, 전년·익년 경계 포함 (연말연초 대체공휴일이 이웃 해로 넘어가는 경우)"""
    if year not in _hol_cache:
        m = {}
        for y in (year - 1, year, year + 1):
            if y not in _hol_cache:
                pass
            for h in holidays_of(y):
                m[h["date"]] = h
        _hol_cache[year] = m
    return _hol_cache[year]

def holiday_on(d):
    return holiday_map(d.year).get(d)

# ── 손 없는 날·택일 ─────────────────────────────────
def is_sonnopneun(d):
    return lunar_of(d)[2] % 10 in (9, 0)

SAMGUNG = (5, 14, 23)  # 삼궁일(음력 5·14·23일)

PURPOSE = {
 "imsa":     dict(label="이사", good=("성","개","만","정"), bad=("파","폐"), need_son=True,  great=4, fine=3),
 "gyeolhon": dict(label="결혼", good=("만","성","개","정"), bad=("파","위"), need_son=False, great=3, fine=2),
 "gaeop":    dict(label="개업", good=("개","성","만","건"), bad=("파","폐"), need_son=False, great=3, fine=2),
}

def judge(d, purpose):
    """(등급, 점수, 사유목록) — 등급: 대길/길/보통/피함"""
    P = PURPOSE[purpose]
    ly, lm, ld, leap = lunar_of(d)
    sh = SHIN12[shin12_of_idx(d)]
    hw = hwangdo_of(d)
    son = ld % 10 in (9, 0)
    reasons = []; score = 0; avoid = False
    if ld in SAMGUNG:
        avoid = True; reasons.append("음력 %d일은 삼궁일(큰일을 피하는 날)" % ld)
    if sh in P["bad"]:
        avoid = True; reasons.append("건제 12신 ‘%s(%s)’일은 %s에 꺼리는 날" % (sh, SHIN12_H[SHIN12.index(sh)], P["label"]))
    if sh in P["good"]:
        score += 2; reasons.append("건제 12신 ‘%s(%s)’일은 %s에 길한 날" % (sh, SHIN12_H[SHIN12.index(sh)], P["label"]))
    if hw in HWANGDO_GOOD:
        score += 1; reasons.append("황도일(%s)" % hw)
    else:
        reasons.append("흑도일(%s)" % hw)
    if son:
        score += 2 if P["need_son"] else 1
        reasons.append("손 없는 날(음력 %d일)" % ld)
    elif P["need_son"]:
        score -= 1
    if avoid: return "피함", score - 10, reasons
    good_sh = sh in P["good"]; good_hw = hw in HWANGDO_GOOD
    if good_sh and ((son) if P["need_son"] else good_hw): return "대길", score, reasons
    if good_sh or (good_hw and son): return "길", score, reasons
    return "보통", score, reasons

def selftest():
    assert ganzhi(day_index(dt.date(2000,1,1))) == "무오", ganzhi(day_index(dt.date(2000,1,1)))
    print("selftest ok")

if __name__ == "__main__":
    selftest()
