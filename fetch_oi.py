#!/usr/bin/env python3
"""
GIFT Nifty OI - daily fetcher for an automated repo.
Fetches the latest 'Index Combined OI' file(s) from NSE IX and appends any
missing recent days to data/oi_master.csv (deduped by date).
Standard library only.
"""
import os, csv, sys, time, datetime as dt
import urllib.request, http.cookiejar

ROOT   = os.path.dirname(os.path.abspath(__file__))
DATA   = os.path.join(ROOT, "data")
RAW    = os.path.join(DATA, "raw")
MASTER = os.path.join(DATA, "oi_master.csv")
BASE   = "https://www.nseix.com/api/content/daily_report"
PAGE   = "https://www.nseix.com/markets/reports"
UA     = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/124 Safari/537.36")
MINSIZE = 5000
LOOKBACK = 12

os.makedirs(RAW, exist_ok=True)
_cj = http.cookiejar.CookieJar()
_op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cj))
_op.addheaders = [("User-Agent", UA), ("Referer", PAGE)]

def warm():
    try: _op.open(PAGE, timeout=30).read()
    except Exception: pass

def recent_weekdays(n):
    d, out = dt.date.today(), []
    while len(out) < n:
        if d.weekday() < 5: out.append(d)
        d -= dt.timedelta(days=1)
    return out

def download(day):
    ds = day.strftime("%d%m%Y")
    url = f"{BASE}/G_COMBINED_OI_{ds}.csv"
    path = os.path.join(RAW, f"G_COMBINED_OI_{ds}.csv")
    if os.path.exists(path) and os.path.getsize(path) > MINSIZE:
        return path
    for a in range(3):
        try:
            data = _op.open(url, timeout=40).read()
            if len(data) > MINSIZE:
                open(path, "wb").write(data); return path
        except Exception as e:
            print(f"  {ds}: attempt {a+1} failed: {e}")
        time.sleep(5 * (a + 1))
    return None

def parse(path):
    rows = list(csv.reader(open(path, encoding="utf-8", errors="ignore")))
    date = rows[0][0]; fut = {}
    for r in rows[1:]:
        if len(r) >= 7 and r[0] == "FUTIDX" and r[1] == "NIFTY":
            v = r[6].strip().lstrip("-"); fut[r[2]] = int(v) if v.isdigit() else 0
    return (date, fut) if fut else (None, None)

def seen():
    if not os.path.exists(MASTER): return set()
    return {r["date"] for r in csv.DictReader(open(MASTER))}

def append(date, total):
    new = not os.path.exists(MASTER)
    with open(MASTER, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(["date", "nifty_fut_total_oi"])
        w.writerow([date, total])

def main():
    warm()
    days = ([dt.datetime.strptime(sys.argv[1], "%d%m%Y").date()]
            if len(sys.argv) > 1 else recent_weekdays(LOOKBACK))
    have = seen()
    added = 0
    for day in days:
        p = download(day)
        if not p: continue
        date, fut = parse(p)
        if not date or date in have:
            continue                     # already have it - keep filling older gaps
        total = sum(fut.values())
        append(date, total)
        have.add(date); added += 1
        print(f"{date}: appended NIFTY futures OI = {total:,}")
    print(f"done - added {added} new row(s); master has {len(have)} dates")

if __name__ == "__main__":
    main()
