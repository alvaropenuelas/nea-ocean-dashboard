import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

from analysis import compute_climatology, compute_anomaly
from mhw import (
    compute_climatology_percentile,
    detect_mhw_events,
    detect_mhw_pixels,
    summarize_mhw_events,
)

st.set_page_config(
    page_title="NE Atlantic Ocean Dashboard",
    page_icon="🌊",
    layout="wide",
)

# ── Constants ─────────────────────────────────────────────────────────────────

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

CATEGORY_COLORS = {
    "I — Moderate": "rgba(255,200,0,0.20)",
    "II — Strong":  "rgba(255,140,0,0.25)",
    "III — Severe": "rgba(220,50,0,0.30)",
    "IV — Extreme": "rgba(150,0,0,0.38)",
}

CATEGORY_COLORS_SOLID = {
    "I — Moderate": "#c8a000",
    "II — Strong":  "#d07000",
    "III — Severe": "#c03200",
    "IV — Extreme": "#780000",
}
CATEGORY_UNCLASSIFIED_COLOR = "#3d5566"   # < 5 % coverage — not classified

LAYOUT_BASE = dict(
    paper_bgcolor="#060d12",
    plot_bgcolor="#0d1f2d",
    font_color="#ffffff",
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=20, b=40),
)

# ── Data loading ──────────────────────────────────────────────────────────────


