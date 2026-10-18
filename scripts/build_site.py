# -*- coding: utf-8 -*-
"""우아달력 정적 사이트 생성기.  사용: python scripts/build_site.py  (wooacal 루트에 결과 생성)"""
import sys, json, shutil, datetime as dt
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *
import content as C
import engine as E

D1 = dt.timedelta(days=1)
GRADE_CLS = {"대길": "daegil", "길": "gil", "보통": "", "피함": "bad"}
PURP = {
    "imsa": dict(slug="imsa", label="이사", full="이사", hero="🚚", verb="이사하기 좋은 날"),
    "gyeolhon": dict(slug="gyeolhon", label="결혼", full="결혼식", hero="💍", verb="결혼식 날짜로 좋은 날"),
    "gaeop": dict(slug="gaeop", label="개업", full="개업", hero="🏪", verb="개업하기 좋은 날"),
}

def tag(text, cls=""): return '<span class="tag %s">%s</span>' % (cls, esc(text))
def link(u, t): return '<a href="%s">%s</a>' % (u, esc(t))

def date_link(d, with_year=False):
    if d.year not in YEARS:
        return esc(fmtw(d, True))
    return link(url_date(d), fmtw(d, with_year) if with_year else "%d월 %d일(%s)" % (d.month, d.day, wd(d)))

def day_tags(i):
    t = []
    if i["hol"]: t.append(tag(i["hol"]["name"], "hol"))
    if i["term"]: t.append(tag(i["term"]["name"], "term"))
    if i["son"]: t.append(tag("손 없는 날", "son"))
    return " ".join(t)

# ───────────────────────── 달력 격자 ─────────────────────────
def month_grid(y, m):
    first = dt.date(y, m, 1)
    last = (dt.date(y + (m == 12), m % 12 + 1, 1) - D1)
    lead = (first.weekday() + 1) % 7      # 일요일 시작
    cells = [None] * lead + [first + dt.timedelta(days=k) for k in range(last.day)]
    while len(cells) % 7: cells.append(None)
    heads = "".join('<th class="%s">%s</th>' % (c, n) for c, n in zip(["sun", "", "", "", "", "", "sat"], "일월화수목금토"))
    rows = []
    for r in range(0, len(cells), 7):
        tds = []
        for c, d in enumerate(cells[r:r + 7]):
            if d is None:
                tds.append('<td class="empty"></td>'); continue
            i = info(d)
            cls = ["sun" if c == 0 else "sat" if c == 6 else ""]
            if i["hol"]: cls.append("hol")
            lu = ("%s%d.1" % ("윤" if i["leap"] else "", i["lm"])) if i["ld"] == 1 else str(i["ld"])
            ev = ""
            if i["hol"]: ev += '<span class="ev">%s</span>' % esc(i["hol"]["name"].replace("대체공휴일", "대체"))
            if i["term"]: ev += '<span class="ev t">%s</span>' % i["term"]["name"]
            sb = '<span class="sb">손</span>' if i["son"] else ""
            tds.append('<td class="%s"><a class="cell" href="%s">%s<span class="dn">%d</span><span class="lu">음 %s</span>%s</a></td>'
                       % (" ".join(cls), url_date(d), sb, d.day, lu, ev))
        rows.append("<tr>%s</tr>" % "".join(tds))
    return ('<div class="tbl-wrap"><table class="cal-grid"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
            '<div class="legend"><span><b class="red">빨강</b> 공휴일·일요일</span><span><b class="blue">파랑</b> 토요일·24절기</span>'
            '<span><b class="amber">손</b> 손 없는 날</span><span>숫자 아래 ‘음’ = 음력 날짜</span></div>') % (heads, "".join(rows))

# ───────────────────────── 연차 계획 ─────────────────────────
def span_txt(a, b, y):
    fa = fmtw(a, a.year != y); fb = fmtw(b, b.year != y)
    return "%s ~ %s" % (fa, fb)

def leave_plans(y, ks=(1, 2, 3, 4, 5)):
    a, b = dt.date(y, 1, 1), dt.date(y, 12, 31)
    days = list(daterange(a - dt.timedelta(days=10), b + dt.timedelta(days=10)))
    off = [info(d)["off"] for d in days]
    n = len(days)
    res = {}
    for k in ks:
        cands = []
        i = 0
        for s in range(n):
            if not off[s] or (s > 0 and off[s - 1]): continue          # 휴일 연속의 시작에서만
            used, e = 0, s
            j = s
            while j < n:
                if off[j]:
                    e = j
                else:
                    if used == k: break
                    used += 1
                j += 1
            # j-1 이 마지막으로 포함 가능한 날 → 끝이 휴일이어야 함
            while e >= s and not off[e]: e -= 1
            if used < k: continue
            end = e
            while end + 1 < n and off[end + 1]: end += 1
            # 윈도우 [s, end] 에서 평일 수 == k 가 되도록 끝 다듬기
            wk = sum(1 for t in range(s, end + 1) if not off[t])
            if wk != k: continue
            if not (a <= days[s] <= b or a <= days[end] <= b): continue
            has_hol = any(info(days[t])["hol"] for t in range(s, end + 1))
            if not has_hol: continue
            cands.append((end - s + 1, days[s], days[end], [days[t] for t in range(s, end + 1) if not off[t]]))
        cands.sort(key=lambda x: (-x[0], x[1]))
        pick, used_days = [], set()
        for c in cands:
            rng = set(daterange(c[1], c[2]))
            if rng & used_days: continue
            pick.append(c); used_days |= rng
            if len(pick) >= 3: break
        res[k] = pick
    return res

# ───────────────────────── 공휴일 요약 ─────────────────────────
def year_stats(y):
    hs = E.holidays_of(y)
    non_sun = [h for h in hs if h["date"].weekday() != 6]
    sat = [h for h in hs if h["date"].weekday() == 5]
    subs = [h for h in hs if h["sub"]]
    days_off = sum(1 for d in daterange(dt.date(y, 1, 1), dt.date(y, 12, 31)) if info(d)["off"])
    return dict(hs=hs, n=len(hs), real=len(non_sun), sun=len(hs) - len(non_sun), sat=len(sat), subs=subs, off=days_off)

def blocks_of_year(y):
    seen, out = set(), []
    for h in E.holidays_of(y):
        d = h["date"]
        if d in seen: continue
        a, b = off_block(d)
        for x in daterange(a, b): seen.add(x)
        n = (b - a).days + 1
        names = []
        for x in daterange(a, b):
            hh = info(x)["hol"]
            if hh:
                nm = hh["orig"] if hh["sub"] else hh["name"]
                nm = nm.split(" · ")[0].replace("설날 연휴", "설날").replace("추석 연휴", "추석")
                if nm not in names: names.append(nm)
        out.append((a, b, n, names))
    return out

def holiday_groups(y):
    """key -> [dates] (연휴/대체 포함), main date"""
    g = {}
    for h in E.holidays_of(y):
        k = h["key"].replace("sub_", "")
        g.setdefault(k, []).append(h)
    return g

def main_date(y, key):
    g = holiday_groups(y).get(key)
    if not g: return None
    for h in g:
        if not h["sub"] and h["name"].split(" · ")[0] in (C.HINFO[key]["name"],): return h["date"]
    for h in g:
        if not h["sub"]: return h["date"]
    return g[0]["date"]

