import streamlit as st
import pandas as pd
import numpy as np
import pyarrow.parquet as pq
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

st.set_page_config(
    page_title="NE Atlantic Ocean Dashboard",
    page_icon="🌊",
    layout="wide",
)

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_DIR = Path("data")

VARIABLES = {
    "SST": {
        "anom_file": DATA_DIR / "sst_anomaly.parquet",
        "anom_col":  "sst_anom",
        "label": "Sea Surface Temperature",
        "unit": "°C",
        "colorscale": "RdBu_r",
        "year_min": 2000,
        "year_max": 2023,
    },
    "Chlorophyll-a": {
        "anom_file": DATA_DIR / "chl_anomaly.parquet",
        "anom_col":  "chl_anom",
        "label": "Chlorophyll-a",
        "unit": "mg m⁻³",
        "colorscale": "RdBu_r",
        "year_min": 2018,
        "year_max": 2023,
    },
}

CATEGORY_COLORS_SOLID = {
    "I — Moderate": "#c8a000",
    "II — Strong":  "#d07000",
    "III — Severe": "#c03200",
    "IV — Extreme": "#780000",
}
CATEGORY_UNCLASSIFIED_COLOR = "#3d5566"

_FONT = dict(family="Inter, sans-serif", size=12, color="#e6edf3")
_AXIS = dict(
    showgrid=False,
    title_font=dict(size=11, color="#7a8a99"),
    tickfont=dict(size=11, color="#7a8a99"),
    linecolor="rgba(255,255,255,0.08)",
)
_YAXIS = dict(
    showgrid=True,
    gridcolor="rgba(26,46,64,0.9)",
    title_font=dict(size=11, color="#7a8a99"),
    tickfont=dict(size=11, color="#7a8a99"),
    linecolor="rgba(255,255,255,0.08)",
)

LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=_FONT,
    legend=dict(
        bgcolor="rgba(13,31,45,0.6)",
        bordercolor="#1D9E75",
        borderwidth=1,
        font=dict(size=11),
    ),
    margin=dict(l=40, r=20, t=40, b=40),
)

# Annotation events shown on SST time series
_SST_EVENTS = [
    ("2003-08-01", "2003 European heatwave"),
    ("2018-06-01", "2018 NW European MHW"),
    ("2023-06-01", "2023 NE Atlantic MHW\n276-yr return event"),
]

# ── Data loaders ──────────────────────────────────────────────────────────────


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


# ── Hero ──────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div style="padding: 2rem 0 1rem 0;">
      <h1 style="margin:0; font-size:2rem; font-weight:700; color:#e6edf3;
                 font-family:'Inter',sans-serif; letter-spacing:-0.02em;">
        NE Atlantic Ocean Anomaly Explorer
      </h1>
      <p style="margin:0.4rem 0 0 0; font-size:0.95rem; font-weight:400;
                color:#7a8a99; font-family:'Inter',sans-serif;">
        Marine heatwave detection and SST–chlorophyll coupling in the
        North-East Atlantic, 2000–2023
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

_mhw_kpi = load_mhw_summary()
_n_mhw_months = int((_mhw_kpi["max_category"].notna()).sum())

_CARD_CSS = (
    "background:#0d1f2d;"
    "border:1px solid rgba(29,158,117,0.30);"
    "border-radius:8px;"
    "padding:16px 20px;"
)
_LABEL_CSS = (
    "font-size:11px;font-weight:600;letter-spacing:0.08em;"
    "text-transform:uppercase;color:#7a8a99;"
    "font-family:'Inter',sans-serif;margin:0;"
)
_VALUE_CSS = (
    "font-size:28px;font-weight:700;color:#e6edf3;"
    "font-family:'Inter',sans-serif;margin:4px 0 2px 0;line-height:1.1;"
)
_SUB_CSS = (
    "font-size:11px;color:#7a8a99;"
    "font-family:'Inter',sans-serif;margin:0;"
)

kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.markdown(
        f"<div style='{_CARD_CSS}'>"
        f"<p style='{_LABEL_CSS}'>Peak basin coverage</p>"
        f"<p style='{_VALUE_CSS}'>78.5%</p>"
        f"<p style='{_SUB_CSS}'>June 2023</p>"
        f"</div>",
        unsafe_allow_html=True,
    )
