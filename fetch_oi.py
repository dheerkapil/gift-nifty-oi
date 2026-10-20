#!/usr/bin/env python3
"""
GIFT Nifty OI fetcher + Nifty underlying, for the automated repo.

Hourly 17:00-23:00 IST (Mon-Fri):
  * weekends / coded holidays -> do nothing
  * if today's OI row is already in the master -> do nothing
  * otherwise fetch today's 'Index Combined OI' AND the 'Underlying Price'
    file (NIFTY), append both, then backfill older gaps
Both files come from nseix.com, so there is no external price dependency.
"""
import os, csv, sys, time, datetime as dt
import urllib.request, http.cookiejar

ROOT   = os.path.dirname(os.path.abspath(__file__))
DATA   = os.path.join(ROOT, "data")
RAW    = os.path.join(DATA, "raw")
MASTER = os.path.join(DATA, "oi_master.csv")
NIFTY  = os.path.join(DATA, "nifty_daily.csv")
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
            if line:
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

def _get(url, path, minsize):
    if os.path.exists(path) and os.path.getsize(path) > minsize:
        return path
    for a in range(3):
        try:
            data = _op.open(url, timeout=40).read()
            if len(data) > minsize:
                open(path, "wb").write(data); return path
        except Exception:
            time.sleep(5 * (a + 1))
    return None

def get_oi(day):
    ds = day.strftime("%d%m%Y")
    return _get(f"{BASE}/G_COMBINED_OI_{ds}.csv",
                os.path.join(RAW, f"G_COMBINED_OI_{ds}.csv"), MINSIZE)

def get_ul(day):
    ds = day.strftime("%d%m%Y")
    return _get(f"{BASE}/G_T1_UL_PRICE_{ds}.csv",
                os.path.join(RAW, f"G_T1_UL_PRICE_{ds}.csv"), 100)

def parse_oi(path):
    rows = list(csv.reader(open(path, encoding="utf-8", errors="ignore")))
    date = canon(rows[0][0]); fut = {}
    for r in rows[1:]:
        if len(r) >= 7 and r[0] == "FUTIDX" and r[1] == "NIFTY":
            v = r[6].strip().lstrip("-"); fut[r[2]] = int(v) if v.isdigit() else 0
    return (date, fut) if fut else (None, None)

def parse_ul(path):
    for r in csv.reader(open(path, encoding="utf-8", errors="ignore")):
        if len(r) >= 3 and r[1].strip().upper() == "NIFTY":
            try: return canon(r[0]), float(r[2])
            except Exception: return None, None
    return None, None

def seen(path, col):
    if not os.path.exists(path): return set()
    return {canon(r["date"]) for r in csv.DictReader(open(path))}

def append(path, header, row):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(header)
        w.writerow(row)

def do_day(day, have_oi, have_nx):
    """fetch + append one day's OI and Nifty; return (oi_added, nifty_added)."""
    added = [0, 0]
    p = get_oi(day)
    if p:
        date, fut = parse_oi(p)
        if date and date not in have_oi:
            append(MASTER, ["date", "nifty_fut_total_oi"], [date, sum(fut.values())])
            have_oi.add(date); added[0] = 1
            print(f"{date}: OI {sum(fut.values()):,}")
    q = get_ul(day)
    if q:
        date, val = parse_ul(q)
        if date and date not in have_nx:
            append(NIFTY, ["date", "nifty"], [date, val])
            have_nx.add(date); added[1] = 1
            print(f"{date}: nifty {val}")
    return added

def main():
    today = ist_today()
    if today.weekday() >= 5:
        print(f"{today} is a weekend - nothing to do"); return
    if today in load_holidays():
        print(f"{today} is a coded holiday - no run"); return
    have_oi = seen(MASTER, "date")
    have_nx = seen(NIFTY, "date")
    if canon(today.strftime("%d-%b-%Y")) in have_oi and canon(today.strftime("%d-%b-%Y")) in have_nx:
        print(f"already have {today} - no further fetches today"); return

    warm()
    a = do_day(today, have_oi, have_nx)
    if a == [0, 0]:
        print(f"{today}: not published yet - the next hourly run will retry"); return
    hol = load_holidays()
    for day in recent_weekdays(LOOKBACK):
        if day == today or day.weekday() >= 5 or day in hol: continue
        do_day(day, have_oi, have_nx)
    print(f"done - master {len(have_oi)} dates, nifty {len(have_nx)} dates")

if __name__ == "__main__":
    main()