# ───────────────────────── 연간 공휴일 페이지 ─────────────────────────
def page_year(y):
    st = year_stats(y)
    hs = st["hs"]
    blocks = blocks_of_year(y)
    longest = max(blocks, key=lambda x: (x[2], -x[0].toordinal()))
    path = "/%d/" % y
    # 표
    rows = []
    for h in hs:
        d = h["date"]; i = info(d)
        key = h["key"].replace("sub_", "")
        nm = h["name"]
        nm_html = esc(nm)
        if key in C.HINFO and main_date(y, key): nm_html = link("/%d/%s/" % (y, key), nm)
        note = ""
        if h["sub"]: note = "%s이(가) 주말·다른 공휴일과 겹쳐 지정" % h["orig"]
        elif d.weekday() == 6: note = "일요일과 겹침" + ("" if key in ("hyunchung", "sinjeong") else "(대체공휴일 있음)" if C.HINFO.get(key, {}).get("sub") else "")
        elif d.weekday() == 5: note = "토요일과 겹침"
        rows.append("<tr><td>%s</td><td class=\"%s\">%s</td><td>%s</td><td>%s</td></tr>" % (
            link(url_date(d), "%d월 %d일" % (d.month, d.day)), "red" if d.weekday() == 6 else "blue" if d.weekday() == 5 else "",
            wd(d), nm_html, esc(note)))
    t1 = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>날짜</th><th>요일</th><th>공휴일</th><th>비고</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(rows)
    # 연휴
    long_blocks = [b for b in blocks if b[2] >= 3]
    brow = "".join('<tr%s><td>%s ~ %s</td><td><b>%d일</b></td><td>%s</td></tr>' % (
        ' class="hl"' if b is longest else "", fmtw(b[0], False), fmtw(b[1], False), b[2], esc(" · ".join(b[3]))) for b in long_blocks)
    t2 = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>연휴 기간</th><th>쉬는 날</th><th>포함된 공휴일</th></tr></thead><tbody>%s</tbody></table></div>' % brow
    # 연차
    lp = leave_plans(y)
    prow = []
    for k in sorted(lp):
        for c in lp[k][:2]:
            prow.append("<tr><td>연차 <b>%d일</b></td><td><b>%d일</b> 연휴</td><td>%s</td><td>%s</td></tr>" % (
                k, c[0], span_txt(c[1], c[2], y), esc(", ".join("%d/%d(%s)" % (x.month, x.day, wd(x)) for x in c[3]))))
    t3 = ('<div class="tbl-wrap"><table class="tbl"><thead><tr><th>쓰는 연차</th><th>연휴 길이</th><th>기간</th><th>연차 낼 날</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(prow)) if prow else ""
    # 월별
    mrow = []
    for m in range(1, 13):
        ds = list(daterange(dt.date(y, m, 1), dt.date(y + (m == 12), m % 12 + 1, 1) - D1))
        hol = [d for d in ds if info(d)["hol"] and d.weekday() < 5]
        wk = [d for d in ds if d.weekday() < 5]
        mrow.append("<tr><td>%s</td><td>%d일</td><td>%d일</td><td>%d일</td><td>%s</td></tr>" % (
            link("/%d/%02d/" % (y, m), "%d월 달력" % m), len([d for d in ds if info(d)["hol"]]), len(hol), len(wk) - len(hol),
            esc(", ".join(info(d)["hol"]["name"].replace("대체공휴일", "대체") for d in ds if info(d)["hol"]) or "-")))
    t4 = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>월</th><th>공휴일</th><th>평일에 쉬는 날</th><th>근무일수</th><th>공휴일 이름</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(mrow)
    prev = E.holidays_of(y - 1) if y - 1 >= 2025 else None
    cmp_txt = ""
    if y - 1 in YEARS:
        ps = year_stats(y - 1)
        diff = st["real"] - ps["real"]
        cmp_txt = " 전년(%d년)의 실질 휴일 %d일과 비교하면 %s." % (y - 1, ps["real"], "같습니다" if diff == 0 else "%d일 %s" % (abs(diff), "더 많습니다" if diff > 0 else "더 적습니다"))
    sub_txt = ", ".join("%d월 %d일(%s) %s" % (h["date"].month, h["date"].day, wd(h["date"]), h["name"].replace("대체공휴일", "").strip("()") or "") for h in st["subs"])
    lead = ("<p class=\"lead\"><b>%d년 관공서 공휴일은 모두 %d일</b>입니다(일요일과 겹치는 날 포함). 이 중 일요일과 겹치는 %d일을 빼면 평일·토요일에 실제로 쉬는 공휴일은 <b>%d일</b>이며, "
            "대체공휴일은 <b>%d일</b> 포함돼 있습니다%s.%s 가장 긴 연휴는 <b>%s ~ %s, %d일</b>(%s)입니다. 주 5일 근무자는 주말을 포함해 1년에 <b>%d일</b>을 쉽니다.</p>") % (
        y, st["n"], st["sun"], st["real"], len(st["subs"]), (" — %s" % sub_txt) if sub_txt else "", cmp_txt,
        fmtw(longest[0], False), fmtw(longest[1], False), longest[2], " · ".join(longest[3]), st["off"])
    stats = ('<div class="stat-row"><div class="stat"><small>관공서 공휴일</small><b>%d일</b></div><div class="stat"><small>실질 공휴일(일요일 제외)</small><b>%d일</b></div>'
             '<div class="stat"><small>대체공휴일</small><b>%d일</b></div><div class="stat"><small>최장 연휴</small><b>%d일</b></div><div class="stat"><small>총 쉬는 날(주말 포함)</small><b>%d일</b></div></div>') % (
        st["n"], st["real"], len(st["subs"]), longest[2], st["off"])
    nxt = ""
    chips = "".join('<a class="chip%s" href="/%d/">%d년</a>' % (" on" if yy == y else "", yy, yy) for yy in YEARS)
    mchips = "".join('<a class="chip" href="/%d/%02d/">%d월</a>' % (y, m, m) for m in range(1, 13))
    hchips = "".join('<a class="chip" href="/%d/%s/">%s</a>' % (y, k, C.HINFO[k]["name"]) for k in C.HORDER if main_date(y, k))
    extra = ""
    if y >= 2026:
        extra = "2026년부터 제헌절(7월 17일)과 노동절(5월 1일)도 법정공휴일에 포함돼 해당 연도부터 목록에 반영했습니다. "
    body = """
<div class="page-head"><h1>%(y)d년 공휴일·대체공휴일 총정리</h1>
<p>법정공휴일 %(n)d일 · 연휴 · 연차 쓰는 법 · 월별 근무일수</p></div>
<div class="chips">%(chips)s</div>
%(lead)s
%(stats)s
%(ad)s
<h2 class="group-title">📌 %(y)d년 공휴일 전체 목록</h2>
%(t1)s
<p class="note">%(extra)s대체공휴일은 설날·추석 연휴가 일요일 또는 다른 공휴일과 겹칠 때, 그리고 어린이날과 삼일절·광복절·개천절·한글날·부처님오신날·성탄절(2026년부터 노동절·제헌절 포함)이 토·일요일 또는 다른 공휴일과 겹칠 때 적용합니다. 신정과 현충일은 대체공휴일이 없습니다. 임시공휴일은 정부가 지정해 발표하면 반영합니다.</p>
<h2 class="group-title">🏖️ %(y)d년 3일 이상 연휴 <small>토·일요일과 이어지는 구간</small></h2>
%(t2)s
<h2 class="group-title">🗓️ 연차 쓰고 더 길게 쉬는 법 <small>%(y)d년 기준 추천</small></h2>
<p class="lead">공휴일 사이에 평일이 끼어 있으면 연차를 조금만 써도 연휴가 크게 늘어납니다. 아래는 %(y)d년에 연차 1~5일을 썼을 때 가장 길게 쉴 수 있는 구간입니다.</p>
%(t3)s
%(ad)s
<h2 class="group-title">📅 월별 공휴일·근무일수</h2>
%(t4)s
<h2 class="group-title">🔎 더 자세히 보기</h2>
<div class="chips">%(hchips)s</div>
<div class="chips">%(mchips)s</div>
<div class="chips"><a class="chip" href="/jeolgi/%(y)d/">%(y)d년 24절기</a><a class="chip" href="/sonnopneun-nal/%(y)d/">%(y)d년 손 없는 날</a><a class="chip" href="/imsa/%(y)d/">%(y)d년 이사 길일</a><a class="chip" href="/gyeolhon/%(y)d/">%(y)d년 결혼 길일</a><a class="chip" href="/umnyeok/%(y)d/">%(y)d년 음력</a></div>
""" % dict(y=y, n=st["n"], chips=chips, lead=lead, stats=stats, ad=ad(), t1=t1, t2=t2, t3=t3, t4=t4, hchips=hchips, mchips=mchips, extra=extra)
    faq = [
        ("%d년 대체공휴일은 며칠인가요?" % y, "%d년 대체공휴일은 %d일입니다.%s" % (y, len(st["subs"]), (" " + sub_txt + ".") if sub_txt else " 올해는 토·일요일이나 다른 공휴일과 겹쳐 대체공휴일이 생기는 날이 없습니다.")),
        ("%d년 가장 긴 연휴는 언제인가요?" % y, "%s ~ %s, 모두 %d일 연휴로 %s이(가) 포함됩니다. 연차를 쓰면 더 길게 쉴 수 있는 구간은 위 ‘연차 쓰고 더 길게 쉬는 법’ 표를 참고하세요." % (fmtw(longest[0], False), fmtw(longest[1], False), longest[2], " · ".join(longest[3]))),
        ("임시공휴일이 새로 생기면 어떻게 되나요?", "임시공휴일은 정부가 국무회의 의결로 지정하며, 지정되면 달력과 연휴 계산이 달라집니다. 이 페이지는 발표된 공휴일만 반영하므로 새로 발표되면 갱신합니다. 정확한 내용은 정부 공고와 우주항공청·한국천문연구원 월력요항으로 확인하세요."),
        ("일요일과 겹친 공휴일은 쉬는 날이 더 생기나요?", "설날·추석 연휴와 어린이날, 삼일절·광복절·개천절·한글날·부처님오신날·성탄절(2026년부터 노동절·제헌절도)은 토·일요일이나 다른 공휴일과 겹치면 다음 평일을 대체공휴일로 쉽니다. 신정과 현충일은 겹쳐도 대체공휴일이 없습니다."),
    ]
    write(path, layout(path, "%d년 공휴일·대체공휴일 총정리 (연휴·달력)" % y,
        "%d년 공휴일 %d일(실질 %d일), 대체공휴일 %d일, 최장 연휴 %d일. 설날·추석 날짜, 3일 이상 연휴, 연차 쓰는 법, 월별 근무일수를 한눈에 정리했습니다." % (y, st["n"], st["real"], len(st["subs"]), longest[2]),
        body, faq, [("홈", "/"), ("%d년 공휴일" % y, path)], coupang=True), "0.9")

# ───────────────────────── 개별 공휴일 페이지 ─────────────────────────
def page_holiday(y, key):
    H = C.HINFO[key]
    md = main_date(y, key)
    if not md: return
    g = holiday_groups(y)[key]
    dates = sorted(h["date"] for h in g)
    a, b = off_block(md)
    n_off = (b - a).days + 1
    sub = [h for h in g if h["sub"]]
    nm = H["name"]
    path = "/%d/%s/" % (y, key)
    i = info(md)
    lun = "음력 %s" % i["lunar_str"]
    # 연도별 비교표
    crow = []
    for yy in YEARS:
        m2 = main_date(yy, key)
        if not m2: continue
        a2, b2 = off_block(m2)
        gs = [h for h in holiday_groups(yy)[key] if h["sub"]]
        crow.append('<tr%s><td>%s</td><td>%s</td><td>%s</td><td>%d일</td><td>%s</td></tr>' % (
            ' class="hl"' if yy == y else "", link("/%d/%s/" % (yy, key), "%d년" % yy), esc(fmtw(m2, False)), esc("음력 " + info(m2)["lunar_str"]),
            (b2 - a2).days + 1, esc(("대체공휴일 " + ", ".join("%d/%d" % (h["date"].month, h["date"].day) for h in gs)) if gs else "-")))
    tcmp = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>연도</th><th>날짜</th><th>음력</th><th>연휴 길이</th><th>대체공휴일</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(crow)
    # 연휴 구성
    comp = []
    for x in daterange(a, b):
        ix = info(x)
        label = ix["hol"]["name"] if ix["hol"] else ("토요일" if x.weekday() == 5 else "일요일")
        comp.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (date_link(x), wd(x), esc(label)))
    tcomp = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>날짜</th><th>요일</th><th>구분</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(comp)
    base_dates = sorted(h["date"] for h in g if not h["sub"] and h["key"] == key)
    lun_txt = "음력 %s" % i["lunar_str"]
    if H["lunar"] and len(base_dates) >= 3:
        span = "%s ~ %s" % (fmtw(base_dates[0], False), fmtw(base_dates[-1], False))
        what = "연휴는 <b>%s</b>(3일)입니다" % span
        faq_date = "%s이고 %s입니다. 연휴는 %s입니다" % (fmtw(md, True), lun_txt, span)
    else:
        what = ""
        faq_date = "%s입니다(%s)" % (fmtw(md, True), lun_txt)
    sub_sent = ""
    if sub:
        sub_sent = " %s과 겹쳐 %s이(가) 대체공휴일로 지정됩니다." % ("주말" if md.weekday() >= 5 else "다른 공휴일", ", ".join(fmtw(h["date"], False) for h in sub))
        if H["lunar"]: sub_sent = " 연휴 중 일요일 또는 다른 공휴일이 겹쳐 %s이(가) 대체공휴일로 지정됩니다." % ", ".join(fmtw(h["date"], False) for h in sub)
    elif md.weekday() >= 5 and not H["sub"]:
        sub_sent = " %s요일과 겹치지만 %s은(는) 대체공휴일이 적용되지 않아 다른 날에 따로 쉬지 않습니다." % (wd(md), nm)
    free = ""
    if n_off != len(dates):
        free = " 앞뒤 주말까지 이어지면 <b>%s ~ %s, 총 %d일</b>을 쉬게 됩니다." % (fmtw(a, False), fmtw(b, False), n_off)
    if H["lunar"]:
        lead = "<p class=\"lead\"><b>%d년 %s</b>은(는) <b>%s</b>이고 %s입니다.%s%s%s</p>" % (y, nm, fmtw(md, False), lun_txt, (" " + what + ".") if what else "", sub_sent, free)
    else:
        lead = "<p class=\"lead\"><b>%d년 %s</b>은(는) <b>%s</b>입니다(%s). 음력으로는 %s입니다.%s%s</p>" % (y, nm, fmtw(md, False), H["rule"], i["lunar_str"], sub_sent, free)
    stats = ('<div class="stat-row"><div class="stat"><small>날짜</small><b>%d.%d(%s)</b></div><div class="stat"><small>연휴 길이</small><b>%d일</b></div>'
             '<div class="stat"><small>오늘로부터</small><b id="dd" data-date="%s">-</b></div><div class="stat"><small>연차 필요</small><b>%s</b></div></div>') % (
        md.month, md.day, wd(md), n_off, md.isoformat(), "없음" if n_off >= 3 else "1~2일 쓰면 연장")
    lp = leave_plans(y)
    mine = []
    for k in lp:
        for c in lp[k]:
            if c[1] <= md <= c[2] or any(c[1] <= x <= c[2] for x in dates):
                mine.append((k, c))
    plan_html = ""
    if mine:
        plan_html = "<h2 class=\"group-title\">🏖️ 연차를 쓰면 이렇게 쉴 수 있어요</h2><div class=\"tbl-wrap\"><table class=\"tbl\"><thead><tr><th>쓰는 연차</th><th>연휴 길이</th><th>기간</th><th>연차 낼 날</th></tr></thead><tbody>%s</tbody></table></div>" % "".join(
            "<tr><td>연차 <b>%d일</b></td><td><b>%d일</b></td><td>%s</td><td>%s</td></tr>" % (k, c[0], span_txt(c[1], c[2], y), esc(", ".join("%d/%d(%s)" % (x.month, x.day, wd(x)) for x in c[3]))) for k, c in mine[:4])
    paras = "".join("<p class=\"lead\">%s</p>" % esc(p) for p in H["paras"])
    body = """
<div class="page-head"><h1>%(y)d년 %(nm)s 언제? %(md)s</h1><p>%(rule)s · 연휴 %(n)d일 · 대체공휴일 %(subtxt)s</p></div>
<div class="chips">%(chips)s</div>
%(lead)s
%(stats)s
%(ad)s
<h2 class="group-title">📅 %(y)d년 %(nm)s 연휴 일정</h2>
%(tcomp)s
%(plan)s
<h2 class="group-title">📖 %(nm)s이란?</h2>
%(paras)s
<h2 class="group-title">🔁 연도별 %(nm)s 날짜 비교</h2>
%(tcmp)s
<div class="chips"><a class="chip" href="/%(y)d/">%(y)d년 공휴일 전체</a><a class="chip" href="%(mlink)s">%(m)d월 달력</a></div>
<script src="/assets/js/dday.js"></script>
""" % dict(y=y, nm=nm, md=fmtw(md, False), rule=H["rule"], n=n_off, subtxt=("%d일 있음" % len(sub)) if sub else "없음",
           chips="".join('<a class="chip%s" href="/%d/%s/">%d년</a>' % (" on" if yy == y else "", yy, key, yy) for yy in YEARS if main_date(yy, key)),
           lead=lead, stats=stats, ad=ad(), tcomp=tcomp, plan=plan_html, paras=paras, tcmp=tcmp, mlink="/%d/%02d/" % (y, md.month), m=md.month)
    faq = [
        ("%d년 %s은 몇 월 며칠인가요?" % (y, nm), "%d년 %s은 %s." % (y, nm, faq_date)),
        ("%d년 %s 연휴는 며칠인가요?" % (y, nm), "공휴일과 주말을 이어 %s ~ %s, 총 %d일을 쉽니다.%s" % (fmtw(a, False), fmtw(b, False), n_off, " 대체공휴일이 포함돼 있습니다." if sub else "")),
        ("%s은 대체공휴일이 적용되나요?" % nm, ("네. 토·일요일 또는 다른 공휴일과 겹치면 다음 첫 평일이 대체공휴일입니다." if H["sub"] else "아니요. %s은(는) 대체공휴일 적용 대상이 아니라 주말과 겹쳐도 다른 날에 쉬지 않습니다." % nm)),
    ]
    write(path, layout(path, "%d년 %s 언제? %s%s" % (y, nm, fmtw(md, False), (" 연휴 %d일" % n_off) if n_off >= 2 else ""),
        "%d년 %s은 %s, 음력 %s. %s대체공휴일 %s. 연차 쓰는 법과 연도별 날짜를 정리했습니다." % (y, nm, fmtw(md, False), i["lunar_str"], ("연휴 %d일, " % n_off) if n_off >= 2 else "", ("%d일" % len(sub)) if sub else "없음"),
        body, faq, [("홈", "/"), ("%d년 공휴일" % y, "/%d/" % y), (nm, path)], coupang=False), "0.7")