with kpi2:
    st.markdown(
        f"<div style='{_CARD_CSS}'>"
        f"<p style='{_LABEL_CSS}'>Strongest category reached</p>"
        f"<p style='{_VALUE_CSS}'>IV Extreme</p>"
        f"<p style='{_SUB_CSS}'>Hobday et al. 2018</p>"
        f"</div>",
        unsafe_allow_html=True,
    )
with kpi3:
    st.markdown(
        f"<div style='{_CARD_CSS}'>"
        f"<p style='{_LABEL_CSS}'>MHW months detected</p>"
        f"<p style='{_VALUE_CSS}'>{_n_mhw_months}</p>"
        f"<p style='{_SUB_CSS}'>≥ 5% domain coverage, 2000–2023</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        "<p style='font-size:10px;font-weight:700;letter-spacing:0.12em;"
        "text-transform:uppercase;color:#7a8a99;margin-bottom:8px;'>"
        "Controls</p>",
        unsafe_allow_html=True,
    )

    var_key = st.selectbox("Variable", list(VARIABLES.keys()))
    meta = VARIABLES[var_key]

    year = st.slider("Year", meta["year_min"], meta["year_max"],
                     min(2020, meta["year_max"]))
    month = st.slider("Month", 1, 12, 6, format="%d")

    st.divider()
    st.caption("SST: 2000–2023 | Chl-a: 2018–2023\nNE Atlantic (30°W–5°E, 35°N–65°N)")

    with st.expander("Methods & References"):
        st.markdown(
            """
**Anomaly calculation**

Monthly anomalies per grid cell: observation minus the long-term
monthly climatological mean.
- SST baseline: 2000–2020
- Chl-a baseline: 2018–2022

**Marine heatwave detection**

Follows Hobday et al. (2016) adapted to monthly resolution.
Threshold: 90th percentile per (lat, lon, month) over the
2000–2020 baseline. Consecutive months above threshold form
a discrete event.

**Categorisation (Hobday 2018)**

| Category | Intensity multiple |
|---|---|
| I — Moderate | 1× – 2× |
| II — Strong | 2× – 3× |
| III — Severe | 3× – 4× |
| IV — Extreme | ≥ 4× |

**Coherent-area filter**

Maximum category only assigned when ≥ 5% of the NE Atlantic
domain is simultaneously in MHW state, suppressing isolated
frontal-pixel extremes.

**Coupling analysis**

Pearson r between spatially-averaged monthly SST and
Chl-a anomalies over the 2018–2023 overlap period, plus
lagged cross-correlation at −3 to +3 months.

---

**References**

Hobday et al. (2016) *Progress in Oceanography* 141, 227–238.

Hobday et al. (2018) *Oceanography* 31(2), 162–173.

England et al. (2025) *Nature* 642, 75–82.

*Data: Copernicus Marine Service*
            """
        )

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_map, tab_ts, tab_hm, tab_mhw, tab_coupling = st.tabs(
    ["Spatial Anomaly", "Time Series", "Month × Year",
     "Marine Heatwaves", "SST–Chlorophyll"]
)

# ── Tab 1: Spatial Anomaly ────────────────────────────────────────────────────

with tab_map:
    st.subheader(f"{meta['label']} Anomaly — {year}-{month:02d}")

    if not meta["anom_file"].exists():
        st.error(f"Missing {meta['anom_file']}. Run `python precompute.py`.")
    else:
        selected = load_map_month(str(meta["anom_file"]), year, month)
        if selected.empty:
            st.warning("No data for this month/year combination.")
        else:
            anom_abs = float(selected["anomaly"].abs().quantile(0.98))
            fig_map = px.scatter_map(
                selected,
                lat="lat", lon="lon",
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
                coloraxis_colorbar=dict(title=meta["unit"]),
                paper_bgcolor="rgba(0,0,0,0)",
                font=_FONT,
            )
            st.plotly_chart(fig_map, use_container_width=True)
            st.caption(
                "Each pixel shows how much the selected month deviates from its "
                "2000–2020 climatological average. Red = warmer than typical, blue = cooler. "
                "Use the year and month sliders to scan for marine heatwave events — try June 2023."
            )

# ── Tab 2: Time Series ────────────────────────────────────────────────────────

