# -*- coding: utf-8 -*-
"""생성 결과 점검: 내부 링크 깨짐, 제목/설명 중복·길이, JSON-LD 유효성, 사이트맵 일치."""
import re, sys, json, pathlib, collections
sys.stdout.reconfigure(encoding="utf-8")
root = pathlib.Path(__file__).resolve().parent.parent
files = [p for p in root.rglob("index.html") if "scripts" not in p.parts] + [root / "404.html"]
broken = collections.Counter(); titles = collections.defaultdict(list); descs = collections.defaultdict(list)
tl, dl = [], []
badld = 0
for f in files:
    t = f.read_text(encoding="utf-8")
    rel = "/" + "/".join(f.relative_to(root).parts[:-1]) + "/" if f.name == "index.html" else "/404.html"
    rel = rel.replace("//", "/")
    for h in re.findall(r'href="(/[^"#?]*)', t):
        if h.startswith("//"): continue
        tgt = root / h.strip("/")
        if h.endswith("/"):
            ok = (tgt / "index.html").exists() if h != "/" else (root / "index.html").exists()
        else:
            ok = tgt.exists()
        if not ok: broken[h] += 1
    m = re.search(r"<title>(.*?)</title>", t); ti = m.group(1)
    d = re.search(r'name="description" content="(.*?)"', t).group(1)
    titles[ti].append(rel); descs[d].append(rel)
    tl.append(len(ti)); dl.append(len(d))
    for ld in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
        try: json.loads(ld)
        except Exception: badld += 1
print("파일", len(files), "깨진 링크", len(broken), list(broken.items())[:10])
print("중복 title", sum(1 for v in titles.values() if len(v) > 1), "중복 description", sum(1 for v in descs.values() if len(v) > 1))
for k, v in list(titles.items()):
    if len(v) > 1: print("  dup title:", k, v[:3]); break
print("title 길이 최대/평균", max(tl), sum(tl) // len(tl), "description 최대/평균", max(dl), sum(dl) // len(dl))
print("JSON-LD 오류", badld)
sm = (root / "sitemap.xml").read_text(encoding="utf-8")
urls = re.findall(r"<loc>https://wooacal.wooahouse.com(.*?)</loc>", sm)
missing = [u for u in urls if not ((root / u.strip("/") / "index.html").exists() if u != "/" else (root / "index.html").exists())]
print("sitemap URL", len(urls), "누락 파일", len(missing))
print("josa 미해결", sum(1 for f in files if re.search(r"이\(가\)|은\(는\)|을\(를\)|과\(와\)", f.read_text(encoding="utf-8").split("<footer")[0].split("<main")[1] if "<main" in f.read_text(encoding="utf-8") else "")))