# ───────────────────────── 월 달력 ─────────────────────────
def month_days(y, m):
    return list(daterange(dt.date(y, m, 1), dt.date(y + (m == 12), m % 12 + 1, 1) - D1))

def page_month(y, m):
    ds = month_days(y, m)
    path = "/%d/%02d/" % (y, m)
    hol = [d for d in ds if info(d)["hol"]]
    wk = [d for d in ds if d.weekday() < 5]
    work = len([d for d in wk if not info(d)["hol"]])
    sons = [d for d in ds if info(d)["son"]]
    terms = [t for t in E.terms_of_year(y) if t["at"].month == m]
    l1, l2 = info(ds[0]), info(ds[-1])
    lunar_rng = "음력 %s월 %d일 ~ %s월 %d일" % (("윤" if l1["leap"] else "") + str(l1["lm"]), l1["ld"], ("윤" if l2["leap"] else "") + str(l2["lm"]), l2["ld"])
    prev = (y, m - 1) if m > 1 else (y - 1, 12)
    nxt = (y, m + 1) if m < 12 else (y + 1, 1)
    nav = '<div class="nav-row">%s%s</div>' % (
        ('<a class="btn" href="/%d/%02d/">← %d년 %d월</a>' % (prev[0], prev[1], prev[0], prev[1])) if prev[0] in YEARS else "<span></span>",
        ('<a class="btn" href="/%d/%02d/">%d년 %d월 →</a>' % (nxt[0], nxt[1], nxt[0], nxt[1])) if nxt[0] in YEARS else "<span></span>")
    hrow = "".join("<tr><td>%s</td><td>%s</td></tr>" % (date_link(d), esc(info(d)["hol"]["name"])) for d in hol)
    hsec = ('<div class="tbl-wrap"><table class="tbl"><thead><tr><th>날짜</th><th>공휴일</th></tr></thead><tbody>%s</tbody></table></div>' % hrow) if hol else '<p class="lead">%d년 %d월에는 공휴일이 없습니다.</p>' % (y, m)
    trow = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
        link("/jeolgi/%s/" % C.TERM_INFO[t["name"]][0], "%s(%s)" % (t["name"], t["hanja"])), date_link(t["at"].date()),
        t["at"].strftime("%H:%M"), esc(C.TERM_INFO[t["name"]][1])) for t in terms)
    tsec = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>절기</th><th>날짜</th><th>시각(KST)</th><th>뜻</th></tr></thead><tbody>%s</tbody></table></div>' % trow
    srow = "".join("<tr><td>%s</td><td>음력 %s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
        date_link(d), info(d)["lunar_str"], info(d)["gz"], tag(E.judge(d, "imsa")[0], GRADE_CLS[E.judge(d, "imsa")[0]]),
        esc("공휴일: " + info(d)["hol"]["name"] if info(d)["hol"] else "주말" if d.weekday() >= 5 else "평일")) for d in sons)
    ssec = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>양력</th><th>음력</th><th>일진</th><th>이사 판정</th><th>구분</th></tr></thead><tbody>%s</tbody></table></div>' % srow
    picks = {}
    for p in PURP:
        gl = [(d, E.judge(d, p)[0]) for d in ds]
        picks[p] = [d for d, g in gl if g == "대길"]
    psec = "".join('<tr><td>%s</td><td>%s</td></tr>' % (link("/%s/%d/%02d/" % (p, y, m), PURP[p]["label"] + " 길일"),
                    " · ".join("%d일" % d.day for d in picks[p][:8]) or "없음") for p in PURP)
    psec = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>목적</th><th>%d월 대길일</th></tr></thead><tbody>%s</tbody></table></div>' % (m, psec)
    mid = ds[len(ds) // 2]
    lead = ("<p class=\"lead\"><b>%d년 %d월</b>은 %d일까지 있고 평일 %d일, 주말 %d일입니다. 공휴일이 평일에 %d일 있어 <b>근무일수는 %d일</b>입니다. %s에 해당하며, 손 없는 날은 <b>%s</b>입니다.%s</p>") % (
        y, m, len(ds), len(wk), len(ds) - len(wk), len([d for d in hol if d.weekday() < 5]), work, lunar_rng,
        ", ".join("%d일" % d.day for d in sons) or "없음",
        (" 이달의 24절기는 %s입니다." % ", ".join("%s(%d일)" % (t["name"], t["at"].day) for t in terms)) if terms else "")
    body = """
<div class="page-head"><h1>%(y)d년 %(m)d월 달력 — 음력·공휴일·손 없는 날</h1><p>%(lunar)s · 근무일수 %(work)d일 · 공휴일 %(hn)d일</p></div>
<div class="chips">%(mchips)s</div>
%(lead)s
%(grid)s
%(nav)s
%(ad)s
<h2 class="group-title">🎌 %(m)d월 공휴일</h2>
%(hsec)s
<h2 class="group-title">🌱 %(m)d월 24절기</h2>
%(tsec)s
<h2 class="group-title">🧭 %(m)d월 손 없는 날 <small>음력 9·10·19·20·29·30일</small></h2>
%(ssec)s
<p class="note">손 없는 날은 이사·결혼 등 큰일을 피하는 ‘손(귀신)’이 없는 날로 전해지는 풍습입니다. <a href="/sonnopneun-nal/%(y)d/%(m2)02d/">%(m)d월 손 없는 날 자세히</a></p>
%(ad)s
<h2 class="group-title">✨ %(m)d월 목적별 길일</h2>
%(psec)s
<div class="chips"><a class="chip" href="/%(y)d/">%(y)d년 공휴일 전체</a><a class="chip" href="/umnyeok/">음력 ↔ 양력 변환</a></div>
""" % dict(y=y, m=m, m2=m, lunar=lunar_rng, work=work, hn=len(hol), mchips="".join('<a class="chip%s" href="/%d/%02d/">%d월</a>' % (" on" if mm == m else "", y, mm, mm) for mm in range(1, 13)),
           lead=lead, grid=month_grid(y, m), nav=nav, ad=ad(), hsec=hsec, tsec=tsec, ssec=ssec, psec=psec)
    faq = [
        ("%d년 %d월 공휴일은 며칠인가요?" % (y, m), ("%d년 %d월 공휴일은 %s입니다." % (y, m, ", ".join("%d일(%s)" % (d.day, info(d)["hol"]["name"]) for d in hol))) if hol else "%d년 %d월에는 공휴일이 없습니다." % (y, m)),
        ("%d년 %d월 손 없는 날은 언제인가요?" % (y, m), "%s입니다. 음력 날짜의 끝자리가 9 또는 0인 날(9일·10일·19일·20일·29일·30일)이 손 없는 날입니다." % (", ".join("%d일(%s)" % (d.day, wd(d)) for d in sons) or "이달에는 없")),
        ("%d년 %d월 근무일수는 몇 일인가요?" % (y, m), "토·일요일과 평일에 있는 공휴일을 뺀 근무일수는 %d일입니다." % work),
    ]
    write(path, layout(path, "%d년 %d월 달력 — 음력·공휴일·손 없는 날·24절기" % (y, m),
        "%d년 %d월 달력. 음력 날짜, 공휴일 %d일, 24절기, 손 없는 날(%s), 근무일수 %d일과 이사·결혼·개업 길일을 한 번에 확인하세요." % (y, m, len(hol), ", ".join("%d일" % d.day for d in sons[:6]), work),
        body, faq, [("홈", "/"), ("%d년 공휴일" % y, "/%d/" % y), ("%d월 달력" % m, path)], coupang=False), "0.8")

# ───────────────────────── 24절기 ─────────────────────────
def page_jeolgi_year(y):
    path = "/jeolgi/%d/" % y
    rows = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
        link("/jeolgi/%s/" % C.TERM_INFO[t["name"]][0], "%s(%s)" % (t["name"], t["hanja"])),
        date_link(t["at"].date()), t["at"].strftime("%H시 %M분"), "절(節)" if t["kind"] == "절" else "중기(中氣)",
        esc("음력 " + info(t["at"].date())["lunar_str"])) for t in E.terms_of_year(y))
    t = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>절기</th><th>양력 날짜</th><th>시각(한국 표준시)</th><th>구분</th><th>음력</th></tr></thead><tbody>%s</tbody></table></div>' % rows
    ip, dj = E.terms_of_year(y)[2], E.terms_of_year(y)[23]
    chips = "".join('<a class="chip%s" href="/jeolgi/%d/">%d년</a>' % (" on" if yy == y else "", yy, yy) for yy in YEARS)
    body = """
<div class="page-head"><h1>%(y)d년 24절기 날짜·시각 (양력·음력)</h1><p>입춘 %(ip)s · 하지 · 동지 %(dj)s</p></div>
<div class="chips">%(chips)s</div>
<p class="lead"><b>%(y)d년 24절기</b>는 소한(1월 %(sohan)d일)에서 시작해 동지(12월 %(dj_d)d일)로 끝납니다. 절기는 태양이 황도 위에서 15도씩 움직이는 지점에 닿는 순간으로 정해지며, 아래 시각은 태양 시황경을 계산한 한국 표준시 기준입니다. 달력에는 날짜만 나오지만 입춘처럼 날짜가 바뀌는 시각이 중요한 절기도 있습니다.</p>
%(ad)s
%(t)s
<p class="note">절기 이름을 누르면 의미와 풍습, 연도별 날짜를 볼 수 있습니다. 입춘·경칩처럼 ‘절(節)’에 해당하는 12개는 사주의 월(月)을 가르는 기준이고, 나머지 12개는 ‘중기(中氣)’입니다.</p>
<h2 class="group-title">🔎 같이 보기</h2>
<div class="chips"><a class="chip" href="/%(y)d/">%(y)d년 공휴일</a><a class="chip" href="/umnyeok/%(y)d/">%(y)d년 음력</a><a class="chip" href="/%(y)d/01/">%(y)d년 달력</a><a class="chip" href="https://wooaunse.wooahouse.com/saju/">사주 만세력(우아운세)</a></div>
""" % dict(y=y, ip=fmtw(ip["at"].date(), False), dj=fmtw(dj["at"].date(), False), chips=chips, sohan=E.terms_of_year(y)[0]["at"].day, dj_d=dj["at"].day, ad=ad(), t=t)
    faq = [("%d년 입춘은 언제인가요?" % y, "%d년 입춘은 %s %s입니다." % (y, fmtw(ip["at"].date(), False), ip["at"].strftime("%H시 %M분"))),
           ("%d년 동지는 언제인가요?" % y, "%d년 동지는 %s %s이며 일 년 중 밤이 가장 긴 날입니다." % (y, fmtw(dj["at"].date(), False), dj["at"].strftime("%H시 %M분"))),
           ("24절기 날짜는 해마다 왜 조금씩 다른가요?", "절기는 태양의 위치로 정해지는데 지구가 태양을 도는 데 365.24일이 걸려 양력 날짜가 하루 안팎으로 달라집니다. 윤년이 4년마다 이를 보정합니다.")]
    write(path, layout(path, "%d년 24절기 날짜·시각 (입춘·하지·동지)" % y,
        "%d년 24절기 양력 날짜와 시각, 음력 날짜. 입춘 %s, 하지 %s, 동지 %s를 비롯한 24절기 전체를 표로 정리했습니다." % (y, fmt(ip["at"].date(), False), fmt(E.terms_of_year(y)[11]["at"].date(), False), fmt(dj["at"].date(), False)),
        body, faq, [("홈", "/"), ("24절기", "/jeolgi/"), ("%d년" % y, path)], coupang=False), "0.8")

