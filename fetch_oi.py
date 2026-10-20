#!/usr/bin/env python3
"""
GIFT Nifty OI - daily fetcher (scheduled hourly 17:00-23:00 IST).
Logic:
  * weekends and coded holidays -> do nothing
  * if today's row already in the master -> do nothing  (so once we have the
    day's file, later runs that day fetch nothing)
  * otherwise try today's file; if it isn't published yet, exit quietly and
    let the next hourly run try again
  * on success, also backfill any older missing weekdays
Standard library only.
"""
import os, csv, sys, time, datetime as dt
import urllib.request, http.cookiejar

ROOT   = os.path.dirname(os.path.abspath(__file__))
DATA   = os.path.join(ROOT, "data")
RAW    = os.path.join(DATA, "raw")
MASTER = os.path.join(DATA, "oi_master.csv")
HOLID  = os.path.join(DATA, "holidays.txt")
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

def ist_today():
    return (dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)).date()

def canon(s):
    try: return dt.datetime.strptime(s.strip(), "%d-%b-%Y").strftime("%d-%b-%Y")
    except Exception: return s.strip()

def load_holidays():
    hol = set()
    if os.path.exists(HOLID):
        for line in open(HOLID):
            line = line.split("#")[0].strip()
            if not line: continue
            try: hol.add(dt.datetime.strptime(line, "%d-%b-%Y").date())
            except Exception: pass
    return hol

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
        except Exception:
            time.sleep(5 * (a + 1))
    return None

def parse(path):
    rows = list(csv.reader(open(path, encoding="utf-8", errors="ignore")))
    date = canon(rows[0][0]); fut = {}
    for r in rows[1:]:
        if len(r) >= 7 and r[0] == "FUTIDX" and r[1] == "NIFTY":
            v = r[6].strip().lstrip("-"); fut[r[2]] = int(v) if v.isdigit() else 0
    return (date, fut) if fut else (None, None)

def seen():
    if not os.path.exists(MASTER): return set()
    return {canon(r["date"]) for r in csv.DictReader(open(MASTER))}

def append(date, total):
    new = not os.path.exists(MASTER)
    with open(MASTER, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(["date", "nifty_fut_total_oi"])
        w.writerow([date, total])

def main():
    today = ist_today()
    if today.weekday() >= 5:
        print(f"{today} is a weekend - nothing to do"); return
    if today in load_holidays():
        print(f"{today} is a coded holiday - no run"); return
    have = seen()
    if canon(today.strftime("%d-%b-%Y")) in have:
        print(f"already have {today} - no further fetches today"); return

    warm()
    p = download(today)
    if not p:
        print(f"{today}: not published yet - the next hourly run will retry"); return
    date, fut = parse(p)
    if not date:
        print(f"{today}: file present but unparseable"); return
    append(date, sum(fut.values())); have.add(date)
    print(f"{date}: appended OI {sum(fut.values()):,}")

    # backfill older gaps (bounded, only runs on the day's first success)
    hol = load_holidays()
    for day in recent_weekdays(LOOKBACK):
        if day == today or day.weekday() >= 5 or day in hol: continue
        pp = download(day)
        if not pp: continue
        d2, f2 = parse(pp)
        if d2 and d2 not in have:
            append(d2, sum(f2.values())); have.add(d2)
            print(f"{d2}: backfilled OI {sum(f2.values()):,}")
    print(f"done - master has {len(have)} dates")

if __name__ == "__main__":
    main()
