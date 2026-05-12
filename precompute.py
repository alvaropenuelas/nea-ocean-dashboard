"""
Run once locally after data_fetch.py to generate all derived products.
The deployed app loads only these files — the raw SST/Chl parquets are
never touched at runtime.

Usage:
    python precompute.py
"""

import json
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path

from analysis import compute_climatology, compute_anomaly
from mhw import (
    compute_climatology_percentile,
    detect_mhw_events,
    detect_mhw_pixels,
    summarize_mhw_events,
)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


def save(df: pd.DataFrame, name: str, row_group_size: int | None = None) -> None:
    path = DATA_DIR / name
    table = pa.Table.from_pandas(df, preserve_index=False)
    kwargs = {"row_group_size": row_group_size} if row_group_size else {}
    pq.write_table(table, path, **kwargs)
    kb = path.stat().st_size / 1024
    print(f"  ✓ {name}: {len(df):,} rows  ({kb:.0f} KB)")


# ── SST ───────────────────────────────────────────────────────────────────────

print("Loading raw SST (9.1 M rows)…")
sst_raw = pd.read_parquet(DATA_DIR / "sst_monthly.parquet")
sst_raw["time"] = pd.to_datetime(sst_raw["time"])

ROWS_PER_MONTH_SST = 31_725   # exact, uniform across all months

# a. sst_anomaly.parquet ─────────────────────────────────────────────────────
print("Computing SST anomaly…")
clim = compute_climatology(sst_raw)
sst_anom = compute_anomaly(sst_raw, clim)
sst_anom = (
    sst_anom[["lat", "lon", "time", "anomaly"]]
    .sort_values("time")
    .reset_index(drop=True)
)
# one row-group per month → pyarrow predicate-pushdown loads only 31k rows
save(sst_anom, "sst_anomaly.parquet", row_group_size=ROWS_PER_MONTH_SST)

# c. sst_climatology.parquet ─────────────────────────────────────────────────
print("Computing SST climatology (P90)…")
clim_p90 = compute_climatology_percentile(sst_raw)
save(clim_p90, "sst_climatology.parquet")

# MHW detection
print("Computing MHW events…")
mhw_basin = detect_mhw_events(sst_raw, clim_p90)
events_df = summarize_mhw_events(mhw_basin)
save(events_df, "mhw_events.parquet")

print("Computing per-pixel MHW…")
pixel_monthly = detect_mhw_pixels(sst_raw, clim_p90)
# e. mhw_monthly_summary.parquet ─────────────────────────────────────────────
mhw_summary = mhw_basin.merge(
    pixel_monthly[["time", "pct_mhw", "max_intensity_multiple", "max_category"]],
    on="time",
    how="left",
)
save(mhw_summary, "mhw_monthly_summary.parquet")

# d. mhw_pixels.parquet — only MHW=True cells ────────────────────────────────
print("Computing per-pixel MHW cells (MHW=True only)…")
sst_raw_copy = sst_raw.copy()
sst_raw_copy["doy"] = sst_raw_copy["time"].dt.month
df_px = sst_raw_copy.merge(clim_p90, on=["lat", "lon", "doy"], how="left")
df_px["is_mhw_px"] = df_px["value"] > df_px["threshold_p90"]
delta = df_px["threshold_p90"] - df_px["clim_mean"]
df_px["intensity_multiple"] = np.where(
    df_px["is_mhw_px"] & (delta > 0),
    (df_px["value"] - df_px["clim_mean"]) / delta,
    np.nan,
)

def _cat(mult):
    if pd.isna(mult) or mult < 1:
        return None
    if mult >= 4: return "IV — Extreme"
    if mult >= 3: return "III — Severe"
    if mult >= 2: return "II — Strong"
    return "I — Moderate"

mhw_px = df_px[df_px["is_mhw_px"]][["lat", "lon", "time", "intensity_multiple"]].copy()
mhw_px["category"] = mhw_px["intensity_multiple"].apply(_cat)
mhw_px = mhw_px.sort_values("time").reset_index(drop=True)
save(mhw_px, "mhw_pixels.parquet")
del sst_raw_copy, df_px, mhw_px

# Spatial mean SST time series (for coupling_stats)
sst_ts = (
    sst_anom.groupby("time", as_index=False)["anomaly"]
    .mean()
    .rename(columns={"anomaly": "sst_anom"})
)

del sst_raw, sst_anom, clim, clim_p90, mhw_basin, pixel_monthly

# ── Chlorophyll-a ─────────────────────────────────────────────────────────────

ROWS_PER_MONTH_CHL = 3_576

print("\nLoading raw Chl-a…")
chl_raw = pd.read_parquet(DATA_DIR / "chl_monthly.parquet")
chl_raw["time"] = pd.to_datetime(chl_raw["time"])

# b. chl_anomaly.parquet ─────────────────────────────────────────────────────
print("Computing Chl-a anomaly…")
chl_clim = compute_climatology(chl_raw)
chl_anom = compute_anomaly(chl_raw, chl_clim)
chl_anom = (
    chl_anom[["lat", "lon", "time", "anomaly"]]
    .sort_values("time")
    .reset_index(drop=True)
)
save(chl_anom, "chl_anomaly.parquet", row_group_size=ROWS_PER_MONTH_CHL)

chl_ts = (
    chl_anom.groupby("time", as_index=False)["anomaly"]
    .mean()
    .rename(columns={"anomaly": "chl_anom"})
)

del chl_raw, chl_clim, chl_anom

# ── f. coupling_stats.parquet ─────────────────────────────────────────────────
# 288 rows: sst_anom (all), chl_anom (NaN for 2000-2017), is_mhw (all)
print("\nBuilding coupling_stats…")
mhw_flag = pd.read_parquet(DATA_DIR / "mhw_monthly_summary.parquet")[["time", "is_mhw"]]
mhw_flag["time"] = pd.to_datetime(mhw_flag["time"])

coupling = (
    sst_ts
    .merge(chl_ts, on="time", how="left")
    .merge(mhw_flag, on="time", how="left")
    .sort_values("time")
    .reset_index(drop=True)
)
coupling["is_mhw"] = coupling["is_mhw"].fillna(False)
save(coupling, "coupling_stats.parquet")

# ── Total size report ─────────────────────────────────────────────────────────
print("\nDerived file totals:")
derived = [
    "sst_anomaly.parquet", "chl_anomaly.parquet",
    "sst_climatology.parquet", "mhw_pixels.parquet",
    "mhw_monthly_summary.parquet", "mhw_events.parquet",
    "coupling_stats.parquet",
]
total_kb = sum((DATA_DIR / f).stat().st_size for f in derived) / 1024
for f in derived:
    kb = (DATA_DIR / f).stat().st_size / 1024
    print(f"  {f}: {kb:.0f} KB")
print(f"  TOTAL: {total_kb/1024:.1f} MB")
print("\nDone.")