def page_jeolgi_term(name):
    slug, mean, season, custom = C.TERM_INFO[name]
    t0 = [t for t in E.terms_of_year(YEARS[0]) if t["name"] == name][0]
    path = "/jeolgi/%s/" % slug
    rows = ""
    for y in YEARS:
        t = [x for x in E.terms_of_year(y) if x["name"] == name][0]
        rows += "<tr><td>%d년</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (y, date_link(t["at"].date()), t["at"].strftime("%H시 %M분"), esc("음력 " + info(t["at"].date())["lunar_str"]))
    tbl = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>연도</th><th>양력 날짜</th><th>시각(KST)</th><th>음력</th></tr></thead><tbody>%s</tbody></table></div>' % rows
    idx = E.TERMS.index([x for x in E.TERMS if x[0] == name][0])
    prv, nx = E.TERMS[(idx - 1) % 24][0], E.TERMS[(idx + 1) % 24][0]
    t27 = [x for x in E.terms_of_year(YEARS[1]) if x["name"] == name][0]
    body = """
<div class="page-head"><h1>%(n)s(%(h)s) — %(y)d년 %(d)s</h1><p>24절기 · %(season)s · 태양 시황경 %(lon)d°</p></div>
<p class="lead"><b>%(n)s(%(h)s)</b>은(는) 24절기 중 %(kind)s에 해당하며 태양 시황경이 <b>%(lon)d도</b>가 되는 순간입니다. %(mean)s %(y)d년에는 <b>%(d)s %(tm)s</b>입니다.</p>
%(ad)s
<h2 class="group-title">📅 연도별 %(n)s 날짜</h2>
%(tbl)s
<h2 class="group-title">🌤️ 계절과 날씨</h2><p class="lead">%(season_txt)s</p>
<h2 class="group-title">🎎 풍습</h2><p class="lead">%(custom)s</p>
<div class="nav-row"><a class="btn" href="/jeolgi/%(ps)s/">← %(pn)s</a><a class="btn" href="/jeolgi/%(ns)s/">%(nn)s →</a></div>
<div class="chips"><a class="chip" href="/jeolgi/">24절기 전체</a><a class="chip" href="/jeolgi/%(y)d/">%(y)d년 24절기</a></div>
""" % dict(n=name, h=t0["hanja"], y=YEARS[1], d=fmtw(t27["at"].date(), False), tm=t27["at"].strftime("%H시 %M분"), season=C.SEASON[name], lon=t0["lon"],
           kind="‘절(節)’" if t0["kind"] == "절" else "‘중기(中氣)’", mean=mean, ad=ad(), tbl=tbl, season_txt=season, custom=custom,
           ps=C.TERM_INFO[prv][0], pn=prv, ns=C.TERM_INFO[nx][0], nn=nx)
    faq = [("%s은 언제인가요?" % name, "%d년 %s은 %s %s입니다. 해마다 하루 안팎으로 달라집니다." % (YEARS[1], name, fmtw(t27["at"].date(), False), t27["at"].strftime("%H시 %M분"))),
           ("%s은 무슨 뜻인가요?" % name, mean),
           ("%s에는 무엇을 하나요?" % name, custom)]
    write(path, layout(path, "%s(%s) 언제? %d년 %s %s" % (name, t0["hanja"], YEARS[1], fmt(t27["at"].date(), False), t27["at"].strftime("%H:%M")),
        "%s(%s)의 뜻과 풍습, %d~%d년 날짜와 시각. %d년 %s은 %s입니다." % (name, t0["hanja"], YEARS[0], YEARS[-1], YEARS[1], name, fmtw(t27["at"].date(), False)),
        body, faq, [("홈", "/"), ("24절기", "/jeolgi/"), (name, path)], coupang=False), "0.6")

def page_jeolgi_index():
    y = YEARS[1]
    rows = "".join('<a class="card" href="/jeolgi/%s/"><b>%s(%s)</b><span>%d년 %s · %s</span></a>' % (
        C.TERM_INFO[t["name"]][0], t["name"], t["hanja"], y, fmt(t["at"].date(), False), t["at"].strftime("%H:%M")) for t in E.terms_of_year(y))
    body = """
<div class="page-head"><h1>24절기 — 날짜·뜻·풍습 총정리</h1><p>입춘부터 대한까지, 연도별 양력 날짜와 시각</p></div>
<p class="lead">24절기는 태양이 황도를 따라 움직이는 위치를 15도씩 24등분해 계절의 변화를 나타낸 것입니다. 달의 모양을 따르는 음력과 달리 <b>태양의 위치</b>로 정해져서 양력 날짜가 해마다 크게 바뀌지 않습니다. 연도를 골라 날짜와 시각을 확인하거나 절기 이름을 눌러 뜻과 풍습을 읽어 보세요.</p>
<div class="chips">%(chips)s</div>
%(ad)s
<h2 class="group-title">🌿 %(y)d년 24절기 <small>이름을 누르면 상세</small></h2>
<div class="card-grid">%(rows)s</div>
""" % dict(chips="".join('<a class="chip" href="/jeolgi/%d/">%d년 24절기</a>' % (yy, yy) for yy in YEARS), ad=ad(), y=y, rows=rows)
    faq = [("24절기는 무엇인가요?", "태양의 황경이 15도 변할 때마다 하나씩, 1년을 24개로 나눈 계절 구분입니다. 입춘에서 시작해 대한으로 끝납니다."),
           ("절기와 음력은 어떻게 다른가요?", "음력은 달의 위상으로 달을 정하고 절기는 태양의 위치로 정합니다. 그래서 절기는 양력 날짜가 거의 고정되고 음력 날짜는 해마다 달라집니다."),
           ("‘절(節)’과 ‘중기(中氣)’는 무엇인가요?", "24절기 가운데 입춘·경칩·청명처럼 각 달의 시작을 알리는 12개를 절, 우수·춘분·곡우처럼 달의 가운데에 오는 12개를 중기라고 합니다. 사주에서는 절이 월을 나눕니다.")]
    write("/jeolgi/", layout("/jeolgi/", "24절기 날짜·뜻·풍습 총정리 (입춘~대한)", "24절기 전체 이름, 뜻, 풍습과 %d~%d년 양력 날짜·시각을 정리했습니다. 입춘·하지·동지가 언제인지 바로 확인하세요." % (YEARS[0], YEARS[-1]),
        body, faq, [("홈", "/"), ("24절기", "/jeolgi/")]), "0.8")

# ───────────────────────── 손 없는 날 / 목적별 길일 ─────────────────────────
SON_EXPLAIN = """<p class="lead"><b>손 없는 날</b>은 이사나 결혼, 개업처럼 중요한 일을 앞두고 사람들이 가장 먼저 찾는 날입니다. 여기서 ‘손’은 사람의 일을 방해한다고 믿어 온 귀신(악귀)을 뜻합니다. 손은 음력 날짜에 따라 움직이는 방향이 정해져 있다고 전해집니다. 음력 1·2일은 동쪽, 3·4일은 남쪽, 5·6일은 서쪽, 7·8일은 북쪽에 있고 <b>9일과 10일(그리고 19·20·29·30일)</b>은 손이 하늘로 올라가 쉬는 날이라 어느 방향으로 움직여도 방해받지 않는다고 봅니다.</p>"""

def page_son_year(y):
    path = "/sonnopneun-nal/%d/" % y
    rows = ""
    cnt = 0; wkend = 0
    for m in range(1, 13):
        ds = [d for d in month_days(y, m) if info(d)["son"]]
        cnt += len(ds); wkend += len([d for d in ds if d.weekday() >= 5])
        rows += "<tr><td>%s</td><td>%s</td><td>%d일</td></tr>" % (link("/sonnopneun-nal/%d/%02d/" % (y, m), "%d월" % m),
            " ".join(('<a href="%s" class="%s">%d일(%s)</a>' % (url_date(d), "red" if d.weekday() == 6 else "blue" if d.weekday() == 5 else "", d.day, wd(d))) for d in ds), len([d for d in ds if d.weekday() >= 5]))
    t = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>월</th><th>손 없는 날</th><th>주말</th></tr></thead><tbody>%s</tbody></table></div>' % rows
    body = """
<div class="page-head"><h1>%(y)d년 손 없는 날 달력 (월별 전체)</h1><p>음력 9·10·19·20·29·30일 · 총 %(c)d일 · 주말 %(w)d일</p></div>
<div class="chips">%(chips)s</div>
<p class="lead"><b>%(y)d년 손 없는 날은 모두 %(c)d일</b>이고 이 중 주말(토·일)에 걸린 날이 %(w)d일, 평일이 %(p)d일입니다. 이사 업체는 손 없는 날, 특히 주말과 월말에 예약이 몰려 비용이 오르는 경향이 있어 평일 손 없는 날을 고르면 비용과 예약 부담을 줄이기 쉽습니다.</p>
%(ad)s
%(t)s
<h2 class="group-title">❓ 손 없는 날이란?</h2>%(ex)s
<div class="chips"><a class="chip" href="/imsa/%(y)d/">%(y)d년 이사 길일</a><a class="chip" href="/gyeolhon/%(y)d/">%(y)d년 결혼 길일</a><a class="chip" href="/gaeop/%(y)d/">%(y)d년 개업 길일</a></div>
""" % dict(y=y, c=cnt, w=wkend, p=cnt - wkend, chips="".join('<a class="chip%s" href="/sonnopneun-nal/%d/">%d년</a>' % (" on" if yy == y else "", yy, yy) for yy in YEARS), ad=ad(), t=t, ex=SON_EXPLAIN)
    faq = [("%d년 손 없는 날은 며칠인가요?" % y, "%d년 손 없는 날은 총 %d일입니다. 음력으로 매달 9일·10일·19일·20일·29일·30일이 해당합니다(음력 달이 29일까지면 30일은 없습니다)." % (y, cnt)),
           ("손 없는 날은 어떻게 정하나요?", "음력 날짜의 끝자리가 9나 0인 날이 손 없는 날입니다. 양력 날짜로는 매달 비슷한 시기에 오지만 해마다 달라지므로 달력에서 확인해야 합니다."),
           ("손 없는 날에 이사하면 꼭 좋은가요?", "손 없는 날은 민간에 전해 내려오는 풍습으로 과학적 근거는 없습니다. 날짜를 정할 때 참고하되, 가족 일정과 이삿짐 업체 예약 가능 여부, 비용을 함께 고려하세요.")]
    write(path, layout(path, "%d년 손 없는 날 달력 — 월별 전체 날짜" % y, "%d년 손 없는 날 전체 %d일을 월별로 정리했습니다. 주말·평일 구분과 이사·결혼·개업 길일 판정, 손 방향 설명까지 한눈에 확인하세요." % (y, cnt),
        body, faq, [("홈", "/"), ("손 없는 날", "/sonnopneun-nal/"), ("%d년" % y, path)], coupang=True), "0.9")

def page_son_month(y, m):
    path = "/sonnopneun-nal/%d/%02d/" % (y, m)
    ds = month_days(y, m)
    sons = [d for d in ds if info(d)["son"]]
    rows = ""
    for d in sons:
        i = info(d)
        g = E.judge(d, "imsa")
        rows += "<tr><td>%s</td><td>음력 %s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            date_link(d), i["lunar_str"], "%s(%s)" % (i["gz"], i["gzh"]), esc(i["sh"] + "일"), tag(g[0], GRADE_CLS[g[0]]),
            esc(i["hol"]["name"] if i["hol"] else "주말" if d.weekday() >= 5 else "평일"))
    t = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>양력</th><th>음력</th><th>일진</th><th>12신</th><th>이사 판정</th><th>구분</th></tr></thead><tbody>%s</tbody></table></div>' % rows
    wkdays = [d for d in sons if d.weekday() < 5 and not info(d)["hol"]]
    tip = ("평일 손 없는 날은 %s입니다. 주말보다 이삿짐 업체 예약이 수월하고 비용이 낮은 편입니다." % ", ".join("%d일(%s)" % (d.day, wd(d)) for d in wkdays)) if wkdays else "이달 손 없는 날은 모두 주말이거나 공휴일이라 이사 업체 예약이 빨리 마감될 수 있습니다."
    body = """
<div class="page-head"><h1>%(y)d년 %(m)d월 손 없는 날</h1><p>%(list)s</p></div>
<p class="lead"><b>%(y)d년 %(m)d월 손 없는 날은 %(list)s</b>입니다(총 %(n)d일). %(tip)s</p>
%(grid)s
%(ad)s
<h2 class="group-title">📋 %(m)d월 손 없는 날 상세</h2>
%(t)s
<p class="note">‘이사 판정’은 손 없는 날에 건제 12신과 황도·흑도, 삼궁일 여부를 더해 계산한 참고 등급입니다. 기준은 <a href="/about/">계산 기준</a>에서 확인할 수 있습니다.</p>
<div class="nav-row">%(nv)s</div>
<div class="chips"><a class="chip" href="/%(y)d/%(m2)02d/">%(m)d월 달력</a><a class="chip" href="/imsa/%(y)d/%(m2)02d/">%(m)d월 이사 길일</a><a class="chip" href="/sonnopneun-nal/%(y)d/">%(y)d년 손 없는 날</a></div>
""" % dict(y=y, m=m, m2=m, list=", ".join("%d일(%s)" % (d.day, wd(d)) for d in sons), n=len(sons), tip=tip, grid=month_grid(y, m), ad=ad(), t=t,
           nv=_pm_nav("/sonnopneun-nal/", y, m, "손 없는 날"))
    faq = [("%d년 %d월 손 없는 날은 언제인가요?" % (y, m), "%s입니다." % ", ".join("%d일(%s)" % (d.day, wd(d)) for d in sons)),
           ("%d월에 이사하기 가장 좋은 날은?" % m, ("%s이(가) 이사 대길일입니다." % ", ".join("%d일" % d.day for d in ds if E.judge(d, "imsa")[0] == "대길")) if any(E.judge(d, "imsa")[0] == "대길" for d in ds) else "이달에는 이사 ‘대길’ 등급 날이 없고, 손 없는 날 중 ‘길’ 등급을 고르세요."),
           ("손 없는 날은 비용이 더 비싼가요?", "이삿짐 업체는 손 없는 날과 주말, 월말에 수요가 몰려 같은 조건이라도 요금을 올려 받는 경우가 많습니다. 업체별로 다르니 견적을 여러 곳에서 받아 비교해 보세요.")]
    write(path, layout(path, "%d년 %d월 손 없는 날 — %s" % (y, m, ", ".join("%d일" % d.day for d in sons)),
        "%d년 %d월 손 없는 날은 %s입니다. 요일, 음력, 일진과 이사 판정, 평일 손 없는 날 추천을 정리했습니다." % (y, m, ", ".join("%d일" % d.day for d in sons)),
        body, faq, [("홈", "/"), ("손 없는 날", "/sonnopneun-nal/"), ("%d년" % y, "/sonnopneun-nal/%d/" % y), ("%d월" % m, path)], coupang=True), "0.8")

