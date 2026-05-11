"""
Marine heatwave detection and categorization.

Detection:      Hobday et al. (2016) doi:10.1016/j.pocean.2015.12.014
Categorization: Hobday et al. (2018) doi:10.5670/oceanog.2018.205

Adapted to monthly reanalysis data — see README for known limitations.
"""

import numpy as np
import pandas as pd

_CAT_LABELS = {
    1: "I — Moderate",
    2: "II — Strong",
    3: "III — Severe",
    4: "IV — Extreme",
}
_CAT_ORD = {v: k for k, v in _CAT_LABELS.items()}


def categorize_mhw_intensity(
    sst: float,
    climatology_mean: float,
    threshold_p90: float,
) -> str | None:
    """
    Hobday et al. 2018 four-category scheme for a single observation.

    difference      = threshold_p90 - climatology_mean   (local delta)
    intensity_multiple = (sst - climatology_mean) / difference

    Categories:
      I   Moderate:  1 <= multiple < 2
      II  Strong:    2 <= multiple < 3
      III Severe:    3 <= multiple < 4
      IV  Extreme:   multiple >= 4

    Returns None when not a MHW month or when delta <= 0.
    """
    delta = threshold_p90 - climatology_mean
    if delta <= 0:
        return None
    multiple = (sst - climatology_mean) / delta
    if multiple >= 4:
        return _CAT_LABELS[4]
    if multiple >= 3:
        return _CAT_LABELS[3]
    if multiple >= 2:
        return _CAT_LABELS[2]
    if multiple >= 1:
        return _CAT_LABELS[1]
    return None


def compute_climatology_percentile(
    df: pd.DataFrame,
    baseline_start: str = "2000-01-01",
    baseline_end: str = "2020-12-31",
    percentile: int = 90,
) -> pd.DataFrame:
    """
    Per (lat, lon, month), compute climatological mean and percentile
    threshold from the baseline period.

    Returns columns: lat, lon, doy (month number), clim_mean, threshold_p90.
    """
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"])
    baseline = df[
        (df["time"] >= baseline_start) & (df["time"] <= baseline_end)
    ].copy()
    baseline["doy"] = baseline["time"].dt.month

    grp = baseline.groupby(["lat", "lon", "doy"])["value"]
    clim_mean = grp.mean().rename("clim_mean")
    threshold_p90 = grp.quantile(percentile / 100).rename("threshold_p90")

    return pd.concat([clim_mean, threshold_p90], axis=1).reset_index()


def detect_mhw_events(
    df: pd.DataFrame,
    climatology: pd.DataFrame,
) -> pd.DataFrame:
    """
    Flag MHW months where the domain-averaged SST exceeds the
    domain-averaged P90 threshold for that calendar month.
    Assigns Hobday 2018 category to each flagged month.

    Returns: time, spatial_mean_sst, spatial_mean_threshold,
             is_mhw, intensity, category.
    """
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"])

    ts = (
        df.groupby("time", as_index=False)["value"]
        .mean()
        .rename(columns={"value": "spatial_mean_sst"})
    )
    ts["doy"] = ts["time"].dt.month

    monthly_stats = (
        climatology.groupby("doy", as_index=False)
        .agg(
            spatial_mean_threshold=("threshold_p90", "mean"),
            spatial_mean_clim=("clim_mean", "mean"),
        )
    )

    result = ts.merge(monthly_stats, on="doy", how="left").sort_values("time")
    result["is_mhw"] = result["spatial_mean_sst"] > result["spatial_mean_threshold"]
    result["intensity"] = np.where(
        result["is_mhw"],
        result["spatial_mean_sst"] - result["spatial_mean_threshold"],
        np.nan,
    )
    result["category"] = [
        categorize_mhw_intensity(
            row.spatial_mean_sst,
            row.spatial_mean_clim,
            row.spatial_mean_threshold,
        )
        if row.is_mhw else None
        for row in result.itertuples()
    ]

    return result[
        ["time", "spatial_mean_sst", "spatial_mean_threshold",
         "is_mhw", "intensity", "category"]
    ].reset_index(drop=True)


def detect_mhw_pixels(
    df: pd.DataFrame,
    climatology: pd.DataFrame,
) -> pd.DataFrame:
    """
    Per-pixel MHW detection: flag each (lat, lon, time) cell where SST > P90.

    Returns a monthly summary:
      time, pct_mhw (% of pixels in MHW state),
      max_intensity_multiple (basin maximum), max_category (Hobday 2018).
    """
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"])
    df["doy"] = df["time"].dt.month

    df_m = df.merge(climatology, on=["lat", "lon", "doy"], how="left")
    df_m["is_mhw_px"] = df_m["value"] > df_m["threshold_p90"]

    delta = df_m["threshold_p90"] - df_m["clim_mean"]
    df_m["intensity_multiple"] = np.where(
        df_m["is_mhw_px"] & (delta > 0),
        (df_m["value"] - df_m["clim_mean"]) / delta,
        np.nan,
    )

    monthly = (
        df_m.groupby("time")
        .agg(
            pct_mhw=("is_mhw_px", lambda x: x.mean() * 100),
            max_intensity_multiple=("intensity_multiple", "max"),
        )
        .reset_index()
    )

    def _cat(mult):
        if pd.isna(mult) or mult < 1:
            return None
        if mult >= 4:
            return _CAT_LABELS[4]
        if mult >= 3:
            return _CAT_LABELS[3]
        if mult >= 2:
            return _CAT_LABELS[2]
        return _CAT_LABELS[1]

    monthly["max_category"] = monthly["max_intensity_multiple"].apply(_cat)
    return monthly[["time", "pct_mhw", "max_intensity_multiple", "max_category"]]


def summarize_mhw_events(mhw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Group consecutive MHW months into discrete events.

    Returns: event_id, start_date, end_date, duration_months,
             max_intensity, cumulative_intensity, max_category.
    """
    df = mhw_df.sort_values("time").copy()
    df["group"] = (df["is_mhw"] != df["is_mhw"].shift()).cumsum()

    mhw_only = df[df["is_mhw"]]
    if mhw_only.empty:
        return pd.DataFrame(
            columns=[
                "event_id", "start_date", "end_date", "duration_months",
                "max_intensity", "cumulative_intensity", "max_category",
            ]
        )

    events = (
        mhw_only.groupby("group")
        .agg(
            start_date=("time", "min"),
            end_date=("time", "max"),
            duration_months=("time", "count"),
            max_intensity=("intensity", "max"),
            cumulative_intensity=("intensity", "sum"),
        )
        .reset_index(drop=True)
    )

    def _max_cat(cats):
        non_null = [c for c in cats if c is not None]
        return max(non_null, key=lambda c: _CAT_ORD.get(c, 0)) if non_null else None

    max_cats = (
        mhw_only.groupby("group")["category"]
        .apply(_max_cat)
        .reset_index(drop=True)
    )
    events["max_category"] = max_cats.values
    events.insert(0, "event_id", range(1, len(events) + 1))
    return events
