import pandas as pd


def compute_climatology(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly mean value per (lat, lon, month) over the full period."""
    df = df.copy()
    df["month"] = df["time"].dt.month
    climatology = (
        df.groupby(["lat", "lon", "month"], as_index=False)["value"]
        .mean()
        .rename(columns={"value": "clim_mean"})
    )
    return climatology


def compute_anomaly(df: pd.DataFrame, climatology: pd.DataFrame) -> pd.DataFrame:
    """Subtract climatological mean from each observation."""
    df = df.copy()
    df["month"] = df["time"].dt.month
    merged = df.merge(climatology, on=["lat", "lon", "month"], how="left")
    merged["anomaly"] = merged["value"] - merged["clim_mean"]
    return merged