def _pm_nav(base, y, m, label):
    prev = (y, m - 1) if m > 1 else (y - 1, 12)
    nxt = (y, m + 1) if m < 12 else (y + 1, 1)
    return ('<a class="btn" href="%s%d/%02d/">← %d년 %d월 %s</a>' % (base, prev[0], prev[1], prev[0], prev[1], label) if prev[0] in YEARS else "<span></span>") + \
           ('<a class="btn" href="%s%d/%02d/">%d년 %d월 %s →</a>' % (base, nxt[0], nxt[1], nxt[0], nxt[1], label) if nxt[0] in YEARS else "<span></span>")

def page_son_index():
    y = YEARS[1]
    body = """
<div class="page-head"><h1>손 없는 날 — 이사·결혼·개업 날짜 달력</h1><p>음력 9·10·19·20·29·30일 · %(y0)d~%(y1)d년 월별 전체</p></div>
%(ex)s
<div id="son-next" class="today-box" style="background:var(--primary);border-radius:14px;padding:12px;color:#fff;margin:10px 0"></div>
<div class="chips">%(chips)s</div>
%(ad)s
<h2 class="group-title">📆 연도·월별 손 없는 날</h2>
<div class="card-grid">%(cards)s</div>
<h2 class="group-title">✅ 손 없는 날 고르는 요령</h2>
<p class="lead">손 없는 날이 곧 모든 일에 좋은 날은 아닙니다. 음력 5·14·23일은 삼궁일로 큰일을 피하는 날로 전해지고, 건제 12신 가운데 파(破)·폐(閉)일 같은 날은 이사에 적당하지 않다고 봅니다. 이 사이트의 ‘이사 길일’은 손 없는 날에 이런 요소를 함께 따져 등급을 매긴 것입니다. 실제 날짜는 가족 일정, 이삿짐 업체 예약, 잔금일 같은 현실 조건을 먼저 맞추고 풍습은 참고하세요.</p>
<script src="/assets/js/caldata.js"></script><script src="/assets/js/son-next.js"></script>
""" % dict(y0=YEARS[0], y1=YEARS[-1], ex=SON_EXPLAIN, chips="".join('<a class="chip" href="/sonnopneun-nal/%d/">%d년</a>' % (yy, yy) for yy in YEARS), ad=ad(),
           cards="".join('<a class="card" href="/sonnopneun-nal/%d/%02d/"><b>%d년 %d월</b><span>%s</span></a>' % (yy, m, yy, m, ", ".join("%d일" % d.day for d in month_days(yy, m) if info(d)["son"])) for yy in YEARS[:2] for m in range(1, 13)))
    faq = [("손 없는 날이란 무엇인가요?", "음력 날짜의 끝자리가 9나 0인 날(9·10·19·20·29·30일)로, 사람의 일을 방해하는 ‘손’이 없어 이사·결혼 등 큰일을 하기에 좋다고 전해지는 날입니다."),
           ("올해 손 없는 날을 한 번에 보려면?", "연도 버튼을 눌러 월별 전체 목록을 확인하세요. 월별 페이지에서는 요일과 음력, 이사 판정을 함께 볼 수 있습니다."),
           ("손 없는 날은 꼭 지켜야 하나요?", "민간 풍습이므로 지키지 않아도 법적·실제적 문제는 없습니다. 마음의 편안함과 가족의 뜻을 존중하는 선에서 참고하면 됩니다.")]
    write("/sonnopneun-nal/", layout("/sonnopneun-nal/", "손 없는 날 달력 — 이사·결혼·개업 날짜 (2026~2030)", "손 없는 날 뜻과 계산법, 2026~2030년 월별 손 없는 날 달력. 이사·결혼·개업 길일과 평일 손 없는 날을 쉽게 찾으세요.",
        body, faq, [("홈", "/"), ("손 없는 날", "/sonnopneun-nal/")], coupang=True), "0.95")

# 목적별 길일
PURP_TEXT = {
 "imsa": ("이사", "이사 날짜를 잡을 때 가장 널리 쓰는 기준은 <b>손 없는 날</b>입니다. 여기에 건제 12신 가운데 성(成)·개(開)·만(滿)·정(定)일을 길한 날로, 파(破)·폐(閉)일과 음력 5·14·23일(삼궁일)을 피하는 날로 보고 황도일을 더해 등급을 매겼습니다.",
          "입주 날짜가 잔금일·전입신고 일정과 맞는지 먼저 확인하고, 손 없는 날이 평일이면 이삿짐 센터 예약을 한두 달 전에 잡는 것이 좋습니다."),
 "gyeolhon": ("결혼", "결혼식 날짜는 예식장 예약 가능한 날짜가 가장 현실적인 기준이지만, 전통적으로는 건제 12신 가운데 만(滿)·성(成)·개(開)·정(定)일을 길한 날로 보고 <b>황도일</b>이면 더 좋다고 여겼습니다. 파(破)·위(危)일과 음력 5·14·23일(삼궁일)은 피합니다.",
          "인기 있는 대길일 주말은 1년 전부터 예식장이 마감됩니다. 손 없는 날은 필수 조건은 아니지만 가점으로 반영했습니다."),
 "gaeop": ("개업", "개업은 문을 ‘여는’ 일이라 건제 12신 가운데 <b>개(開)일</b>을 가장 좋게 보고 성(成)·만(滿)·건(建)일도 길한 날로 봅니다. 파(破)·폐(閉)일, 삼궁일(음력 5·14·23일)은 피하며 황도일이면 더 좋다고 여깁니다.",
          "가게 문을 여는 날은 상권 특성(점심 장사, 주말 장사)과 인테리어·인허가 일정을 먼저 맞추고, 비슷한 길일이 여러 날이면 평일 개업으로 첫 주를 시험해 보는 것도 방법입니다."),
}

def month_judge_table(y, m, p, only=("대길", "길")):
    rows = ""
    for d in month_days(y, m):
        g, sc, rs = E.judge(d, p)
        if g not in only: continue
        i = info(d)
        rows += "<tr><td>%s</td><td>음력 %s</td><td>%s</td><td>%s</td><td>%s</td><td style=\"font-size:.82rem\">%s</td></tr>" % (
            date_link(d), i["lunar_str"], tag(g, GRADE_CLS[g]), esc(i["hol"]["name"] if i["hol"] else "주말" if d.weekday() >= 5 else "평일"),
            "손 없는 날" if i["son"] else "-", esc(" · ".join(rs[:3])))
    return rows

def page_purpose_index(p):
    P = PURP[p]; label, intro, tip = PURP_TEXT[p]
    y = YEARS[1]
    body = """
<div class="page-head"><h1>%(lb)s 길일 — %(y0)d~%(y1)d년 %(lb)s하기 좋은 날</h1><p>건제 12신 · 황도일 · 손 없는 날 · 삼궁일로 계산한 월별 %(lb)s 날짜</p></div>
<p class="lead">%(intro)s</p>
<p class="lead">%(tip)s</p>
<div class="chips">%(chips)s</div>
%(ad)s
<h2 class="group-title">📆 월별 %(lb)s 길일</h2>
<div class="card-grid">%(cards)s</div>
<p class="note">기준은 <a href="/about/">계산 기준</a>에서 설명합니다. 풍습에 따른 참고 정보이며 과학적 근거가 있는 것은 아닙니다.</p>
""" % dict(lb=label, y0=YEARS[0], y1=YEARS[-1], intro=intro, tip=tip, chips="".join('<a class="chip" href="/%s/%d/">%d년 %s 길일</a>' % (p, yy, yy, label) for yy in YEARS), ad=ad(),
           cards="".join('<a class="card" href="/%s/%d/%02d/"><b>%d년 %d월</b><span>대길 %s</span></a>' % (p, yy, m, yy, m, ", ".join("%d일" % d.day for d in month_days(yy, m) if E.judge(d, p)[0] == "대길") or "없음") for yy in YEARS[:2] for m in range(1, 13)))
    faq = [("%s 길일은 어떻게 정하나요?" % label, "건제 12신, 황도·흑도일, 음력 삼궁일(5·14·23일) 등 전통 택일 요소를 점수화해 대길·길·보통·피함으로 나눴습니다. 자세한 기준은 ‘계산 기준’ 페이지에 있습니다."),
           ("%s 날짜는 꼭 길일이어야 하나요?" % label, "길일은 민간 풍습에 따른 참고 정보입니다. 일정과 비용, 가족 사정을 먼저 맞추고 같은 조건이라면 길일을 고르는 정도로 활용하세요."),
           ("‘피함’ 등급은 무엇인가요?", "음력 5·14·23일(삼궁일)이거나 건제 12신이 %s일 등 꺼리는 날을 뜻합니다. 부득이하면 다른 날을 고르는 것을 권합니다." % ("·".join(E.PURPOSE[p]["bad"])))]
    write("/%s/" % p, layout("/%s/" % p, "%s 길일 %d~%d년 — %s 날짜 추천" % (label, YEARS[0], YEARS[-1], P["verb"]),
        "%s 길일 달력. 건제 12신·황도일·%s삼궁일로 %d~%d년 월별 %s하기 좋은 날과 피할 날을 정리했습니다." % (label, "손 없는 날·" if p == "imsa" else "", YEARS[0], YEARS[-1], label),
        body, faq, [("홈", "/"), (label + " 길일", "/%s/" % p)], coupang=(p == "imsa")), "0.9")

def page_purpose_year(p, y):
    P = PURP[p]; label, intro, tip = PURP_TEXT[p]
    rows = ""; total = 0; wkend = 0
    for m in range(1, 13):
        ds = month_days(y, m)
        big = [d for d in ds if E.judge(d, p)[0] == "대길"]
        total += len(big); wkend += len([d for d in big if d.weekday() >= 5])
        rows += "<tr><td>%s</td><td>%s</td><td>%d일</td></tr>" % (link("/%s/%d/%02d/" % (p, y, m), "%d월" % m),
            " ".join('<a href="%s" class="%s">%d일(%s)</a>' % (url_date(d), "red" if d.weekday() == 6 else "blue" if d.weekday() == 5 else "", d.day, wd(d)) for d in big) or "-", len([d for d in big if d.weekday() >= 5]))
    t = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>월</th><th>대길일</th><th>주말</th></tr></thead><tbody>%s</tbody></table></div>' % rows
    body = """
<div class="page-head"><h1>%(y)d년 %(lb)s 길일 총정리 — 월별 대길일</h1><p>대길일 %(tot)d일 · 주말 %(wk)d일 · 평일 %(wd_)d일</p></div>
<div class="chips">%(chips)s</div>
<p class="lead"><b>%(y)d년 %(lb)s 대길일은 모두 %(tot)d일</b>이고 이 중 주말에 걸린 날이 %(wk)d일입니다. %(intro)s</p>
%(ad)s
%(t)s
<h2 class="group-title">💡 활용 팁</h2><p class="lead">%(tip)s</p>
<div class="chips"><a class="chip" href="/sonnopneun-nal/%(y)d/">%(y)d년 손 없는 날</a><a class="chip" href="/%(y)d/">%(y)d년 공휴일</a><a class="chip" href="/%(p)s/">%(lb)s 길일 설명</a></div>
""" % dict(y=y, lb=label, tot=total, wk=wkend, wd_=total - wkend, intro=intro, tip=tip, p=p, ad=ad(), t=t,
           chips="".join('<a class="chip%s" href="/%s/%d/">%d년</a>' % (" on" if yy == y else "", p, yy, yy) for yy in YEARS))
    faq = [("%d년 %s하기 좋은 날은 언제인가요?" % (y, label), "%d년 %s 대길일은 총 %d일입니다. 월별 표에서 월을 눌러 대길일과 길일의 상세 사유를 확인하세요." % (y, label, total)),
           ("평일 %s 길일을 고르려면?" % label, "월별 표에서 빨강(일요일)·파랑(토요일)이 아닌 날짜가 평일입니다. 공휴일은 날짜 페이지에서 확인할 수 있습니다."),
           ("길일이 아닌 날에 %s하면 안 되나요?" % label, "그렇지 않습니다. 풍습에 따른 참고 정보일 뿐이며 현실적인 일정과 비용을 우선하세요.")]
    write("/%s/%d/" % (p, y), layout("/%s/%d/" % (p, y), "%d년 %s 길일 — 월별 %s 날짜 총정리" % (y, label, label), "%d년 %s 대길일 %d일을 월별로 정리했습니다. 건제 12신·황도일 기준 %s하기 좋은 날과 주말·평일 구분을 확인하세요." % (y, label, total, label),
        body, faq, [("홈", "/"), (label + " 길일", "/%s/" % p), ("%d년" % y, "/%s/%d/" % (p, y))], coupang=(p == "imsa")), "0.85")