@st.cache_data(show_spinner="Loading data …")
def load_variable(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_parquet(path)
    df["time"] = pd.to_datetime(df["time"])
    clim = compute_climatology(df)
    df = compute_anomaly(df, clim)
    df["year"] = df["time"].dt.year
    return df, clim


@st.cache_data(show_spinner="Detecting marine heatwaves …")
def load_mhw(
    sst_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_parquet(sst_path)
    df["time"] = pd.to_datetime(df["time"])
    clim_p90 = compute_climatology_percentile(df)
    mhw_df = detect_mhw_events(df, clim_p90)       # basin-mean (secondary)
    events_df = summarize_mhw_events(mhw_df)
    pixel_df = detect_mhw_pixels(df, clim_p90)     # per-pixel (primary)
    return mhw_df, events_df, pixel_df


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🌊 NE Atlantic")
    st.markdown("**Ocean Anomaly Explorer**")
    st.divider()

    var_key = st.selectbox("Variable", list(VARIABLES.keys()))
    meta = VARIABLES[var_key]

    year = st.slider("Year", 2000, 2023, 2020)
    month = st.slider("Month", 1, 12, 6, format="%d")

    st.divider()
    st.caption("SST: 2000–2023 | Chl-a: 2018–2023\nNE Atlantic (30°W–5°E, 35°N–65°N)")

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

tab_map, tab_ts, tab_hm, tab_mhw, tab_coupling = st.tabs(
    ["🗺 Map", "📈 Time Series", "🟥 Heatmap", "🌡 Heatwaves", "🔗 Coupling"]
)

# ── Tab 1: Map ────────────────────────────────────────────────────────────────

with tab_map:
    st.subheader(f"{meta['label']} Anomaly — {year}-{month:02d}")

    if selected.empty:
        st.warning("No data for this month/year combination.")
    else:
        anom_abs = selected["anomaly"].abs().quantile(0.98)
        fig_map = px.scatter_map(
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
            map_style="carto-darkmatter",
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
    yr_min = int(df["time"].dt.year.min())
    yr_max = int(df["time"].dt.year.max())
    st.subheader(f"{meta['label']} — Spatially-Averaged Anomaly {yr_min}–{yr_max}")

    ts = (
        df.groupby("time", as_index=False)["anomaly"]
        .mean()
        .sort_values("time")
    )
    ts["rolling_std"] = ts["anomaly"].rolling(3, center=True).std()
    ts["upper"] = ts["anomaly"] + ts["rolling_std"].fillna(0)
    ts["lower"] = ts["anomaly"] - ts["rolling_std"].fillna(0)

    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(
        x=pd.concat([ts["time"], ts["time"].iloc[::-1]]),
        y=pd.concat([ts["upper"], ts["lower"].iloc[::-1]]),
        fill="toself",
        fillcolor="rgba(29,158,117,0.15)",
        line=dict(color="rgba(255,255,255,0)"),
        name="±1 std",
    ))
    fig_ts.add_trace(go.Scatter(
        x=ts["time"],
        y=ts["anomaly"],
        mode="lines",
        line=dict(color="#1D9E75", width=1.8),
        name="Anomaly",
    ))
    fig_ts.add_hline(y=0, line_color="white", line_dash="dot", line_width=1)
    fig_ts.update_layout(
        **LAYOUT_BASE,
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="#1a2e40", title=f"Anomaly ({meta['unit']})"),
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
        y=["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        aspect="auto",
    )
    fig_hm.update_layout(
        **LAYOUT_BASE,
        coloraxis_colorbar=dict(title=f"{meta['unit']}"),
    )
    st.plotly_chart(fig_hm, use_container_width=True)

# ── Tab 4: Marine Heatwaves ───────────────────────────────────────────────────

with tab_mhw:
    st.subheader("Marine Heatwave Detection")

    if var_key != "SST":
        st.info("MHW analysis applies to SST only. Switch the Variable selector to SST.")
    else:
        sst_file = VARIABLES["SST"]["file"]
        mhw_df, events_df, pixel_df = load_mhw(sst_file)

        # ── Primary chart: per-pixel % MHW + domain-mean overlay ──────────
        fig_mhw = make_subplots(specs=[[{"secondary_y": True}]])

        bar_colors = [
            CATEGORY_COLORS_SOLID.get(cat, CATEGORY_UNCLASSIFIED_COLOR)
            for cat in pixel_df["max_category"]
        ]
        customdata = (
            pixel_df[["max_category", "max_intensity_multiple"]]
            .copy()
            .assign(max_category=lambda d: d["max_category"].fillna("< 5% coverage"))
            .assign(max_intensity_multiple=lambda d: d["max_intensity_multiple"].round(2).fillna(0))
            .values
        )
        fig_mhw.add_trace(
            go.Bar(
                x=pixel_df["time"],
                y=pixel_df["pct_mhw"],
                marker_color=bar_colors,
                marker_line_width=0,
                name="% pixels in MHW state",
                showlegend=False,
                customdata=customdata,
                hovertemplate=(
                    "%{x|%Y-%m}<br>"
                    "%{y:.1f}% of domain in MHW state<br>"
                    "Max category: %{customdata[0]}<br>"
                    "Max intensity multiple: %{customdata[1]:.2f}×"
                    "<extra></extra>"
                ),
            ),
            secondary_y=False,
        )

        # Legend proxy traces (invisible markers, legend entries only)
        _legend_items = list(CATEGORY_COLORS_SOLID.items()) + [
            ("< 5% coverage (not classified)", CATEGORY_UNCLASSIFIED_COLOR)
        ]
        for _name, _color in _legend_items:
            fig_mhw.add_trace(
                go.Scatter(
                    x=[None], y=[None],
                    mode="markers",
                    marker=dict(color=_color, size=10, symbol="square"),
                    name=_name,
                    showlegend=True,
                ),
                secondary_y=False,
            )
        fig_mhw.add_trace(
            go.Scatter(
                x=mhw_df["time"],
                y=mhw_df["spatial_mean_threshold"],
                mode="lines",
                line=dict(color="rgba(220,80,80,0.55)", width=1.2, dash="dash"),
                name="P90 threshold (domain mean)",
            ),
            secondary_y=True,
        )
        fig_mhw.add_trace(
            go.Scatter(
                x=mhw_df["time"],
                y=mhw_df["spatial_mean_sst"],
                mode="lines",
                line=dict(color="rgba(255,255,255,0.45)", width=1.5),
                name="Domain-mean SST (less sensitive)",
            ),
            secondary_y=True,
        )
        fig_mhw.update_yaxes(
            title_text="% of NE Atlantic in MHW state",
            secondary_y=False,
            range=[0, 100],
            showgrid=True,
            gridcolor="#1a2e40",
        )
        fig_mhw.update_yaxes(
            title_text="SST (°C)",
            secondary_y=True,
            showgrid=False,
        )
        fig_mhw.update_layout(
            **LAYOUT_BASE,
            xaxis=dict(showgrid=False, title=""),
            bargap=0.08,
        )
        st.plotly_chart(fig_mhw, use_container_width=True)

        st.caption(
            "**Bars**: % of NE Atlantic grid cells exceeding their local P90 threshold "
            "(per-pixel detection — primary method). "
            "Bar colour = maximum local Hobday 2018 category reached that month "
            "(yellow I, orange II, red III, dark-red IV). "
            "Grey bars: < 5% of the domain in MHW state — maximum local category is "
            "not assigned because isolated anomalous pixels near coastal fronts produce "
            "spuriously high intensity multiples when the basin as a whole is not in "
            "MHW state. "
            "**Faint lines** (right axis): domain-averaged SST and P90 threshold "
            "— shown as secondary reference; spatial averaging suppresses hotspots "
            "and underdetects events. "
            "Baseline: 2000–2020. Method: Hobday et al. 2016/2018."
        )

        st.subheader("Detected MHW events (basin-mean method)")
        st.caption(
            "Events below are from the domain-averaged detection (secondary view). "
            "See bar chart above for the more sensitive per-pixel picture."
        )
        if events_df.empty:
            st.write("No MHW events detected by the basin-mean method.")
        else:
            display_df = events_df.copy()
            display_df["start_date"] = display_df["start_date"].dt.strftime("%Y-%m")
            display_df["end_date"] = display_df["end_date"].dt.strftime("%Y-%m")
            display_df["max_intensity"] = display_df["max_intensity"].round(3)
            display_df["cumulative_intensity"] = display_df["cumulative_intensity"].round(3)
            st.dataframe(display_df, use_container_width=True, hide_index=True)

# ── Tab 5: Coupling Analysis ──────────────────────────────────────────────────

with tab_coupling:
    st.subheader("SST–Chlorophyll-a Coupling Analysis")

    sst_file = VARIABLES["SST"]["file"]
    chl_file = VARIABLES["Chlorophyll-a"]["file"]

    if not sst_file.exists() or not chl_file.exists():
        st.warning(
            "Coupling Analysis requires both SST and Chl-a parquet files. "
            "Run `python data_fetch.py` to generate them."
        )
    else:
        sst_full, _ = load_variable(sst_file)
        chl_full, _ = load_variable(chl_file)

        sst_ts = (
            sst_full.groupby("time", as_index=False)["anomaly"]
            .mean()
            .rename(columns={"anomaly": "sst_anom"})
        )
        chl_ts = (
            chl_full.groupby("time", as_index=False)["anomaly"]
            .mean()
            .rename(columns={"anomaly": "chl_anom"})
        )
        merged = sst_ts.merge(chl_ts, on="time").sort_values("time").reset_index(drop=True)

        # ── Plot 1: dual-axis time series ──────────────────────────────────
        st.markdown("#### Spatially-Averaged Anomalies (Overlap Period 2018–2023)")

        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
        fig_dual.add_trace(
            go.Scatter(
                x=merged["time"], y=merged["sst_anom"],
                name="SST anomaly",
                line=dict(color="#e05252", width=1.8),
            ),
            secondary_y=False,
        )
        fig_dual.add_trace(
            go.Scatter(
                x=merged["time"], y=merged["chl_anom"],
                name="Chl-a anomaly",
                line=dict(color="#1D9E75", width=1.8),
            ),
            secondary_y=True,
        )
        fig_dual.add_hline(y=0, line_color="rgba(255,255,255,0.3)", line_dash="dot", line_width=1)
        fig_dual.update_yaxes(
            title_text="SST anomaly (°C)",
            secondary_y=False,
            showgrid=True,
            gridcolor="#1a2e40",
            color="#e05252",
        )
        fig_dual.update_yaxes(
            title_text="Chl-a anomaly (mg m⁻³)",
            secondary_y=True,
            showgrid=False,
            color="#1D9E75",
        )
        fig_dual.update_layout(
            **LAYOUT_BASE,
            xaxis=dict(showgrid=False, title=""),
        )
        st.plotly_chart(fig_dual, use_container_width=True)

        st.divider()

        # ── Plot 2: scatter + regression ───────────────────────────────────
        col_l, col_r = st.columns(2)

        x_vals = merged["sst_anom"].values
        y_vals = merged["chl_anom"].values
        r_val = float(np.corrcoef(x_vals, y_vals)[0, 1])
        coeffs = np.polyfit(x_vals, y_vals, 1)
        x_line = np.linspace(x_vals.min(), x_vals.max(), 100)
        y_line = np.polyval(coeffs, x_line)

        with col_l:
            st.markdown("#### SST vs Chl-a Anomaly Scatter")
            fig_scatter = go.Figure()
            fig_scatter.add_trace(go.Scatter(
                x=x_vals, y=y_vals,
                mode="markers",
                marker=dict(color="#1D9E75", size=6, opacity=0.7),
                name="Monthly means",
            ))
            fig_scatter.add_trace(go.Scatter(
                x=x_line, y=y_line,
                mode="lines",
                line=dict(color="#e05252", width=1.5, dash="dash"),
                name=f"Regression (r = {r_val:.3f})",
            ))
            fig_scatter.update_layout(
                **LAYOUT_BASE,
                xaxis=dict(showgrid=True, gridcolor="#1a2e40", title="SST anomaly (°C)"),
                yaxis=dict(showgrid=True, gridcolor="#1a2e40", title="Chl-a anomaly (mg m⁻³)"),
                annotations=[dict(
                    x=0.05, y=0.95, xref="paper", yref="paper",
                    text=f"<b>Pearson r = {r_val:.3f}</b>",
                    showarrow=False,
                    bgcolor="rgba(6,13,18,0.8)",
                    font=dict(color="#ffffff", size=13),
                )],
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

        # ── Plot 3: lagged cross-correlation ───────────────────────────────
        with col_r:
            st.markdown("#### Lagged Cross-Correlation r(SST_t, Chl-a_{t+lag})")
            lags = list(range(-3, 4))
            n = len(merged)
            lag_rs = []
            for lag in lags:
                if lag == 0:
                    a, b = x_vals, y_vals
                elif lag > 0:
                    a, b = x_vals[: n - lag], y_vals[lag:]
                else:
                    a, b = x_vals[-lag:], y_vals[: n + lag]
                lag_rs.append(float(np.corrcoef(a, b)[0, 1]))

            fig_lag = go.Figure(go.Bar(
                x=lags,
                y=lag_rs,
                marker_color=["#e05252" if r >= 0 else "#5281e0" for r in lag_rs],
                text=[f"{r:.3f}" for r in lag_rs],
                textposition="outside",
                textfont=dict(size=11),
            ))
            fig_lag.add_hline(y=0, line_color="white", line_width=1)
            fig_lag.update_layout(
                **LAYOUT_BASE,
                xaxis=dict(
                    showgrid=False,
                    title="Lag (months) — positive: SST leads Chl-a",
                    tickvals=lags,
                    ticktext=[str(l) for l in lags],
                ),
                yaxis=dict(showgrid=True, gridcolor="#1a2e40", title="Pearson r"),
            )
            st.plotly_chart(fig_lag, use_container_width=True)

        st.divider()

        # ── MHW months chlorophyll analysis ───────────────────────────────
        st.markdown("#### Chlorophyll-a Response During MHW Months")

        mhw_df_loaded, _, _ = load_mhw(sst_file)
        mhw_times = set(mhw_df_loaded[mhw_df_loaded["is_mhw"]]["time"])
        merged = merged.copy()
        merged["is_mhw"] = merged["time"].isin(mhw_times)

        mhw_chl = merged.loc[merged["is_mhw"], "chl_anom"].mean()
        non_mhw_chl = merged.loc[~merged["is_mhw"], "chl_anom"].mean()
        n_mhw_months = int(merged["is_mhw"].sum())

        c1, c2, c3 = st.columns(3)
        c1.metric("Chl-a anomaly — MHW months", f"{mhw_chl:+.4f} mg m⁻³")
        c2.metric("Chl-a anomaly — non-MHW months", f"{non_mhw_chl:+.4f} mg m⁻³")
        c3.metric("MHW months (2018–2023)", n_mhw_months)

        mhw_2023 = merged[merged["is_mhw"] & (merged["time"].dt.year == 2023)].copy()
        if not mhw_2023.empty:
            st.markdown("**2023 MHW months:**")
            disp = mhw_2023[["time", "sst_anom", "chl_anom"]].copy()
            disp["time"] = disp["time"].dt.strftime("%Y-%m")
            disp.columns = ["Month", "SST anomaly (°C)", "Chl-a anomaly (mg m⁻³)"]
            disp["SST anomaly (°C)"] = disp["SST anomaly (°C)"].round(4)
            disp["Chl-a anomaly (mg m⁻³)"] = disp["Chl-a anomaly (mg m⁻³)"].round(4)
            st.dataframe(disp, use_container_width=True, hide_index=True)

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
