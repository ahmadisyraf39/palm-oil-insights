"""Monthly refresh of the palm oil dataset.

Reads raw files from Azure Blob Storage, fetches the latest rainfall from Open-Meteo,
repeats the notebook's cleaning and merge steps, and writes the processed dataset
back to Blob Storage for the Power BI dashboard.

Runs on a schedule via GitHub Actions (.github/workflows/monthly-refresh.yml).
"""
import io
import os
from datetime import date, timedelta

import pandas as pd
import requests
from azure.storage.blob import BlobServiceClient

CONTAINER = "palm-oil-data"


# ---------- Blob Storage helpers ----------
def container():
    # Connection string comes from a GitHub secret, never from the code
    service = BlobServiceClient.from_connection_string(os.environ["AZURE_CONN_STR"])
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
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    d = resp.json()["daily"]
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


def main():
    df = load_price().merge(load_rain(), on="date").merge(load_mpob(), on="date", how="left")
    write_csv(df, "processed/palm_oil_monthly.csv")
    print(f"Refreshed palm_oil_monthly.csv: {len(df)} rows, "
          f"latest month {df['date'].max().date()}, missing values {int(df.isna().sum().sum())}")


if __name__ == "__main__":
    main()