def page_purpose_month(p, y, m):
    P = PURP[p]; label, intro, tip = PURP_TEXT[p]
    ds = month_days(y, m)
    best = [d for d in ds if E.judge(d, p)[0] == "대길"]
    good = [d for d in ds if E.judge(d, p)[0] == "길"]
    avoid = [d for d in ds if E.judge(d, p)[0] == "피함"]
    wk_best = [d for d in best if d.weekday() >= 5 or info(d)["hol"]]
    pl_best = [d for d in best if d.weekday() < 5 and not info(d)["hol"]]
    t = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>날짜</th><th>음력</th><th>등급</th><th>구분</th><th>손 없는 날</th><th>사유</th></tr></thead><tbody>%s</tbody></table></div>' % month_judge_table(y, m, p)
    lead = ("<p class=\"lead\"><b>%d년 %d월 %s 대길일은 %s</b>입니다. " % (y, m, label, ", ".join("%d일(%s)" % (d.day, wd(d)) for d in best) or "없")) + \
           ("그 밖에 ‘길’ 등급은 %s입니다. " % ", ".join("%d일" % d.day for d in good[:10]) if good else "") + \
           (("평일 대길일은 %s이고, " % ", ".join("%d일" % d.day for d in pl_best)) if pl_best else "이달 대길일은 모두 주말이거나 공휴일이며, ") + \
           ("피하는 게 좋은 날은 %s입니다.</p>" % ", ".join("%d일" % d.day for d in avoid[:12]) if avoid else "피할 날은 없습니다.</p>")
    body = """
<div class="page-head"><h1>%(y)d년 %(m)d월 %(lb)s 길일 — %(lb)s하기 좋은 날</h1><p>대길 %(nb)d일 · 길 %(ng)d일 · 피하는 날 %(na)d일</p></div>
%(lead)s
%(grid)s
%(ad)s
<h2 class="group-title">✨ %(m)d월 %(lb)s 길일 상세 <small>대길·길 등급</small></h2>
%(t)s
<p class="note">기준: %(intro)s</p>
<h2 class="group-title">⚠️ 피하는 게 좋은 날</h2>
<p class="lead">%(avoid)s</p>
<div class="nav-row">%(nv)s</div>
<div class="chips"><a class="chip" href="/%(y)d/%(m2)02d/">%(m)d월 달력</a><a class="chip" href="/sonnopneun-nal/%(y)d/%(m2)02d/">%(m)d월 손 없는 날</a><a class="chip" href="/%(p)s/%(y)d/">%(y)d년 %(lb)s 길일</a></div>
""" % dict(y=y, m=m, m2=m, lb=label, nb=len(best), ng=len(good), na=len(avoid), lead=lead, grid=month_grid(y, m), ad=ad(), t=t, intro=intro,
           avoid=("; ".join("%s(%s)" % (fmtw(d, False), E.judge(d, p)[2][0]) for d in avoid[:8]) or "없습니다") , nv=_pm_nav("/%s/" % p, y, m, label + " 길일"), p=p)
    faq = [("%d년 %d월 %s 길일은 언제인가요?" % (y, m, label), "대길일은 %s입니다." % (", ".join("%d일(%s)" % (d.day, wd(d)) for d in best) or "없습니다")),
           ("%d월 주말 %s 길일이 있나요?" % (m, label), ("있습니다. %s입니다." % ", ".join("%d일(%s)" % (d.day, wd(d)) for d in wk_best)) if wk_best else "이달 대길일 중 주말·공휴일은 없습니다."),
           ("등급은 어떻게 매기나요?", "건제 12신, 황도·흑도일, 손 없는 날, 삼궁일을 점수화한 참고 등급입니다. 자세한 계산 기준은 계산 기준 페이지를 확인하세요.")]
    write("/%s/%d/%02d/" % (p, y, m), layout("/%s/%d/%02d/" % (p, y, m), "%d년 %d월 %s 길일 — %s 대길일 %s" % (y, m, label, label, ", ".join("%d일" % d.day for d in best[:5]) or "없음"),
        "%d년 %d월 %s하기 좋은 날. 대길일 %s. 건제 12신·황도일·손 없는 날 기준으로 정리한 월별 %s 길일입니다." % (y, m, label, ", ".join("%d일" % d.day for d in best[:6]) or "없음", label),
        body, faq, [("홈", "/"), (label + " 길일", "/%s/" % p), ("%d년" % y, "/%s/%d/" % (p, y)), ("%d월" % m, "/%s/%d/%02d/" % (p, y, m))], coupang=(p == "imsa")), "0.8")

# ───────────────────────── 날짜 페이지 ─────────────────────────
def page_date(d):
    i = info(d)
    path = url_date(d)
    ly, lm = i["ly"], i["lm"]
    verd = ""
    for p in PURP:
        g, sc, rs = E.judge(d, p)
        verd += '<div><h3>%s %s</h3><p>%s</p><ul>%s</ul></div>' % (PURP[p]["hero"] + " " + PURP[p]["label"], tag(g, GRADE_CLS[g]),
            {"대길": "%s하기 아주 좋은 날로 봅니다." % PURP[p]["label"], "길": "무난하게 좋은 날로 봅니다.", "보통": "특별히 좋지도 나쁘지도 않은 날입니다.", "피함": "전통적으로 피하는 날입니다."}[g],
            "".join("<li>%s</li>" % esc(r) for r in rs[:4]))
    sd = son_dir(i["ld"])
    prevd, nextd = d - D1, d + D1
    prev_son = next((x for x in (d - dt.timedelta(days=k) for k in range(1, 40)) if info(x)["son"]), None)
    next_son = next((x for x in (d + dt.timedelta(days=k) for k in range(1, 40)) if info(x)["son"]), None)
    next_hol = next((x for x in (d + dt.timedelta(days=k) for k in range(0, 400)) if x.year <= YEARS[-1] and info(x)["hol"] and x >= d), None)
    near = []
    if next_son and not i["son"]: near.append("다음 손 없는 날은 %s(%d일 뒤)입니다." % (date_link(next_son, True), (next_son - d).days))
    if prev_son and not i["son"]: near.append("직전 손 없는 날은 %s입니다." % date_link(prev_son, True))
    if next_hol and next_hol != d: near.append("다음 공휴일은 %s %s(%d일 뒤)입니다." % (date_link(next_hol, True), esc(info(next_hol)["hol"]["name"]), (next_hol - d).days))
    off_a, off_b = off_block(d) if i["off"] else (None, None)
    facts = [("양력", fmtw(d)), ("음력", ("윤달 " if i["leap"] else "") + "%d년 %s" % (ly, i["lunar_str"])), ("일진", "%s(%s)일 — %s의 날" % (i["gz"], i["gzh"], i["animal"])),
             ("건제 12신", "%s(%s)일" % (i["sh"], E.SHIN12_H[E.SHIN12.index(i["sh"])])), ("황도/흑도", "%s일 (%s)" % (i["hw"], "황도 길신" if i["hw"] in E.HWANGDO_GOOD else "흑도")),
             ("손 없는 날", "예 — 음력 %d일, 손이 하늘로 올라간 날" % i["ld"] if i["son"] else "아니요 — 손이 %s에 있는 날" % sd)]
    if i["hol"]: facts.insert(1, ("공휴일", i["hol"]["name"]))
    if i["term"]: facts.insert(1, ("24절기", "%s(%s) %s" % (i["term"]["name"], i["term"]["hanja"], i["term"]["at"].strftime("%H시 %M분"))))
    if i["off"] and off_a != off_b:
        facts.append(("연휴", "%s ~ %s (%d일)" % (fmtw(off_a, False), fmtw(off_b, False), (off_b - off_a).days + 1)))
    ft = '<div class="tbl-wrap"><table class="tbl"><tbody>%s</tbody></table></div>' % "".join("<tr><th style=\"width:110px\">%s</th><td>%s</td></tr>" % (esc(k), esc(v)) for k, v in facts)
    kinds = []
    if i["hol"]: kinds.append(i["hol"]["name"])
    if i["term"]: kinds.append("24절기 " + i["term"]["name"])
    best = [PURP[p]["label"] for p in PURP if E.judge(d, p)[0] == "대길"]
    shh = E.SHIN12_H[E.SHIN12.index(i["sh"])]
    lead = ("<p class=\"lead\"><b>%s</b>은 음력 %d년 <b>%s</b>이고 일진은 <b>%s(%s)일</b>입니다. 건제 12신으로는 ‘%s(%s)’일이며 %s일(%s)입니다.%s %s%s</p>") % (
        fmtw(d), ly, i["lunar_str"], i["gz"], i["gzh"], i["sh"], shh, i["hw"], "황도 길신" if i["hw"] in E.HWANGDO_GOOD else "흑도",
        (" 이날은 <b>" + "·".join(kinds) + "</b>입니다.") if kinds else "",
        ("<b>손 없는 날</b>이라 이사·결혼 날짜로 많이 선택합니다." if i["son"] else "손이 %s에 있는 날이라 손 없는 날은 아닙니다." % sd),
        (" %s에 특히 좋은 ‘대길’ 등급입니다." % "·".join(best)) if best else "")
    nav = '<div class="nav-row"><a class="btn" href="%s">← %s</a><a class="btn" href="%s">%s →</a></div>' % (url_date(prevd), fmt(prevd, False), url_date(nextd), fmt(nextd, False)) if (prevd.year >= YEARS[0] and nextd.year <= YEARS[-1]) else ""
    body = """
<div class="page-head"><h1>%(t)s</h1><p>%(sub)s</p></div>
%(lead)s
<div class="verdict">%(verd)s</div>
%(ad)s
<h2 class="group-title">📋 %(fd)s 달력 정보</h2>
%(ft)s
<h2 class="group-title">🧭 가까운 날</h2>
<ul class="lead" style="margin-left:18px">%(near)s<li>%(ep)s</li></ul>
%(nav)s
<div class="chips"><a class="chip" href="/%(y)d/%(m2)02d/">%(y)d년 %(m)d월 달력</a><a class="chip" href="/sonnopneun-nal/%(y)d/%(m2)02d/">%(m)d월 손 없는 날</a><a class="chip" href="/imsa/%(y)d/%(m2)02d/">%(m)d월 이사 길일</a><a class="chip" href="/umnyeok/">음력 변환</a></div>
""" % dict(t="%s 음력 %s · %s" % (fmtw(d), i["lunar_str"], "손 없는 날" if i["son"] else "일진 " + i["gz"]), sub="%s일 · %s · 12신 %s" % (i["gz"], "공휴일 " + i["hol"]["name"] if i["hol"] else ("주말" if d.weekday() >= 5 else "평일"), i["sh"]),
           lead=lead, verd=verd, ad=ad(), fd=fmtw(d), ft=ft, near="".join("<li>%s</li>" % n for n in near), ep="한 달 달력은 %s에서 볼 수 있습니다." % link("/%d/%02d/" % (d.year, d.month), "%d년 %d월 달력" % (d.year, d.month)),
           nav=nav, y=d.year, m=d.month, m2=d.month)
    faq = [("%s은 손 없는 날인가요?" % fmtw(d), ("네, 음력 %d일이라 손 없는 날입니다." % i["ld"]) if i["son"] else "아니요, 음력 %d일이라 손 없는 날이 아닙니다. 손은 %s에 있다고 전해집니다.%s" % (i["ld"], sd, (" 가까운 손 없는 날은 %s입니다." % fmtw(next_son, False)) if next_son else "")),
           ("%s은 음력으로 며칠인가요?" % fmtw(d), "음력 %d년 %s입니다. 일진은 %s일입니다." % (ly, i["lunar_str"], i["gz"])),
           ("%s에 이사해도 되나요?" % fmtw(d), "이사 판정은 ‘%s’입니다. %s" % (E.judge(d, "imsa")[0], " · ".join(E.judge(d, "imsa")[2][:3])))]
    write(path, layout(path, "%s 음력 %s — %s, 이사·결혼 길일 여부" % (fmtw(d), i["lunar_str"], "손 없는 날" if i["son"] else "일진 %s일" % i["gz"]),
        "%s은 음력 %s, %s일. %s이사 %s·결혼 %s·개업 %s 판정과 가까운 손 없는 날을 확인하세요." % (fmtw(d), i["lunar_str"], i["gz"], ("손 없는 날. " if i["son"] else ""), E.judge(d, "imsa")[0], E.judge(d, "gyeolhon")[0], E.judge(d, "gaeop")[0]),
        body, faq, [("홈", "/"), ("%d년 %d월" % (d.year, d.month), "/%d/%02d/" % (d.year, d.month)), (fmt(d, False), path)], coupang=False), "0.4")

# ───────────────────────── 음력 변환 ─────────────────────────
def build_lunar_table():
    lines = []
    base = dt.date(1900, 1, 1)
    for ly in range(1900, 2050):
        ny = E.solar_of(ly, 1, 1)
        lens = []
        leap_m = 0
        for mth in range(1, 13):
            for lp in (False, True):
                _lc = E._lc
                ok = _lc.setLunarDate(ly, mth, 1, lp)
                if not ok: continue
                if lp: leap_m = mth
                full = _lc.setLunarDate(ly, mth, 30, lp)
                lens.append("1" if full else "0")
        lines.append([ly, (ny - base).days, leap_m, "".join(lens)])
    return lines

