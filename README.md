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

## Related repos

This dashboard is part of a broader computational ecology portfolio:

- **[species-distribution-modeling](https://github.com/alvaropenuelas/species-distribution-modeling)** — MaxEnt / SDM with Sentinel-2 / GEE integration
- **[mediterranean-biodiversity-analysis](https://github.com/alvaropenuelas/mediterranean-biodiversity-analysis)** — benthic biodiversity assessment from photographic transects, Tenerife field data

---

*Data: Copernicus Marine Service — © E.U. Copernicus Marine Service Information*
