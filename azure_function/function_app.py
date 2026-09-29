import io
import logging
import os
from datetime import date, timedelta

import azure.functions as func
import pandas as pd
import requests
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()

CONTAINER = "palm-oil-data"


# ---------- Blob Storage helpers ----------
def container():
    service = BlobServiceClient.from_connection_string(os.environ["DATA_STORAGE"])
    return service.get_container_client(CONTAINER)

def read_blob(name):
    return container().download_blob(name).readall()

def write_csv(df, name):
    container().upload_blob(name, df.to_csv(index=False), overwrite=True)


# ---------- Data sources (same logic as the notebook) ----------
def load_price():
    xlsx = io.BytesIO(read_blob("raw/CMO-Historical-Data-Monthly.xlsx"))
    raw = pd.read_excel(xlsx, sheet_name="Monthly Prices", header=None)
    hdr = raw.index[raw.apply(lambda r: r.astype(str).str.contains("Palm oil").any(), axis=1)][0]
    xlsx.seek(0)
    price = pd.read_excel(xlsx, sheet_name="Monthly Prices", header=hdr)
    price.columns = price.columns.astype(str).str.strip()
    price = price.rename(columns={price.columns[0]: "month"})[["month", "Palm oil"]]
    price = price[price["month"].astype(str).str.match(r"\d{4}M\d{2}")].copy()
    price["date"] = pd.to_datetime(price["month"].str.replace("M", "-") + "-01")
    price = price[["date", "Palm oil"]].rename(columns={"Palm oil": "price_usd"})
    price["price_usd"] = pd.to_numeric(price["price_usd"], errors="coerce")
    return price[price["date"] >= "2015-01-01"]

def load_rain():
    end = (date.today() - timedelta(days=7)).isoformat()   # archive data lags a few days
    url = ("https://archive-api.open-meteo.com/v1/archive"
           "?latitude=5.84&longitude=118.12"
           f"&start_date=2015-01-01&end_date={end}"
           "&daily=precipitation_sum&timezone=Asia/Kuala_Lumpur")
    d = requests.get(url, timeout=60).json()["daily"]
    rain = pd.DataFrame({"date": pd.to_datetime(d["time"]), "rain_mm": d["precipitation_sum"]})
    rain = rain.resample("MS", on="date").sum().reset_index()
    rain["rain_mm"] = rain["rain_mm"].round(1)
    return rain

def load_mpob():
    raw = pd.read_csv(io.BytesIO(read_blob("raw/mpob_raw.csv")))
    mpob = raw[raw["indicator"].isin(["cpo_production", "total_po_stock"])]
    mpob = mpob.pivot_table(index="month", columns="indicator", values="value", aggfunc="last").reset_index()
    mpob = mpob.rename(columns={"month": "date", "cpo_production": "production_t", "total_po_stock": "stocks_t"})
    mpob["date"] = pd.to_datetime(mpob["date"])
    mpob = mpob[mpob["date"] >= "2015-01-01"]

    fill = pd.read_csv(io.BytesIO(read_blob("raw/production_backfill.csv")), parse_dates=["date"])
    mpob = mpob.set_index("date")
    mpob["production_t"] = mpob["production_t"].fillna(fill.set_index("date")["production_t"])
    return mpob.reset_index()


# ---------- The scheduled job ----------
# NCRONTAB: second minute hour day month day-of-week  ->  02:00 UTC on the 12th of every month
@app.timer_trigger(schedule="0 0 2 12 * *", arg_name="timer", run_on_startup=False, use_monitor=False)
def refresh_palm_oil_data(timer: func.TimerRequest) -> None:
    df = load_price().merge(load_rain(), on="date").merge(load_mpob(), on="date", how="left")
    write_csv(df, "processed/palm_oil_monthly.csv")
    logging.info("Refreshed palm_oil_monthly.csv: %d rows, latest month %s, missing values %d",
                 len(df), df["date"].max().date(), int(df.isna().sum().sum()))
