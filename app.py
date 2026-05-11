import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

from analysis import compute_climatology, compute_anomaly

st.set_page_config(
    page_title="NE Atlantic Ocean Dashboard",
    page_icon="🌊",
    layout="wide",
)

# ── Data loading ──────────────────────────────────────────────────────────────

DATA_DIR = Path("data")

VARIABLES = {
    "SST": {
        "file": DATA_DIR / "sst_monthly.parquet",
        "label": "Sea Surface Temperature",
        "unit": "°C",
        "colorscale": "RdBu_r",
    },
    "Chlorophyll-a": {
        "file": DATA_DIR / "chl_monthly.parquet",
        "label": "Chlorophyll-a",
        "unit": "mg m⁻³",
        "colorscale": "RdBu_r",
    },
}


@st.cache_data(show_spinner="Loading data …")
def load_variable(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"])
    clim = compute_climatology(df)
    df = compute_anomaly(df, clim)
    df["year"] = df["time"].dt.year
    return df, clim


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🌊 NE Atlantic")
    st.markdown("**Ocean Anomaly Explorer**")
    st.divider()

    var_key = st.selectbox("Variable", list(VARIABLES.keys()))
    meta = VARIABLES[var_key]

    year = st.slider("Year", 2010, 2023, 2020)
    month = st.slider("Month", 1, 12, 6, format="%d")

    st.divider()
    st.caption("Data covers 2010–2023, NE Atlantic (30°W–5°E, 35°N–65°N)")

# ── Load data ─────────────────────────────────────────────────────────────────

if not meta["file"].exists():
    st.error(
        f"Data file **{meta['file']}** not found. "
        "Run `python data_fetch.py` locally to generate the cache."
    )
    st.stop()

df, _ = load_variable(meta["file"])

# ── Subset for selected month/year ────────────────────────────────────────────

selected = df[(df["year"] == year) & (df["month"] == month)]

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_map, tab_ts, tab_hm = st.tabs(["🗺 Map", "📈 Time Series", "🟥 Heatmap"])

# ── Tab 1: Map ────────────────────────────────────────────────────────────────

with tab_map:
    st.subheader(f"{meta['label']} Anomaly — {year}-{month:02d}")

    if selected.empty:
        st.warning("No data for this month/year combination.")
    else:
        anom_abs = selected["anomaly"].abs().quantile(0.98)
        fig_map = px.scatter_mapbox(
            selected,
            lat="lat",
            lon="lon",
            color="anomaly",
            color_continuous_scale=meta["colorscale"],
            range_color=[-anom_abs, anom_abs],
            opacity=0.75,
            size_max=6,
            zoom=3.5,
            center={"lat": 52, "lon": -15},
            mapbox_style="carto-darkmatter",
            labels={"anomaly": f"Anomaly ({meta['unit']})"},
            hover_data={"lat": ":.2f", "lon": ":.2f", "anomaly": ":.3f"},
        )
        fig_map.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            coloraxis_colorbar=dict(title=f"{meta['unit']}"),
            paper_bgcolor="#060d12",
        )
        st.plotly_chart(fig_map, use_container_width=True)

# ── Tab 2: Time Series ────────────────────────────────────────────────────────

with tab_ts:
    st.subheader(f"{meta['label']} — Spatially-Averaged Anomaly 2010–2023")

    ts = (
        df.groupby("time", as_index=False)["anomaly"]
        .mean()
        .sort_values("time")
    )
    ts["rolling_std"] = ts["anomaly"].rolling(3, center=True).std()
    ts["upper"] = ts["anomaly"] + ts["rolling_std"].fillna(0)
    ts["lower"] = ts["anomaly"] - ts["rolling_std"].fillna(0)

    fig_ts = go.Figure()

    fig_ts.add_trace(
        go.Scatter(
            x=pd.concat([ts["time"], ts["time"].iloc[::-1]]),
            y=pd.concat([ts["upper"], ts["lower"].iloc[::-1]]),
            fill="toself",
            fillcolor="rgba(29,158,117,0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="±1 std",
            showlegend=True,
        )
    )
    fig_ts.add_trace(
        go.Scatter(
            x=ts["time"],
            y=ts["anomaly"],
            mode="lines",
            line=dict(color="#1D9E75", width=1.8),
            name="Anomaly",
        )
    )
    fig_ts.add_hline(y=0, line_color="white", line_dash="dot", line_width=1)

    fig_ts.update_layout(
        paper_bgcolor="#060d12",
        plot_bgcolor="#0d1f2d",
        font_color="#ffffff",
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="#1a2e40", title=f"Anomaly ({meta['unit']})"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=20, b=40),
    )
    st.plotly_chart(fig_ts, use_container_width=True)

# ── Tab 3: Heatmap ────────────────────────────────────────────────────────────

with tab_hm:
    st.subheader(f"{meta['label']} — Monthly × Yearly Anomaly Matrix")

    pivot = (
        df.groupby(["year", "month"], as_index=False)["anomaly"]
        .mean()
        .pivot(index="month", columns="year", values="anomaly")
    )

    anom_abs = pivot.abs().values[~np.isnan(pivot.values)].max()

    fig_hm = px.imshow(
        pivot,
        color_continuous_scale=meta["colorscale"],
        zmin=-anom_abs,
        zmax=anom_abs,
        labels={"x": "Year", "y": "Month", "color": f"Anomaly ({meta['unit']})"},
        y=[
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ],
        aspect="auto",
    )
    fig_hm.update_layout(
        paper_bgcolor="#060d12",
        plot_bgcolor="#0d1f2d",
        font_color="#ffffff",
        margin=dict(t=20),
        coloraxis_colorbar=dict(title=f"{meta['unit']}"),
    )
    st.plotly_chart(fig_hm, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────

st.divider()
st.markdown(
    "<div style='text-align:center; color:#888; font-size:0.8rem;'>"
    "Data: Copernicus Marine Service | "
    "Álvaro Peñuelas Sánchez | "
    "<a href='https://github.com/alvaropenuelas' style='color:#1D9E75;'>github.com/alvaropenuelas</a>"
    "</div>",
    unsafe_allow_html=True,
)
