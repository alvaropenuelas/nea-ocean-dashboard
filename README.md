# nea-ocean-dashboard

Interactive Streamlit dashboard visualising Sea Surface Temperature (SST) and Chlorophyll-a anomalies in the NE Atlantic (2010–2023), powered by Copernicus Marine Service data.

---

## Screenshot

> *(placeholder — replace with a screenshot of the deployed app)*

---

## Data pipeline

The app reads pre-fetched **parquet** cache files so no Copernicus credentials are needed to view the deployed dashboard. Run the fetch script **once locally** to generate them:

```bash
export COPERNICUSMARINE_SERVICE_USERNAME="your_username"
export COPERNICUSMARINE_SERVICE_PASSWORD="your_password"

python data_fetch.py
```

This writes two files to `data/` (gitignored):

| File | Source dataset | Variable |
|---|---|---|
| `data/sst_monthly.parquet` | `cmems_mod_glo_phy_my_0.083deg_P1M-m` | `thetao` (surface) |
| `data/chl_monthly.parquet` | `cmems_mod_bio_glo_biogeochemistry_my_0.25deg_P1M-m` | `chl` |

Free Copernicus Marine credentials: <https://data.marine.copernicus.eu/register>

---

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Deploy to Streamlit Cloud

1. Push this repo to GitHub (the parquet files must be committed — temporarily remove `data/` from `.gitignore` after fetching, commit, then restore).
2. Go to <https://share.streamlit.io> → **New app** → select this repo → `app.py`.
3. No secrets are required for the deployed app.

---

## Live demo

> *(placeholder — add Streamlit Cloud URL here)*

---

## Methods

### Anomaly calculation
Monthly SST and Chlorophyll-a anomalies are computed per grid cell by subtracting the long-term monthly climatological mean (2018–2022 baseline) from each observation.

### Marine heatwave detection
MHW detection follows **Hobday et al. (2016)** ([doi:10.1016/j.pocean.2015.12.014](https://doi.org/10.1016/j.pocean.2015.12.014)), adapted to monthly resolution:

- **Climatology baseline**: 2018–2022
- **Threshold**: 90th percentile of SST values per (lat, lon, month) across baseline years
- **MHW month**: any month where the spatially-averaged SST exceeds the spatially-averaged 90th-percentile threshold for that calendar month
- Consecutive MHW months are grouped into discrete events

> **Caveat — known limitation**: The Hobday et al. (2016) standard requires *daily* SST data and a minimum event duration of 5 consecutive days. This dashboard uses *monthly* reanalysis output, so the 5-day rule cannot be applied and sub-monthly heatwaves are invisible. The monthly adaptation should be treated as indicative only. For rigorous MHW detection, daily satellite SST (e.g. OSTIA or CMC 0.1°) is required.

### Data sources

| Variable | Copernicus Marine dataset ID |
|---|---|
| SST | `cmems_mod_glo_phy_my_0.083deg_P1M-m` |
| Chlorophyll-a | `cmems_mod_glo_bgc_my_0.25deg_P1M-m` |

---

## Related repos

This dashboard is part of a broader computational ecology portfolio:

- **[species-distribution-modeling](https://github.com/alvaropenuelas/species-distribution-modeling)** — MaxEnt / SDM with Sentinel-2 / GEE integration
- **[mediterranean-biodiversity-analysis](https://github.com/alvaropenuelas/mediterranean-biodiversity-analysis)** — benthic biodiversity assessment from photographic transects, Tenerife field data

---

*Data: Copernicus Marine Service — © E.U. Copernicus Marine Service Information*
