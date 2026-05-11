"""
Marine heatwave detection adapted from Hobday et al. (2016)
doi:10.1016/j.pocean.2015.12.014

Standard definition requires daily SST and a 5-day minimum duration.
This implementation adapts to monthly reanalysis data: day-of-year
becomes month-of-year, and the duration rule is replaced by flagging
any month where the spatially-averaged SST exceeds the spatially-averaged
90th-percentile threshold for that calendar month.
"""

import numpy as np
import pandas as pd


def compute_climatology_percentile(
    df: pd.DataFrame,
    baseline_start: str = "2018-01-01",
    baseline_end: str = "2022-12-31",
    percentile: int = 90,
) -> pd.DataFrame:
    """
    Per (lat, lon, month), compute the climatological mean and the
    percentile threshold over the baseline period.

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
    domain-averaged 90th-percentile threshold for that calendar month.

    Returns: time, spatial_mean_sst, spatial_mean_threshold, is_mhw, intensity.
    """
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"])

    ts = (
        df.groupby("time", as_index=False)["value"]
        .mean()
        .rename(columns={"value": "spatial_mean_sst"})
    )
    ts["doy"] = ts["time"].dt.month

    monthly_thresh = (
        climatology.groupby("doy", as_index=False)["threshold_p90"]
        .mean()
        .rename(columns={"threshold_p90": "spatial_mean_threshold"})
    )

    result = ts.merge(monthly_thresh, on="doy", how="left").sort_values("time")
    result["is_mhw"] = result["spatial_mean_sst"] > result["spatial_mean_threshold"]
    result["intensity"] = np.where(
        result["is_mhw"],
        result["spatial_mean_sst"] - result["spatial_mean_threshold"],
        np.nan,
    )
    return result[
        ["time", "spatial_mean_sst", "spatial_mean_threshold", "is_mhw", "intensity"]
    ].reset_index(drop=True)


def summarize_mhw_events(mhw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Group consecutive MHW months into discrete events.

    Returns: event_id, start_date, end_date, duration_months,
             max_intensity, cumulative_intensity.
    """
    df = mhw_df.sort_values("time").copy()
    df["group"] = (df["is_mhw"] != df["is_mhw"].shift()).cumsum()

    mhw_only = df[df["is_mhw"]]
    if mhw_only.empty:
        return pd.DataFrame(
            columns=[
                "event_id", "start_date", "end_date",
                "duration_months", "max_intensity", "cumulative_intensity",
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
    events.insert(0, "event_id", range(1, len(events) + 1))
    return events
