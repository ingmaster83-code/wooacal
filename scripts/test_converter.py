# -*- coding: utf-8 -*-
import json, sys, datetime as dt, pathlib
sys.stdout.reconfigure(encoding="utf-8")
here = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(here))
import engine as E
js = json.load(open(here / "_js_out.json", encoding="utf-8"))
bad = 0
for y, m, d, ly, lm, ld, lp in js:
    r = E.lunar_of(dt.date(y, m, d))
    if r != (ly, lm, ld, bool(lp)):
        bad += 1
        if bad < 5: print("불일치", y, m, d, "py", r, "js", (ly, lm, ld, lp))
print("py vs js 불일치", bad, "/", len(js))
