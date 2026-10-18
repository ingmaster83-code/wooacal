# -*- coding: utf-8 -*-
"""우아달력 공용: 상수, 날짜 정보 캐시, 레이아웃(헤더/푸터/광고/FAQ/JSON-LD)."""
import datetime as dt, html, json
from pathlib import Path
import engine as E

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://wooacal.wooahouse.com"
SITE = "우아달력"
YEARS = [2026, 2027, 2028, 2029, 2030]
NAVER_TOKEN = ""          # 네이버 서치어드바이저 메타태그 값(사용자 발급) — 있으면 head 에 삽입
TODAY_STAMP = "2026년 10월"  # 푸터 최종 수정 표기

esc = html.escape
WDK = ["월", "화", "수", "목", "금", "토", "일"]

def wd(d): return WDK[d.weekday()]
def fmt(d, y=True):
    return ("%d년 " % d.year if y else "") + "%d월 %d일" % (d.month, d.day)
def fmtw(d, y=True): return fmt(d, y) + "(%s)" % wd(d)
def url_date(d): return "/date/%s/" % d.isoformat()

_info = {}
def info(d):
    if d in _info: return _info[d]
    ly, lm, ld, leap = E.lunar_of(d)
    i = E.day_index(d)
    h = E.holiday_on(d)
    term = None
    for yy in (d.year,):
        for t in E.terms_of_year(yy):
            if t["at"].date() == d: term = t
    r = dict(d=d, ly=ly, lm=lm, ld=ld, leap=leap, gz=E.ganzhi(i), gzh=E.ganzhi_h(i), animal=E.ANIMAL[i % 12],
             sh=E.shin12_of(d), hw=E.hwangdo_of(d), son=(ld % 10 in (9, 0)), hol=h, term=term,
             off=(d.weekday() >= 5 or h is not None))
    r["lunar_str"] = ("윤" if leap else "") + "%d월 %d일" % (lm, ld)
    _info[d] = r
    return r

def son_dir(ld):
    n = ld % 10
    if n in (1, 2): return "동쪽"
    if n in (3, 4): return "남쪽"
    if n in (5, 6): return "서쪽"
    if n in (7, 8): return "북쪽"
    return None

def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)

def off_block(d):
    """d 를 포함하는 연속 휴일(주말+공휴일) 구간 (시작, 끝)"""
    a = d
    while info(a - dt.timedelta(days=1))["off"]: a -= dt.timedelta(days=1)
    b = d
    while info(b + dt.timedelta(days=1))["off"]: b += dt.timedelta(days=1)
    return a, b

def ad(label=""):
    return ('<div class="ad-slot"><ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-6464921081676309" '
            'data-ad-slot="7080296704" data-ad-format="auto" data-full-width-responsive="true"></ins>'
            '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div>')

COUPANG = ('<div class="coupang-partners" style="margin:36px auto 0;max-width:720px;padding:0 16px 8px;text-align:center;overflow-x:auto;">'
           '<script src="https://ads-partners.coupang.com/g.js"></script>'
           '<script>new PartnersCoupang.G({"id":980427,"trackingCode":"AF5600192","subId":"cal","template":"carousel","width":"680","height":"140"});</script>'
           '</div>')
COUPANG_NOTE = '<p style="margin:6px 0 0;font-size:.7rem;opacity:.55;">이 페이지는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>'

NAV = [("공휴일", "/%d/" % YEARS[1]), ("달력", "/%d/01/" % YEARS[1]), ("손 없는 날", "/sonnopneun-nal/"),
       ("이사", "/imsa/"), ("결혼", "/gyeolhon/"), ("개업", "/gaeop/"), ("24절기", "/jeolgi/"), ("음력변환", "/umnyeok/")]

import re
_JOSA = re.compile(r'([가-힣0-9\)])((?:</[a-z]+>)*)(이\(가\)|은\(는\)|을\(를\)|과\(와\))')
_DIG = {"0": True, "1": True, "2": False, "3": True, "4": False, "5": False, "6": True, "7": True, "8": True, "9": False}
def _has_batchim(s, end):
    """s[end] 는 조사 앞 글자(또는 ')')의 위치"""
    c = s[end]
    if c == ")":
        k = s.rfind("(", 0, end)
        if k > 0: return _has_batchim(s, k - 1)
        return False
    if c in _DIG: return _DIG[c]
    return (ord(c) - 0xAC00) % 28 != 0
def josa(t):
    def f(m):
        has = _has_batchim(m.string, m.start(1))
        pair = m.group(3)
        a, b = pair[0], pair[2]
        return m.group(1) + m.group(2) + (a if has else b)
    return _JOSA.sub(f, t)