def write_assets():
    a = ROOT / "assets" / "js"
    lt = build_lunar_table()
    (a / "lunar-table.js").write_text("/* 음력 표 1900~2049: [음력연, 설날의 1900-01-01 기준 일수, 윤달 월(0=없음), 월별 대소(1=30일) — 윤달은 해당 월 뒤에 위치] */\nvar LT=" + json.dumps(lt, separators=(",", ":")) + ";\n", encoding="utf-8")
    names, tn = [], [t[0] for t in E.TERMS]
    days = []
    start = dt.date(YEARS[0], 1, 1)
    for d in daterange(start, dt.date(YEARS[-1], 12, 31)):
        i = info(d)
        hn = -1
        if i["hol"]:
            if i["hol"]["name"] not in names: names.append(i["hol"]["name"])
            hn = names.index(i["hol"]["name"])
        days.append([i["lm"] + (100 if i["leap"] else 0), i["ld"], E.day_index(d), E.SHIN12.index(i["sh"]), E.HWANGDO.index(i["hw"]), hn, tn.index(i["term"]["name"]) if i["term"] else -1])
    js = "var CAL=" + json.dumps(dict(s=start.isoformat(), h=names, t=tn, g=E.HWANGDO, k=E.SHIN12, d=days), ensure_ascii=False, separators=(",", ":")) + ";\n"
    (a / "caldata.js").write_text(js, encoding="utf-8")

def page_umnyeok_index():
    body = """
<div class="page-head"><h1>음력 양력 변환기 — 양력↔음력 날짜 계산</h1><p>1900~2049년 · 윤달 지원 · 일진·띠 표시</p></div>
<p class="lead">양력 날짜를 음력으로, 음력 날짜를 양력으로 바꿔 줍니다. 한국천문연구원의 음양력 자료를 바탕으로 한 표를 쓰므로 윤달도 정확히 구분하고, 변환한 날짜의 <b>일진·띠·요일·손 없는 날 여부</b>까지 함께 알려 줍니다. 기일(제사)이나 생일, 명절 날짜를 확인할 때 쓰세요.</p>
<div class="tool-box"><h3 style="margin-top:0">양력 → 음력</h3>
<div class="tool-row"><div><label for="s-y">년</label><input id="s-y" type="number" min="1900" max="2049" value="%(y)d" style="width:90px"></div>
<div><label for="s-m">월</label><input id="s-m" type="number" min="1" max="12" value="1" style="width:70px"></div>
<div><label for="s-d">일</label><input id="s-d" type="number" min="1" max="31" value="1" style="width:70px"></div>
<button class="btn-p" id="s-go">음력으로 변환</button></div><div class="tool-out" id="s-out">날짜를 입력하고 변환을 눌러 주세요.</div></div>
<div class="tool-box"><h3 style="margin-top:0">음력 → 양력</h3>
<div class="tool-row"><div><label for="l-y">음력 년</label><input id="l-y" type="number" min="1900" max="2049" value="%(y)d" style="width:90px"></div>
<div><label for="l-m">월</label><input id="l-m" type="number" min="1" max="12" value="1" style="width:70px"></div>
<div><label for="l-d">일</label><input id="l-d" type="number" min="1" max="30" value="1" style="width:70px"></div>
<div><label for="l-leap">윤달</label><input id="l-leap" type="checkbox" style="width:20px;height:20px"></div>
<button class="btn-p" id="l-go">양력으로 변환</button></div><div class="tool-out" id="l-out">날짜를 입력하고 변환을 눌러 주세요.</div></div>
%(ad)s
<h2 class="group-title">📅 연도별 음력 정보</h2>
<div class="chips">%(chips)s<a class="chip" href="/umnyeok/seol-chuseok/">설날·추석 10년 달력</a></div>
<h2 class="group-title">❓ 음력과 양력의 차이</h2>
<p class="lead">양력은 지구가 태양을 한 바퀴 도는 시간(약 365.24일)을, 음력은 달이 차고 기우는 주기(약 29.53일)를 기준으로 합니다. 음력 12달은 354일 안팎이라 양력과 해마다 약 11일씩 어긋나고, 이를 맞추려 3년에 한 번 정도 <b>윤달</b>을 넣습니다. 그래서 설날과 추석은 양력으로 날짜가 바뀝니다. 한국의 음력은 한국천문연구원이 천문 계산으로 정하는 날짜를 따릅니다.</p>
<script src="/assets/js/lunar-table.js"></script><script src="/assets/js/converter.js"></script>
""" % dict(y=YEARS[1], ad=ad(), chips="".join('<a class="chip" href="/umnyeok/%d/">%d년 음력</a>' % (yy, yy) for yy in YEARS))
    faq = [("양력 생일을 음력으로 바꾸려면?", "위 변환기에 양력 생년월일을 입력하면 해당 날짜의 음력이 나옵니다. 음력으로 생일을 쇠는 경우 해마다 양력 날짜가 달라지므로 그해 음력 날짜를 양력으로 다시 바꿔야 합니다."),
           ("윤달은 어떻게 표시하나요?", "윤달이 있는 해에는 같은 이름의 달이 두 번 나옵니다(예: 윤5월). 음력 → 양력 변환에서 ‘윤달’을 체크하면 윤달 날짜로 계산합니다."),
           ("변환 결과가 다른 사이트와 다르면?", "한국의 음력은 한국천문연구원 기준입니다. 중국 음력은 계산 기준이 달라 드물게 하루 다를 수 있습니다.")]
    write("/umnyeok/", layout("/umnyeok/", "음력 양력 변환기 — 양력↔음력 날짜 계산 (1900~2049, 윤달)", "양력을 음력으로, 음력을 양력으로 변환합니다. 윤달 지원, 일진·띠·손 없는 날 표시. 1900~2049년 한국천문연구원 음양력 자료 기준.",
        body, faq, [("홈", "/"), ("음력 변환", "/umnyeok/")]), "0.9")

def page_umnyeok_year(y):
    path = "/umnyeok/%d/" % y
    ny = E.solar_of(y, 1, 1)
    rows = ""
    leap_info = ""
    for lm in range(1, 13):
        for lp in (False, True):
            try:
                s = E.solar_of(y, lm, 1, lp)
            except Exception:
                continue
            if lp and not E._lc.setLunarDate(y, lm, 1, True): continue
            if E._lc.setLunarDate(y, lm, 1, lp) is False: continue
            s = E.solar_of(y, lm, 1, lp)
            ln = 30 if E._lc.setLunarDate(y, lm, 30, lp) else 29
            if lp: leap_info = "윤%d월" % lm
            rows += "<tr><td>%s음력 %d월</td><td>%s</td><td>%d일(%s)</td></tr>" % ("윤" if lp else "", lm, date_link(s, True), ln, "대월" if ln == 30 else "소월")
    t = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>음력 월</th><th>1일의 양력 날짜</th><th>일수</th></tr></thead><tbody>%s</tbody></table></div>' % rows
    gi = (y - 4) % 60
    key = [("설날", ny), ("정월 대보름(음 1월 15일)", E.solar_of(y, 1, 15)), ("부처님오신날(음 4월 8일)", E.solar_of(y, 4, 8)), ("단오(음 5월 5일)", E.solar_of(y, 5, 5)),
           ("칠석(음 7월 7일)", E.solar_of(y, 7, 7)), ("추석(음 8월 15일)", E.solar_of(y, 8, 15)), ("중양절(음 9월 9일)", E.solar_of(y, 9, 9)), ("동지(양력, 절기)", [t["at"].date() for t in E.terms_of_year(y) if t["name"] == "동지"][0])]
    krow = "".join("<tr><td>%s</td><td>%s</td></tr>" % (esc(n), date_link(d, True)) for n, d in key)
    kt = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>명절·절기</th><th>%d년 양력</th></tr></thead><tbody>%s</tbody></table></div>' % (y, krow)
    body = """
<div class="page-head"><h1>%(y)d년 음력 달력 — 설날·추석·윤달</h1><p>%(gz)s년 %(animal)s띠의 해 · %(leap)s</p></div>
<div class="chips">%(chips)s</div>
<p class="lead"><b>%(y)d년 설날은 %(ny)s</b>, 추석은 %(cs)s입니다. %(y)d년은 간지로 <b>%(gz)s(%(gzh)s)년</b>, <b>%(animal)s띠</b>의 해이며 %(leap_txt)s</p>
%(ad)s
<h2 class="group-title">🎑 %(y)d년 주요 명절 날짜</h2>
%(kt)s
<h2 class="group-title">🌙 음력 월별 1일 (양력 날짜)</h2>
%(t)s
<p class="note">음력 연도는 설날을 기준으로 바뀌므로 1월 초·중순(설날 이전)의 양력 날짜는 전년도 음력에 속합니다. 띠는 민속에서 설날(음력 1월 1일), 사주에서는 입춘을 기준으로 바뀝니다.</p>
<div class="chips"><a class="chip" href="/umnyeok/">음력↔양력 변환기</a><a class="chip" href="/%(y)d/">%(y)d년 공휴일</a><a class="chip" href="/jeolgi/%(y)d/">%(y)d년 24절기</a></div>
""" % dict(y=y, gz=E.ganzhi(gi), gzh=E.ganzhi_h(gi), animal=E.ANIMAL[gi % 12], leap=("윤달 있음(%s)" % leap_info) if leap_info else "윤달 없음", chips="".join('<a class="chip%s" href="/umnyeok/%d/">%d년</a>' % (" on" if yy == y else "", yy, yy) for yy in YEARS),
           ny=fmtw(ny, False), cs=fmtw(E.solar_of(y, 8, 15), False), ad=ad(), kt=kt, t=t, leap_txt=("이 해에는 %s이 있어 음력으로 13달입니다." % leap_info) if leap_info else "윤달이 없어 음력으로 12달입니다.")
    faq = [("%d년 설날은 언제인가요?" % y, "%d년 설날은 %s입니다." % (y, fmtw(ny, True))),
           ("%d년 추석은 언제인가요?" % y, "%d년 추석(음력 8월 15일)은 %s입니다." % (y, fmtw(E.solar_of(y, 8, 15), True))),
           ("%d년에 윤달이 있나요?" % y, ("네, %s이 있습니다." % leap_info) if leap_info else "아니요, %d년에는 윤달이 없습니다." % y)]
    write(path, layout(path, "%d년 음력 달력 — 설날 %s·추석 %s·윤달" % (y, fmt(ny, False), fmt(E.solar_of(y, 8, 15), False)),
        "%d년 음력 달력. 설날 %s, 추석 %s, 정월 대보름·단오·칠석 날짜와 음력 월별 1일 양력 날짜, 윤달 여부를 정리했습니다." % (y, fmtw(ny, False), fmtw(E.solar_of(y, 8, 15), False)),
        body, faq, [("홈", "/"), ("음력 변환", "/umnyeok/"), ("%d년" % y, path)]), "0.8")

def page_seol_chuseok():
    rows = ""
    for y in range(2024, 2036):
        s, c = E.solar_of(y, 1, 1), E.solar_of(y, 8, 15)
        rows += "<tr><td>%d년</td><td>%s</td><td>%s</td></tr>" % (y, esc(fmtw(s, False)), esc(fmtw(c, False)))
    body = """
<div class="page-head"><h1>설날·추석 날짜 10년 달력 (2024~2035)</h1><p>양력 날짜와 요일 한눈에</p></div>
<p class="lead">설날(음력 1월 1일)과 추석(음력 8월 15일)은 양력으로 해마다 날짜가 달라집니다. 2024년부터 2035년까지의 양력 날짜와 요일을 정리했습니다. 연도별 연휴 길이와 대체공휴일은 각 연도의 공휴일 페이지에서 확인하세요.</p>
%(ad)s
<div class="tbl-wrap"><table class="tbl"><thead><tr><th>연도</th><th>설날</th><th>추석</th></tr></thead><tbody>%(rows)s</tbody></table></div>
<div class="chips"><a class="chip" href="/%(y1)d/seol/">%(y1)d년 설날</a><a class="chip" href="/%(y1)d/chuseok/">%(y1)d년 추석</a><a class="chip" href="/umnyeok/">음력 변환기</a></div>
""" % dict(ad=ad(), rows=rows, y1=YEARS[1])
    faq = [("올해 설날과 추석은 언제인가요?", "연도별 표에서 확인하세요. 설날은 음력 1월 1일, 추석은 음력 8월 15일이며 각각 전날과 다음날을 포함해 3일 연휴입니다."),
           ("설날과 추석이 일요일이면?", "연휴 중 일요일이 있으면 연휴가 끝난 다음 평일이 대체공휴일입니다.")]
    write("/umnyeok/seol-chuseok/", layout("/umnyeok/seol-chuseok/", "설날·추석 날짜 10년 달력 (2024~2035)", "2024~2035년 설날과 추석의 양력 날짜와 요일을 한 표로 정리했습니다.",
        body, faq, [("홈", "/"), ("음력 변환", "/umnyeok/"), ("설날·추석", "/umnyeok/seol-chuseok/")]), "0.7")