with tab_ts:
    coupling_all = load_coupling_stats()
    anom_col = meta["anom_col"]

    ts = coupling_all.dropna(subset=[anom_col])[["time", "year", anom_col]].copy()
    ts = ts.sort_values("time").rename(columns={anom_col: "mean_anomaly"})

    yr_min, yr_max = int(ts["year"].min()), int(ts["year"].max())
    st.subheader(f"{meta['label']} — Spatially-Averaged Anomaly {yr_min}–{yr_max}")

    ts["rolling_std"] = ts["mean_anomaly"].rolling(3, center=True).std()
    ts["upper"] = ts["mean_anomaly"] + ts["rolling_std"].fillna(0)
    ts["lower"] = ts["mean_anomaly"] - ts["rolling_std"].fillna(0)

    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(
        x=pd.concat([ts["time"], ts["time"].iloc[::-1]]),
        y=pd.concat([ts["upper"], ts["lower"].iloc[::-1]]),
        fill="toself",
        fillcolor="rgba(29,158,117,0.12)",
        line=dict(color="rgba(255,255,255,0)"),
        name="±1 std (3-month)",
        hoverinfo="skip",
    ))
    fig_ts.add_trace(go.Scatter(
        x=ts["time"], y=ts["mean_anomaly"],
        mode="lines",
        line=dict(color="#1D9E75", width=1.8),
        name="Anomaly",
    ))
    fig_ts.add_hline(y=0, line_color="rgba(255,255,255,0.25)",
                     line_dash="dot", line_width=1)

    if var_key == "SST":
        for date_str, label in _SST_EVENTS:
            dt = pd.Timestamp(date_str)
            if ts["time"].min() <= dt <= ts["time"].max():
                fig_ts.add_vline(
                    x=dt.timestamp() * 1000,
                    line_color="rgba(29,158,117,0.60)",
                    line_dash="dash",
                    line_width=1,
                    annotation_text=label,
                    annotation_position="top right",
                    annotation_font=dict(size=10, color="#7a8a99"),
                    annotation_bgcolor="rgba(13,31,45,0.75)",
                    annotation_bordercolor="rgba(29,158,117,0.4)",
                    annotation_borderwidth=1,
                )

    fig_ts.update_layout(
        **LAYOUT_BASE,
        xaxis=dict(**_AXIS, title=""),
        yaxis=dict(**_YAXIS, title=f"Anomaly ({meta['unit']})"),
    )
    st.plotly_chart(fig_ts, use_container_width=True)
    st.caption(
        "Monthly spatially-averaged anomaly across the NE Atlantic. "
        "The shaded band shows the 3-month rolling ±1 standard deviation. "
        "Values oscillate around zero by construction; sustained excursions above "
        "the band indicate basin-wide warming events."
    )

# ── Tab 3: Month × Year ───────────────────────────────────────────────────────

