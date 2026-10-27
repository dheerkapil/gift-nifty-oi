#!/usr/bin/env python3
"""Hourly availability probe for the NSE IX daily GIFT Nifty report files.

It answers one question per hour: does the file for a given trading date exist
yet, and how big is it?  It never downloads the report - it sends a ranged
request for a single byte and reads only the response headers, then closes the
connection without touching the body.

The first time a file for a date is seen, one row is appended to
data/probe_log.csv with the IST and UTC timestamps, so publication times can be
reconstructed afterwards without keeping per-run noise in git.  Every check is
also written to the Actions step summary for the record.

Self-expiring: no-ops once the IST date passes PROBE_UNTIL.
"""
import csv
import datetime as dt
import http.cookiejar
import os
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "data", "probe_log.csv")
BASE = "https://www.nseix.com/api/content/daily_report"
PAGE = "https://www.nseix.com/markets/reports"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124 Safari/537.36")

# (file prefix, minimum plausible size in bytes)
FILES = [("G_COMBINED_OI", 5000), ("G_T1_UL_PRICE", 100)]
LOOKBACK = 6                      # today + 5 previous weekdays
PROBE_UNTIL = dt.date(2026, 11, 3)  # stop after this IST date
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

_cj = http.cookiejar.CookieJar()
_op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cj))
_op.addheaders = [("User-Agent", UA), ("Referer", PAGE)]


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


def probe(url):
    """Return (status, size_bytes, last_modified). The body is never read."""
    req = urllib.request.Request(url, headers={"Range": "bytes=0-0",
                                               "Accept": "*/*"})
    try:
        resp = _op.open(req, timeout=40)
    except urllib.error.HTTPError as exc:
        hdr = exc.headers or {}
        return exc.code, None, hdr.get("Last-Modified", "")
    except Exception as exc:                       # network / proxy problems
        return "ERR:" + type(exc).__name__, None, ""
    status, hdr = resp.status, resp.headers
    size = None
    content_range = hdr.get("Content-Range", "")   # e.g. "bytes 0-0/123456"
    if "/" in content_range:
        tail = content_range.rsplit("/", 1)[1].strip()
        if tail.isdigit():
            size = int(tail)
    if size is None:
        length = (hdr.get("Content-Length") or "").strip()
        if length.isdigit():
            size = int(length)
    last_modified = hdr.get("Last-Modified", "")
    resp.close()                                   # body deliberately unread
    return status, size, last_modified


def recent_weekdays(n):
    day = utcnow().astimezone(IST).date()
    out = []
    while len(out) < n:
        if day.weekday() < 5:
            out.append(day)
        day -= dt.timedelta(days=1)
    return out


def main():
    stamp = utcnow()
    today_ist = stamp.astimezone(IST).date()
    if today_ist > PROBE_UNTIL:
        print("probe window closed on %s - nothing to do" % PROBE_UNTIL)
        return 0

    try:                                           # warm cookies like fetch_oi
        _op.open(PAGE, timeout=30).read(2000)
    except Exception:
        pass

    known = set()
    if os.path.exists(LOG):
        with open(LOG, newline="") as fh:
            for row in csv.DictReader(fh):
                known.add((row.get("file_date", ""), row.get("kind", "")))

    table = ["| file | status | size (bytes) | last-modified | state |",
             "|---|---|---|---|---|"]
    fresh = []
    for day in recent_weekdays(LOOKBACK):
        code = day.strftime("%d%m%Y")
        label = day.strftime("%d-%b-%Y")
        for prefix, min_size in FILES:
            status, size, last_modified = probe("%s/%s_%s.csv" % (BASE, prefix, code))
            present = (isinstance(status, int) and status in (200, 206)
                       and (size or 0) >= min_size)
            state = ""
            if present and (label, prefix) not in known:
                fresh.append([label, prefix,
                              stamp.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S"),
                              stamp.strftime("%Y-%m-%d %H:%M:%S"),
                              status, size, last_modified])
                state = "**NEW**"
            elif present:
                state = "already logged"
            table.append("| %s %s | %s | %s | %s | %s |"
                         % (label, prefix, status, size, last_modified, state))
            print("%s %s: status=%s size=%s lm=%s %s"
                  % (label, prefix, status, size, last_modified, state))

    if fresh:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        new_file = not os.path.exists(LOG)
        with open(LOG, "a", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            if new_file:
                writer.writerow(["file_date", "kind", "first_seen_ist",
                                 "first_seen_utc", "status", "size",
                                 "last_modified"])
            writer.writerows(fresh)
        print("logged %d new file(s)" % len(fresh))
    else:
        print("no newly published file this hour")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as fh:
            fh.write("### OI probe - %s IST\n\n"
                     % stamp.astimezone(IST).strftime("%d-%b-%Y %H:%M"))
            fh.write("\n".join(table) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