def layout(path, title, desc, body, faq=None, crumbs=None, kind="website", extra_ld=None, coupang=False, noindex=False):
    """path: '/2027/' 형태의 정규 경로. 반환: 완성된 HTML"""
    canon = BASE + path
    title, desc, body = josa(title), josa(desc), josa(body)
    if faq: faq = [(josa(q), josa(a)) for q, a in faq]
    full_title = title if title.endswith(SITE) or path == "/" else title + " | " + SITE
    ld = []
    if crumbs:
        items = [{"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + u} for i, (n, u) in enumerate(crumbs)]
        ld.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items})
    if faq:
        ld.append({"@context": "https://schema.org", "@type": "FAQPage",
                   "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]})
    if extra_ld: ld += extra_ld
    ld_html = "".join('<script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False) for x in ld)
    nav = "".join('<a href="%s">%s</a>' % (u, n) for n, u in NAV)
    crumb_html = ""
    if crumbs:
        crumb_html = '<nav class="breadcrumb" aria-label="위치">' + ' <span>›</span> '.join(
            ('<a href="%s">%s</a>' % (u, esc(n))) if i < len(crumbs) - 1 else '<span>%s</span>' % esc(n)
            for i, (n, u) in enumerate(crumbs)) + '</nav>'
    faq_html = ""
    if faq:
        faq_html = '<div class="faq-block"><h2>자주 묻는 질문</h2>' + "".join(
            '<details><summary>%s</summary><p>%s</p></details>' % (esc(q), esc(a)) for q, a in faq) + '</div>'
    naver = '<meta name="naver-site-verification" content="%s" />' % NAVER_TOKEN if NAVER_TOKEN else ""
    robots = '<meta name="robots" content="noindex,follow">' if noindex else ""
    return """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%(title)s</title>
<meta name="description" content="%(desc)s">
%(naver)s%(robots)s
<link rel="canonical" href="%(canon)s">
<meta property="og:type" content="%(kind)s">
<meta property="og:title" content="%(title)s">
<meta property="og:description" content="%(desc)s">
<meta property="og:url" content="%(canon)s">
<meta property="og:site_name" content="우아달력">
<meta property="og:image" content="%(base)s/assets/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/main.css?v=1">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-9ZGENFSXWC"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-9ZGENFSXWC');</script>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6464921081676309" crossorigin="anonymous"></script>
%(ld)s
</head>
<body>
<header class="site-header"><div class="header-inner">
<a href="/" class="site-logo"><span class="logo-icon">🗓️</span><span class="logo-text">우아달력</span></a>
<nav class="header-nav">%(nav)s</nav></div></header>
<script src="/assets/js/wooa-sites-bar.js"></script>
<script src="/assets/js/ad-dev-placeholder.js"></script>
<main class="site-main">
<div class="page-with-sidebar">
<div class="cal-page">
%(crumb)s
%(body)s
%(faq)s
</div>
<aside class="tool-sidebar"></aside>
</div>
</main>
<script src="/assets/js/wooa-sidebar.js"></script>
%(coupang)s
<footer class="site-footer"><div class="footer-inner">
<p class="footer-disclaimer">달력 정보는 한국천문연구원 음양력 자료와 태양 시황경 계산, 「관공서의 공휴일에 관한 규정」을 바탕으로 계산한 참고용 정보입니다. 임시공휴일 등 정부 발표로 달라질 수 있으니 중요한 일정은 우주항공청·한국천문연구원 월력요항과 정부 공고로 다시 확인하세요. 손 없는 날·택일은 민간에 전해 내려오는 풍습이며 과학적 근거가 있는 것은 아닙니다.</p>
<p class="footer-links"><a href="https://wooahouse.com">WooaHouse</a> · <a href="https://wooaunse.wooahouse.com">우아운세</a> · <a href="https://wooatown.wooahouse.com">우아동네</a> · <a href="https://wooaapt.wooahouse.com">우아아파트</a> · <a href="/about/">계산 기준</a> · <a href="/privacy/">개인정보처리방침</a></p>
<p class="copyright">&copy; 2026 우아달력 · WooaHouse. All rights reserved.</p>
%(cnote)s
</div></footer>
</body>
</html>
""" % dict(title=esc(full_title), desc=esc(desc), naver=naver, robots=robots, canon=canon, kind=kind, base=BASE,
           ld=ld_html, nav=nav, crumb=crumb_html, body=body, faq=faq_html,
           coupang=COUPANG if coupang else "", cnote=COUPANG_NOTE if coupang else "")

WRITTEN = []   # (path, priority, lastmod)
def write(path, html_text, prio="0.6", sitemap=True):
    out = ROOT / path.strip("/") / "index.html" if path != "/" else ROOT / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_text, encoding="utf-8")
    if sitemap: WRITTEN.append((path, prio))