with tab_hm:
    coupling_hm = load_coupling_stats()
    anom_col = meta["anom_col"]

    ts_hm = coupling_hm.dropna(subset=[anom_col])
    st.subheader(f"{meta['label']} — Monthly × Yearly Anomaly Matrix")

    pivot = ts_hm.pivot(index="month", columns="year", values=anom_col)
    vals = pivot.values[~np.isnan(pivot.values)]
    anom_abs = float(np.abs(vals).max())

    fig_hm = px.imshow(
        pivot,
        color_continuous_scale=meta["colorscale"],
        zmin=-anom_abs, zmax=anom_abs,
        labels={"x": "Year", "y": "Month", "color": f"Anomaly ({meta['unit']})"},
        y=["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        aspect="auto",
    )
    fig_hm.update_layout(
        **LAYOUT_BASE,
        coloraxis_colorbar=dict(title=meta["unit"]),
        xaxis={**_AXIS, "title": "Year"},
        yaxis={**_YAXIS, "showgrid": False, "title": ""},
    )
    st.plotly_chart(fig_hm, use_container_width=True)
    st.caption(
        "Each cell is the spatially-averaged anomaly for one month-year combination. "
        "Rows are months (Jan → Dec), columns are years. "
        "Vertical streaks of red indicate years with sustained warming; "
        "horizontal streaks indicate seasonal biases in the anomaly signal."
    )

# ── Tab 4: Marine Heatwaves ───────────────────────────────────────────────────

with tab_mhw:
    st.subheader("Marine Heatwave Detection")

    if not (DATA_DIR / "mhw_monthly_summary.parquet").exists():
        st.error("Missing mhw_monthly_summary.parquet. Run `python precompute.py`.")
    else:
        mhw_sum = load_mhw_summary()
        events_df = load_mhw_events()

        pixel_df = mhw_sum[["time", "pct_mhw", "max_intensity_multiple", "max_category"]]
        mhw_basin = mhw_sum[["time", "spatial_mean_sst", "spatial_mean_threshold"]]

        fig_mhw = make_subplots(specs=[[{"secondary_y": True}]])

        bar_colors = [
            CATEGORY_COLORS_SOLID.get(cat, CATEGORY_UNCLASSIFIED_COLOR)
            for cat in pixel_df["max_category"]
        ]
        customdata = (
            pixel_df[["max_category", "max_intensity_multiple"]].copy()
            .assign(max_category=lambda d: d["max_category"].fillna("< 5% coverage"))
            .assign(max_intensity_multiple=lambda d:
                    d["max_intensity_multiple"].round(2).fillna(0))
            .values
        )
        fig_mhw.add_trace(
            go.Bar(
                x=pixel_df["time"], y=pixel_df["pct_mhw"],
                marker_color=bar_colors, marker_line_width=0,
                name="% pixels in MHW state", showlegend=False,
                customdata=customdata,
                hovertemplate=(
                    "%{x|%Y-%m}<br>%{y:.1f}% of domain in MHW state<br>"
                    "Max category: %{customdata[0]}<br>"
                    "Max intensity multiple: %{customdata[1]:.2f}×<extra></extra>"
                ),
            ),
            secondary_y=False,
        )

        for _name, _color in list(CATEGORY_COLORS_SOLID.items()) + [
            ("< 5% coverage (not classified)", CATEGORY_UNCLASSIFIED_COLOR)
        ]:
            fig_mhw.add_trace(
                go.Scatter(x=[None], y=[None], mode="markers",
                           marker=dict(color=_color, size=10, symbol="square"),
                           name=_name, showlegend=True),
                secondary_y=False,
            )

        fig_mhw.add_trace(
            go.Scatter(x=mhw_basin["time"], y=mhw_basin["spatial_mean_threshold"],
                       mode="lines",
                       line=dict(color="rgba(220,80,80,0.55)", width=1.2, dash="dash"),
                       name="P90 threshold (domain mean)"),
            secondary_y=True,
        )
        fig_mhw.add_trace(
            go.Scatter(x=mhw_basin["time"], y=mhw_basin["spatial_mean_sst"],
                       mode="lines",
                       line=dict(color="rgba(255,255,255,0.40)", width=1.5),
                       name="Domain-mean SST (less sensitive)"),
            secondary_y=True,
        )
        fig_mhw.update_yaxes(
            title_text="% of NE Atlantic in MHW state",
            secondary_y=False, range=[0, 100],
            showgrid=True, gridcolor="rgba(26,46,64,0.9)",
            title_font=dict(size=11, color="#7a8a99"),
            tickfont=dict(size=11, color="#7a8a99"),
        )
        fig_mhw.update_yaxes(
            title_text="SST (°C)", secondary_y=True,
            showgrid=False,
            title_font=dict(size=11, color="#7a8a99"),
            tickfont=dict(size=11, color="#7a8a99"),
        )
        fig_mhw.update_xaxes(
            showgrid=False,
            title_font=dict(size=11, color="#7a8a99"),
            tickfont=dict(size=11, color="#7a8a99"),
        )
        fig_mhw.update_layout(
            **LAYOUT_BASE,
            xaxis=dict(title=""),
            bargap=0.08,
        )
        st.plotly_chart(fig_mhw, use_container_width=True)

        st.caption(
            "Percentage of the NE Atlantic in marine heatwave state each month, "
            "with bars colored by the maximum local Hobday 2018 category "
            "(I Moderate → IV Extreme). "
            "Grey bars indicate months below the 5% coherent-area threshold — "
            "isolated hot pixels, not basin-scale events. "
            "The June 2023 peak (78.5% coverage) dominates the 24-year record."
        )

        st.subheader("Detected MHW events (basin-mean method)")
        st.caption(
            "Consecutive months in basin-mean MHW state, grouped as discrete events. "
            "This basin-averaged view is less sensitive than the per-pixel detection "
            "above and is shown for reference."
        )
        if events_df.empty:
            st.write("No MHW events detected by the basin-mean method.")
        else:
            disp = events_df.copy()
            disp["start_date"] = disp["start_date"].dt.strftime("%Y-%m")
            disp["end_date"] = disp["end_date"].dt.strftime("%Y-%m")
            disp["max_intensity"] = disp["max_intensity"].round(3)
            disp["cumulative_intensity"] = disp["cumulative_intensity"].round(3)
            st.dataframe(disp, use_container_width=True, hide_index=True)

# ── Tab 5: SST–Chlorophyll ────────────────────────────────────────────────────

with tab_coupling:
    st.subheader("SST–Chlorophyll-a Coupling Analysis")

    if not (DATA_DIR / "coupling_stats.parquet").exists():
        st.error("Missing coupling_stats.parquet. Run `python precompute.py`.")
    else:
        coup_all = load_coupling_stats()
        coup = coup_all.dropna(subset=["chl_anom"]).copy()

        x_vals = coup["sst_anom"].values
        y_vals = coup["chl_anom"].values

        # ── Plot 1: dual-axis time series ─────────────────────────────────
        st.markdown("#### Spatially-Averaged Anomalies (Overlap Period 2018–2023)")

        fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
        fig_dual.add_trace(
            go.Scatter(x=coup["time"], y=x_vals, name="SST anomaly",
                       line=dict(color="#e05252", width=1.8)),
            secondary_y=False,
        )
        fig_dual.add_trace(
            go.Scatter(x=coup["time"], y=y_vals, name="Chl-a anomaly",
                       line=dict(color="#1D9E75", width=1.8)),
            secondary_y=True,
        )
        fig_dual.add_hline(y=0, line_color="rgba(255,255,255,0.2)",
                           line_dash="dot", line_width=1)
        fig_dual.update_yaxes(
            title_text="SST anomaly (°C)", secondary_y=False,
            showgrid=True, gridcolor="rgba(26,46,64,0.9)",
            title_font=dict(size=11, color="#e05252"),
            tickfont=dict(size=11, color="#7a8a99"),
        )
        fig_dual.update_yaxes(
            title_text="Chl-a anomaly (mg m⁻³)", secondary_y=True,
            showgrid=False,
            title_font=dict(size=11, color="#1D9E75"),
            tickfont=dict(size=11, color="#7a8a99"),
        )
        fig_dual.update_xaxes(
            showgrid=False,
            tickfont=dict(size=11, color="#7a8a99"),
        )
        fig_dual.update_layout(**LAYOUT_BASE, xaxis=dict(title=""))
        st.plotly_chart(fig_dual, use_container_width=True)
        st.caption(
            "SST anomaly (red) and chlorophyll-a anomaly (green) over the shared "
            "2018–2023 period. "
            "Look for inverse coupling: warm SST anomalies often correspond to "
            "chlorophyll declines, consistent with reduced nutrient mixing under "
            "thermally stratified conditions."
        )

        st.divider()

        # ── Plot 2: scatter + regression ──────────────────────────────────
        col_l, col_r = st.columns(2)

        r_val = float(np.corrcoef(x_vals, y_vals)[0, 1])
        coeffs = np.polyfit(x_vals, y_vals, 1)
        x_line = np.linspace(x_vals.min(), x_vals.max(), 100)
        y_line = np.polyval(coeffs, x_line)

        with col_l:
            st.markdown("#### SST vs Chl-a Anomaly Scatter")
            fig_sc = go.Figure()
            fig_sc.add_trace(go.Scatter(
                x=x_vals, y=y_vals, mode="markers",
                marker=dict(color="#1D9E75", size=6, opacity=0.7),
                name="Monthly means",
            ))
            fig_sc.add_trace(go.Scatter(
                x=x_line, y=y_line, mode="lines",
                line=dict(color="#e05252", width=1.5, dash="dash"),
                name=f"Regression (r = {r_val:.3f})",
            ))
            fig_sc.update_layout(
                **LAYOUT_BASE,
                xaxis={**_AXIS, "showgrid": True,
                       "gridcolor": "rgba(26,46,64,0.9)",
                       "title": "SST anomaly (°C)"},
                yaxis={**_YAXIS, "title": "Chl-a anomaly (mg m⁻³)"},
                annotations=[dict(
                    x=0.05, y=0.95, xref="paper", yref="paper",
                    text=f"<b>Pearson r = {r_val:.3f}</b>",
                    showarrow=False,
                    bgcolor="rgba(13,31,45,0.85)",
                    bordercolor="rgba(29,158,117,0.4)",
                    borderwidth=1,
                    font=dict(color="#e6edf3", size=12, family="Inter, sans-serif"),
                )],
            )
            st.plotly_chart(fig_sc, use_container_width=True)
            st.caption(
                "Each point is one month of paired SST and Chl-a anomalies. "
                "A negative slope means warmer-than-average months tend to have "
                "lower chlorophyll — the Pearson r quantifies how consistent "
                "this relationship is across the record."
            )

        # ── Plot 3: lagged cross-correlation ──────────────────────────────
        with col_r:
            st.markdown("#### Lagged Cross-Correlation r(SST_t, Chl-a_{t+lag})")
            lags = list(range(-3, 4))
            n = len(coup)
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
                x=lags, y=lag_rs,
                marker_color=["#e05252" if r >= 0 else "#5281e0" for r in lag_rs],
                text=[f"{r:.3f}" for r in lag_rs],
                textposition="outside",
                textfont=dict(size=11, color="#7a8a99"),
            ))
            fig_lag.add_hline(y=0, line_color="rgba(255,255,255,0.3)", line_width=1)
            fig_lag.update_layout(
                **LAYOUT_BASE,
                xaxis=dict(**_AXIS,
                           title="Lag (months) — positive: SST leads Chl-a",
                           tickvals=lags, ticktext=[str(l) for l in lags]),
                yaxis=dict(**_YAXIS, title="Pearson r"),
            )
            st.plotly_chart(fig_lag, use_container_width=True)
            st.caption(
                "Correlation between SST anomaly at time t and Chl-a anomaly "
                "at t + lag months. "
                "A negative bar at a positive lag means chlorophyll tends to drop "
                "after an SST spike — look for whether the signal is stronger "
                "with a 1–2 month delay than at zero lag."
            )

        st.divider()

        # ── MHW months chlorophyll analysis ───────────────────────────────
        st.markdown("#### Chlorophyll-a Response During MHW Months")

        mhw_chl = coup.loc[coup["is_mhw"], "chl_anom"].mean()
        non_mhw_chl = coup.loc[~coup["is_mhw"], "chl_anom"].mean()
        n_mhw_months = int(coup["is_mhw"].sum())

        c1, c2, c3 = st.columns(3)
        c1.metric("Chl-a anomaly — MHW months", f"{mhw_chl:+.4f} mg m⁻³")
        c2.metric("Chl-a anomaly — non-MHW months", f"{non_mhw_chl:+.4f} mg m⁻³")
        c3.metric("MHW months (2018–2023)", n_mhw_months)

        mhw_2023 = coup[coup["is_mhw"] & (coup["time"].dt.year == 2023)].copy()
        if not mhw_2023.empty:
            st.markdown("**2023 MHW months:**")
            disp = mhw_2023[["time", "sst_anom", "chl_anom"]].copy()
            disp["time"] = disp["time"].dt.strftime("%Y-%m")
            disp.columns = ["Month", "SST anomaly (°C)", "Chl-a anomaly (mg m⁻³)"]
            disp["SST anomaly (°C)"] = disp["SST anomaly (°C)"].round(4)
            disp["Chl-a anomaly (mg m⁻³)"] = disp["Chl-a anomaly (mg m⁻³)"].round(4)
            st.dataframe(disp, use_container_width=True, hide_index=True)

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div style="border-top:1px solid #1f2d3d; margin-top:2rem; padding-top:1rem;
                display:flex; justify-content:space-between; align-items:center;
                flex-wrap:wrap; gap:0.5rem;">
      <span style="color:#7a8a99; font-size:11px; font-family:'Inter',sans-serif;">
        Data: Copernicus Marine Service ·
        <code style="font-size:10px; color:#7a8a99;">
          cmems_mod_glo_phy_my_0.083deg_P1M-m
        </code>
      </span>
      <span style="color:#7a8a99; font-size:11px; font-family:'Inter',sans-serif;">
        Álvaro Peñuelas Sánchez ·
        <a href="https://github.com/alvaropenuelas/nea-ocean-dashboard"
           style="color:#1D9E75; text-decoration:none;">
          ⌥ github.com/alvaropenuelas/nea-ocean-dashboard
        </a>
      </span>
    </div>
    """,
    unsafe_allow_html=True,
)
