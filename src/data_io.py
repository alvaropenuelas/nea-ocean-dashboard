import streamlit as st
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

DATA_DIR = Path("data")


@st.cache_data(show_spinner=False)
def load_map_month(path: str, year: int, month: int) -> pd.DataFrame:
    t = pd.Timestamp(year=year, month=month, day=1)
    df = pq.read_table(path, filters=[("time", "==", t)]).to_pandas()
    df["time"] = pd.to_datetime(df["time"])
    return df


@st.cache_data(show_spinner=False)
def load_coupling_stats() -> pd.DataFrame:
    df = pd.read_parquet(DATA_DIR / "coupling_stats.parquet")
    df["time"] = pd.to_datetime(df["time"])
    df["year"] = df["time"].dt.year
    df["month"] = df["time"].dt.month
    return df


@st.cache_data(show_spinner=False)
def load_mhw_summary() -> pd.DataFrame:
    df = pd.read_parquet(DATA_DIR / "mhw_monthly_summary.parquet")
    df["time"] = pd.to_datetime(df["time"])
    return df


@st.cache_data(show_spinner=False)
def load_mhw_events() -> pd.DataFrame:
    df = pd.read_parquet(DATA_DIR / "mhw_events.parquet")
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    return df
