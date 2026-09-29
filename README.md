# Malaysian Palm Oil Price & Production Insights

An end-to-end data project that combines palm oil prices, Malaysian production and stock data, and rainfall to answer two questions:

1. **What drives Malaysian palm oil supply and prices?**
2. **Can next month's palm oil price be forecast better than a simple baseline?**

Built with Python (pandas, scikit-learn) and Power BI.

![Dashboard overview](dashboard/dashboard_overview.png)

---

## Key findings

| # | Finding | Evidence |
|---|---------|----------|
| 1 | **Strong seasonality:** crude palm oil (CPO) production is lowest in February and peaks in September–October | Peak month is ~51% higher than the lowest month (2015–2026 average) |
| 2 | **Rainfall acts with a delay:** production is most strongly linked to rainfall about **10 months earlier** | r = 0.52 at a 10-month lag (part of this may reflect shared seasonality) |
| 3 | **Stocks weigh on prices:** higher closing stocks are associated with lower prices the following month | r = −0.42 |
| 4 | **Forecasting:** a Random Forest predicting monthly price changes beats a naive baseline by **~9.5%** | MAE USD 35.1 vs 38.8 per tonne (2024–2026 test period) |

---

## Forecast results

The model predicts **next month's price change** using only information available at the time (last month's price change, stock level and change, production, and rainfall lagged 10 months). The data was split by time: trained on **2015–2023 (98 months)** and tested on **Jan 2024 – Aug 2026 (32 months)** that the model never saw.

| Model | MAE (USD/tonne) | vs naive baseline |
|-------|-----------------|-------------------|
| Naive baseline (next month = this month) | 38.8 | – |
| Linear Regression | 35.8 | 7.7% better |
| **Random Forest** | **35.1** | **9.5% better** |

**Interpretation:** the improvement is real but modest, as expected for commodity prices, which are driven by many global factors not in this dataset (e.g. crude oil prices, soybean oil, export policies, the 2022 supply shock).

**Built-in forecast comparison:** Power BI's forecast (exponential smoothing on price history only), backtested over the same period by predicting all 32 months at once, drifted well below actual prices as they rose in 2025–2026. This shows the value of supply-side features and why forecast horizon matters.

![AI insights page](dashboard/dashboard_ai_insights.png)

---

## Approach

```
World Bank prices ─┐
MPOB production &  ├─► Clean & merge (pandas) ─► Analysis ─► Forecast models ─► Power BI dashboard
stocks             │    monthly, 2015–2026        3 business     naive / linear /     2 pages
Open-Meteo rainfall┘                              questions      random forest
```

1. **Data collection and cleaning:** load the World Bank Pink Sheet, locate the header row programmatically, convert `2015M01`-style dates, aggregate daily rainfall to monthly totals, and reshape MPOB data from long to wide format.
2. **Data quality:** the MPOB production series had **76 missing months**. These were backfilled from MPOB's official yearly *Summary of the Malaysian Palm Oil Industry* reports (2015–2020), the Ministry of Plantation and Commodities' *Palm Oil Statistics 2023* (2022), and MPOB monthly report figures (2023). The backfill was validated against MPOB's closing stocks (exact match) and official annual production totals (2022 exact; 2023 within 0.01%).
3. **Analysis:** seasonality by calendar month, lagged correlation between rainfall and production (0–12 months), and stocks vs next month's price.
4. **Forecasting:** feature engineering using only past information (no data leakage), a time-based train/test split, and comparison of three models by mean absolute error.
5. **Dashboard:** a two-page Power BI report with DAX measures (latest price, month-on-month change, stocks, forecast error), a year filter, a forecast backtest, and a stocks-vs-price trend line.

---

## Data sources

| Data | Source | Frequency |
|------|--------|-----------|
| Palm oil price (USD/tonne) | [World Bank Commodity Markets (Pink Sheet)](https://www.worldbank.org/en/research/commodity-markets) | Monthly |
| CPO production and palm oil closing stocks | Malaysian Palm Oil Board (MPOB), via [palmoileconomics.com](https://palmoileconomics.com/data/mpob), backfilled from [MPOB](https://bepi.mpob.gov.my/) and [KPK](https://www.kpk.gov.my/) reports | Monthly |
| Rainfall, Sandakan, Sabah | [Open-Meteo Historical Weather API](https://open-meteo.com/) | Daily, aggregated to monthly |

---

## Repository structure

```
palm-oil-insights/
├── README.md
├── palm_oil_project.ipynb          # data pipeline, analysis and forecasting
├── data/
│   ├── CMO-Historical-Data-Monthly.xlsx
│   ├── mpob_raw.csv
│   ├── production_backfill.csv
│   ├── mpob_production.csv
│   ├── palm_oil_prices_and_rainfall.csv
│   ├── palm_oil_monthly.csv        # final clean dataset
│   └── forecast.csv                # model predictions for 2024–2026
└── dashboard/
    ├── palm_oil_dashboard.pbix
    ├── palm_oil_theme_fhd_dark_text.json
    ├── dashboard_overview.png
    └── dashboard_ai_insights.png
```

---

## How to run

1. Open `palm_oil_project.ipynb` in [Google Colab](https://colab.research.google.com/) (use the **Open in Colab** badge at the top of the notebook).
2. Upload the files from `data/` to your Google Drive folder, or update the `folder` path in the notebook.
3. Run all cells (**Runtime → Run all**).
4. Open `dashboard/palm_oil_dashboard.pbix` in Power BI Desktop (Windows) and refresh the data sources if needed.

---

## Limitations

- **Short test period:** 32 months, so results may change with more data.
- **Correlation, not causation:** the rainfall lag may partly reflect shared seasonal patterns.
- **Missing global drivers:** crude oil prices, competing vegetable oils, exchange rates and export policies are not included.
- **Single rainfall location:** Sandakan represents one major palm oil region, not all of Malaysia.

## Next steps

- Store data in **Azure Blob Storage** and connect Power BI to the cloud source
- Automate the monthly data refresh with an **Azure Function** (timer trigger)
- Benchmark against **Azure AutoML**
- Add external drivers such as crude oil and soybean oil prices

---

## Tech stack

Python (pandas, scikit-learn, matplotlib) · Google Colab · Power BI (DAX, Power Query) · GitHub

## Author

**Ahmad Isyraf** · [LinkedIn](https://linkedin.com/in/ahmad-isyraf/) · [GitHub](https://github.com/ahmadisyraf39)