# ───────────────────────── 홈 / 기타 ─────────────────────────
def page_home():
    y = YEARS[1]
    cards = [("🎌", "%d년 공휴일" % y, "대체공휴일·연휴·연차 쓰는 법", "/%d/" % y), ("🗓️", "%d년 %d월 달력" % (y, 1), "음력·절기·손 없는 날 표시", "/%d/01/" % y),
             ("🧭", "손 없는 날", "월별 전체 날짜와 뜻", "/sonnopneun-nal/"), ("🚚", "이사 길일", "손 없는 날 + 건제 12신", "/imsa/"),
             ("💍", "결혼 길일", "황도일·길한 12신", "/gyeolhon/"), ("🏪", "개업 길일", "문 여는 날 ‘개(開)일’", "/gaeop/"),
             ("🌱", "24절기", "입춘~대한 날짜·시각", "/jeolgi/"), ("🌙", "음력 양력 변환", "윤달·일진·띠", "/umnyeok/")]
    cards_html = "".join('<a class="card" href="%s"><b>%s %s</b><span>%s</span></a>' % (u, ic, esc(t), esc(s)) for ic, t, s, u in cards)
    body = """
<div class="hero"><h1>🗓️ 오늘 날짜 · 음력 · 손 없는 날</h1><p id="today-line">공휴일, 음력, 24절기, 손 없는 날과 이사·결혼·개업 길일을 한 곳에서 확인하세요.</p>
<div class="today-box" id="today-box"></div></div>
%(ad)s
<h2 class="group-title">🔎 바로 가기</h2>
<div class="card-grid">%(cards)s</div>
<div id="upcoming"></div>
<h2 class="group-title">📅 연도별 공휴일</h2>
<div class="chips">%(chips)s</div>
<p class="lead">우아달력은 한국천문연구원 음양력 자료와 태양 시황경 계산, 공휴일 관련 규정을 바탕으로 <b>%(y0)d~%(y1)d년</b>의 공휴일·대체공휴일, 음력, 24절기, 손 없는 날, 이사·결혼·개업 길일을 날짜별로 정리한 달력 사이트입니다. 모든 날짜마다 음력과 일진, 길흉 판정을 확인할 수 있고, 계산 기준은 <a href="/about/">계산 기준</a> 페이지에 공개했습니다.</p>
<script src="/assets/js/caldata.js"></script><script src="/assets/js/home.js"></script>
""" % dict(ad=ad(), cards=cards_html, chips="".join('<a class="chip" href="/%d/">%d년 공휴일</a>' % (yy, yy) for yy in YEARS), y0=YEARS[0], y1=YEARS[-1])
    faq = [("올해 공휴일은 며칠인가요?", "연도별 페이지에서 확인하세요. %d년은 관공서 공휴일 %d일(일요일 제외 %d일)입니다." % (y, year_stats(y)["n"], year_stats(y)["real"])),
           ("손 없는 날은 언제인가요?", "음력 날짜의 끝자리가 9나 0인 날(9·10·19·20·29·30일)입니다. 월별 손 없는 날 페이지에서 양력 날짜를 확인하세요."),
           ("음력 날짜는 어디 기준인가요?", "한국천문연구원이 발표하는 음양력 자료(한국 표준시)를 기준으로 한 표를 사용합니다.")]
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": "우아달력", "url": BASE + "/", "inLanguage": "ko"}]
    write("/", layout("/", "우아달력 — 공휴일·음력·손 없는 날·24절기 달력", "공휴일·대체공휴일, 음력 변환, 24절기, 손 없는 날과 이사·결혼·개업 길일을 날짜별로 확인하는 달력 사이트. %d~%d년." % (YEARS[0], YEARS[-1]),
        body, faq, None, extra_ld=ld), "1.0")

def page_about():
    body = """
<div class="page-head"><h1>계산 기준과 데이터 출처</h1><p>우아달력이 날짜를 어떻게 계산하는지 공개합니다</p></div>
<h2 class="group-title">🌙 음력</h2>
<p class="lead">음력 날짜는 한국천문연구원이 발표하는 음양력 자료를 바탕으로 한 변환 표(1900~2049년)를 사용합니다. 윤달과 대월(30일)·소월(29일)이 모두 반영돼 있으며 한국 표준시(KST)를 기준으로 하는 한국의 음력입니다.</p>
<h2 class="group-title">🌱 24절기</h2>
<p class="lead">24절기는 태양의 겉보기 황경(시황경)이 15도의 배수가 되는 순간을 천문 계산(겉보기 위치, 한국 표준시)으로 구해 분 단위로 표시합니다. 입춘은 2024~2026년에 공개된 시각과 분 단위까지 일치함을 확인했습니다.</p>
<h2 class="group-title">🎌 공휴일</h2>
<p class="lead">법정공휴일은 「관공서의 공휴일에 관한 규정」과 대체공휴일 규정에 따라 계산합니다. 설날·추석 연휴는 일요일 또는 다른 공휴일과 겹치면 연휴 다음 첫 평일을 대체공휴일로 하고, 어린이날·삼일절·광복절·개천절·한글날·부처님오신날·성탄절(2026년부터 노동절·제헌절 포함)은 토·일요일 또는 다른 공휴일과 겹치면 다음 첫 평일을 대체공휴일로 합니다. 신정과 현충일에는 대체공휴일이 없습니다. 선거일(국회의원·대통령·지방선거)과 이미 지정된 임시공휴일은 별도로 반영했고, 새 임시공휴일은 발표되는 대로 추가합니다. 2027년은 우주항공청이 발표한 월력요항(관공서 공휴일 76일, 실질 72일)과 같은 결과임을 확인했습니다.</p>
<h2 class="group-title">🧭 손 없는 날</h2>
<p class="lead">음력 날짜의 끝자리가 9 또는 0인 날(9·10·19·20·29·30일)을 손 없는 날로 표시합니다. 음력 1·2일은 동쪽, 3·4일은 남쪽, 5·6일은 서쪽, 7·8일은 북쪽에 손이 있다고 전해집니다.</p>
<h2 class="group-title">✨ 길일 판정 (이사·결혼·개업)</h2>
<p class="lead">길일은 전통 택일에서 쓰는 몇 가지 요소를 점수화한 참고 정보입니다.</p>
<ul class="lead" style="margin-left:20px">
<li><b>일진</b>: 날짜마다 60간지가 순서대로 붙습니다(2000년 1월 1일 = 무오일).</li>
<li><b>건제 12신</b>: 건(建)·제(除)·만(滿)·평(平)·정(定)·집(執)·파(破)·위(危)·성(成)·수(收)·개(開)·폐(閉)가 일진의 지지와 그 달의 지지(절기 기준)를 비교해 정해집니다. 절입일(입춘·경칩 등) 당일부터 새 달로 계산합니다.</li>
<li><b>황도일/흑도일</b>: 월 지지에 따라 청룡·명당·금궤·천덕·옥당·사명이 있는 날은 황도(길), 천형·주작·백호·천뢰·현무·구진은 흑도로 봅니다.</li>
<li><b>삼궁일</b>: 음력 5·14·23일은 큰일을 피하는 날로 전해집니다.</li>
<li><b>이사</b>: 성·개·만·정일 + 손 없는 날 + 황도일은 가점, 파·폐일과 삼궁일은 ‘피함’. <b>결혼</b>: 만·성·개·정일 + 황도일, 파·위일 기피. <b>개업</b>: 개·성·만·건일 + 황도일, 파·폐일 기피.</li>
<li>등급: ‘대길’은 해당 목적에 길한 12신이면서 손 없는 날(이사) 또는 황도일(결혼·개업)인 날, ‘길’은 길한 12신이거나 황도일이면서 손 없는 날, ‘피함’은 기피 조건이 있는 날입니다.</li></ul>
<p class="note">이 판정은 민간에 전승되는 풍습을 정리한 것으로 과학적 근거가 있는 것은 아니며, 지역·유파마다 기준이 달라 다른 책력과 결과가 다를 수 있습니다. 실제 날짜는 일정과 비용을 우선해 정하세요.</p>
<h2 class="group-title">📬 문의·정정</h2>
<p class="lead">날짜 오류나 새로 지정된 임시공휴일을 발견하면 <a href="mailto:ingmaster83@gmail.com">ingmaster83@gmail.com</a> 으로 알려 주세요.</p>
"""
    write("/about/", layout("/about/", "계산 기준과 데이터 출처", "우아달력의 음력, 24절기, 공휴일, 손 없는 날, 이사·결혼·개업 길일 계산 기준과 데이터 출처를 공개합니다.", body, None, [("홈", "/"), ("계산 기준", "/about/")]), "0.5")

def page_privacy():
    body = """
<div class="page-head"><h1>개인정보처리방침</h1></div>
<p class="lead">우아달력(wooacal.wooahouse.com, 이하 “서비스”)은 이용자의 개인정보를 중요하게 생각하며 관련 법령을 준수합니다.</p>
<h3>1. 수집하는 개인정보</h3><p class="lead">서비스는 회원가입이나 로그인을 요구하지 않으며 이용자의 개인정보를 직접 수집하지 않습니다. 음력 변환기에 입력한 날짜는 브라우저 안에서만 계산되고 서버로 전송되지 않습니다.</p>
<h3>2. 자동 수집 정보</h3><p class="lead">서비스 품질 개선을 위해 Google Analytics로 방문자 수·페이지뷰 등 익명 통계를 수집하며, Google AdSense와 쿠팡 파트너스는 맞춤형 광고를 위해 쿠키를 사용할 수 있습니다. 쿠키는 브라우저 설정에서 비활성화할 수 있습니다. (<a href="https://policies.google.com/privacy">Google 개인정보처리방침</a>, <a href="https://policies.google.com/technologies/ads">Google 광고 정책</a>)</p>
<h3>3. 쿠팡 파트너스</h3><p class="lead">일부 페이지에는 쿠팡 파트너스 활동의 일환으로 광고가 포함돼 있으며 이에 따른 수수료를 제공받을 수 있습니다.</p>
<h3>4. 문의</h3><p class="lead">개인정보 관련 문의: <a href="mailto:ingmaster83@gmail.com">ingmaster83@gmail.com</a></p>
<p class="note">최종 수정일: 2026년 10월 18일</p>
"""
    write("/privacy/", layout("/privacy/", "개인정보처리방침", "우아달력 개인정보처리방침", body, None, [("홈", "/"), ("개인정보처리방침", "/privacy/")]), sitemap=False)

def make_404():
    body = '<div class="page-head"><h1>페이지를 찾을 수 없습니다</h1><p>주소가 바뀌었거나 제공 기간(%d~%d년) 밖의 날짜일 수 있어요.</p></div>'            '<div class="chips"><a class="chip" href="/">홈</a><a class="chip" href="/%d/">%d년 공휴일</a><a class="chip" href="/sonnopneun-nal/">손 없는 날</a><a class="chip" href="/umnyeok/">음력 변환</a></div>' % (YEARS[0], YEARS[-1], YEARS[1], YEARS[1])
    (ROOT / "404.html").write_text(layout("/404.html", "페이지를 찾을 수 없습니다", "요청한 페이지를 찾을 수 없습니다.", body, None, None, noindex=True), encoding="utf-8")

def make_og():
    f = ROOT / "assets" / "og-image.png"
    if f.exists(): return
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return
    im = Image.new("RGB", (1200, 630), (15, 118, 110))
    dr = ImageDraw.Draw(im)
    def font(sz):
        for n in ("malgunbd.ttf", "malgun.ttf", "NanumGothicBold.ttf", "AppleSDGothicNeo.ttc"):
            try: return ImageFont.truetype(n, sz)
            except Exception: pass
        return ImageFont.load_default()
    dr.rounded_rectangle((90, 90, 1110, 540), 40, fill=(255, 255, 255))
    dr.text((150, 150), "우아달력", font=font(110), fill=(17, 94, 89))
    dr.text((150, 300), "공휴일 · 음력 · 24절기", font=font(56), fill=(31, 41, 55))
    dr.text((150, 380), "손 없는 날 · 이사 · 결혼 · 개업 길일", font=font(56), fill=(31, 41, 55))
    dr.text((150, 470), "wooacal.wooahouse.com", font=font(34), fill=(107, 114, 128))
    im.save(f)

# ───────────────────────── 실행 ─────────────────────────
def clean():
    for d in ROOT.iterdir():
        if d.is_dir() and (d.name.isdigit() or d.name in ("date", "jeolgi", "sonnopneun-nal", "imsa", "gyeolhon", "gaeop", "umnyeok", "about", "privacy")):
            shutil.rmtree(d)

def main():
    clean()
    write_assets()
    page_home(); page_about(); page_privacy()
    for y in YEARS:
        page_year(y)
        for k in C.HORDER: page_holiday(y, k)
        for m in range(1, 13): page_month(y, m)
        page_jeolgi_year(y)
        page_son_year(y)
        for m in range(1, 13): page_son_month(y, m)
        page_umnyeok_year(y)
        for p in PURP:
            page_purpose_year(p, y)
            for m in range(1, 13): page_purpose_month(p, y, m)
    page_son_index(); page_jeolgi_index()
    for n in C.TERM_INFO: page_jeolgi_term(n)
    for p in PURP: page_purpose_index(p)
    page_umnyeok_index(); page_seol_chuseok()
    for d in daterange(dt.date(YEARS[0], 1, 1), dt.date(YEARS[-1], 12, 31)): page_date(d)
    # sitemap / robots / CNAME
    today = dt.date.today().isoformat()
    urls = "".join("<url><loc>%s%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>" % (BASE, p, today, pr) for p, pr in WRITTEN)
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls, encoding="utf-8")
    (ROOT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE, encoding="utf-8")
    (ROOT / "CNAME").write_text("wooacal.wooahouse.com\n", encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    make_404(); make_og()
    (ROOT / ".gitignore").write_text("__pycache__/\n*.pyc\n.env\n", encoding="utf-8")
    print("pages:", len(WRITTEN))

if __name__ == "__main__":
    main()
