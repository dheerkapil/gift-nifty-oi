# GIFT Nifty OI — automated daily fetch

Runs `fetch_oi.py` on a schedule, appends the day's NIFTY futures open
interest to `data/oi_master.csv`, and commits it back to the repo.

## Setup (5 minutes)
1. Create a GitHub repo and drop these files in (keep the `.github/workflows/` path).
2. Repo → **Settings → Actions → General → Workflow permissions → Read and write**. Save.
3. Repo → **Actions → gift-oi-daily → Run workflow**. This first manual run is the
   reachability test: if `data/oi_master.csv` appears with today's OI, the runner
   can reach nseix.com and you're done — it will then run itself every weekday.

## If the test run fails
The GitHub runner's cloud IP is probably blocked by NSE IX. Fall back to running
`fetch_oi.py` on your own machine:
- **Windows:** Task Scheduler → daily → `python fetch_oi.py`
- **Linux/VPS:** cron → `30 19 * * 1-5 python3 /path/fetch_oi.py`

Either way, once `data/oi_master.csv` is being updated, point the analyst at the
repo and no manual downloads are needed again.
