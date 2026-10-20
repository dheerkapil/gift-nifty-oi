# GIFT Nifty OI

Automated tracking of **GIFT Nifty (NSE IX) futures open interest**, with a chart
pushed to Telegram. Two years of daily history, all sourced from NSE IX.

## How it runs
`fetch_oi.py` is scheduled **hourly 17:00-23:00 IST, Mon-Fri**:
- skips weekends and coded holidays (`data/holidays.txt`)
- fetches the day's `G_COMBINED_OI_<DDMMYYYY>.csv` (open interest) **and**
  `G_T1_UL_PRICE_<DDMMYYYY>.csv` (NIFTY underlying)
- appends to `data/oi_master.csv` and `data/nifty_daily.csv` (deduped by date)
- once the day's rows are in, later runs that day fetch nothing
- backfills any missed recent weekdays (12-day look-back)

`plot_chart.py` then builds `chart.png` - GIFT futures OI vs Nifty 50 spot.
Width scales with the data length (~0.052 in/day): ~13 in for a year, ~26 in for two.
It refuses to emit a chart with fewer than 30 points.

On days new data lands, the chart is posted to Telegram (Bot API).

`refresh_holidays.py` refreshes the holiday list from NSE IX weekly.

## Files
| file | purpose |
|---|---|
| `data/oi_master.csv` | OI series: `date,nifty_fut_total_oi` (two years) |
| `data/nifty_daily.csv` | Nifty 50 closes: `date,nifty` (two years) |
| `data/holidays.txt` | NSE IX trading closures |
| `fetch_oi.py` | daily fetcher (OI + Nifty) |
| `plot_chart.py` | chart builder |
| `resolve_chat.py` | Telegram chat-id resolver |
| `refresh_holidays.py` | weekly holiday refresh |
| `.github/workflows/gift-oi.yml` | hourly job |
| `.github/workflows/refresh-holidays.yml` | weekly holiday job |

## Secrets
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Notes
- Everything comes from **nseix.com** (OI + underlying), so there is no external
  price dependency - Yahoo returns garbage to cloud runners.
- Raw NSE IX files are **not** committed (`.gitignore`); only the derived series
  is kept, so the repo stays tiny.
- If the holiday list is ever wrong, the 12-weekday backfill self-heals it.
