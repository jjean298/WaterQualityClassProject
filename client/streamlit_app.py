# client/streamlit_app.py
import os
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

# Connect to your local Flask API
API_BASE = f"http://127.0.0.1:{os.getenv('API_PORT', '5001')}/api"

# Streamlit page settings
st.set_page_config(page_title="💧 Water Quality Dashboard", layout="wide")
st.title("💧 Water Quality Data Explorer")

# Sidebar filters
with st.sidebar:
    st.header("🔍 Filters")
    start = st.text_input("Start Date (ISO, optional)", value="")
    end = st.text_input("End Date (ISO, optional)", value="")

    min_temp = st.number_input("Min Temperature (°C)", value=float("nan"))
    max_temp = st.number_input("Max Temperature (°C)", value=float("nan"))
    min_sal = st.number_input("Min Salinity (ppt)", value=float("nan"))
    max_sal = st.number_input("Max Salinity (ppt)", value=float("nan"))
    min_odo = st.number_input("Min ODO (mg/L)", value=float("nan"))
    max_odo = st.number_input("Max ODO (mg/L)", value=float("nan"))

    limit = st.slider("Result Limit", 10, 1000, 200)
    skip = st.number_input("Skip (pagination)", min_value=0, value=0, step=50)

    def build_params():
        params = {"limit": limit, "skip": skip}
        for k, v in {
            "start": start.strip(), "end": end.strip(),
            "min_temp": min_temp, "max_temp": max_temp,
            "min_sal": min_sal, "max_sal": max_sal,
            "min_odo": min_odo, "max_odo": max_odo,
        }.items():
            if isinstance(v, float) and pd.isna(v):
                continue
            if isinstance(v, str) and not v:
                continue
            params[k] = v
        return params

    params = build_params()

# Fetch data from API
obs_url = f"{API_BASE}/observations"
obs_resp = requests.get(obs_url, params=params)
if obs_resp.ok:
    obs_json = obs_resp.json()
    df = pd.DataFrame(obs_json.get("items", []))
else:
    st.error("Failed to fetch data from API.")
    st.stop()

# Display data table
st.subheader("📋 Observations")
st.caption(f"Total matching records: {obs_json.get('count', 0)} (showing up to {params.get('limit', 100)})")

if df.empty:
    st.warning("No data found for current filters.")
    st.stop()

# Convert timestamps and sort
if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.sort_values("timestamp")

st.dataframe(df, use_container_width=True, hide_index=True)

# ---- Charts Section ----
st.subheader("📊 Visualizations")
col1, col2, col3 = st.columns(3)

with col1:
    if "timestamp" in df.columns and "temperature" in df.columns:
        fig = px.line(df, x="timestamp", y="temperature", title="Temperature over Time")
        st.plotly_chart(fig, use_container_width=True)

with col2:
    if "salinity" in df.columns:
        fig = px.histogram(df, x="salinity", nbins=40, title="Salinity Distribution")
        st.plotly_chart(fig, use_container_width=True)

with col3:
    if {"temperature", "salinity"} <= set(df.columns):
        color = "odo" if "odo" in df.columns else None
        fig = px.scatter(df, x="temperature", y="salinity", color=color,
                         title="Temperature vs Salinity (Color = ODO)")
        st.plotly_chart(fig, use_container_width=True)

# ---- Map Section ----
if {"latitude", "longitude"} <= set(df.columns):
    st.subheader("🌍 Location Map")
    map_df = df.dropna(subset=["latitude", "longitude"])
    fig = px.scatter_geo(map_df, lat="latitude", lon="longitude",
                         hover_name="timestamp", title="Sample Locations")
    st.plotly_chart(fig, use_container_width=True)

# ---- Stats Section ----
st.subheader("📈 Summary Statistics")
stats_resp = requests.get(f"{API_BASE}/stats")
if stats_resp.ok:
    st.json(stats_resp.json(), expanded=False)
else:
    st.warning("No statistics available.")

# ---- Outlier Detection ----
st.subheader("🚨 Outliers")
colA, colB, colC = st.columns([1, 1, 1])
with colA:
    field = st.selectbox("Field", ["temperature", "salinity", "odo"])
with colB:
    method = st.selectbox("Method", ["iqr", "zscore"])
with colC:
    k = st.number_input("k (IQR multiplier or z-threshold)", value=1.5)

outlier_params = {"field": field, "method": method, "k": k}
outlier_resp = requests.get(f"{API_BASE}/outliers", params=outlier_params)
if outlier_resp.ok:
    outlier_json = outlier_resp.json()
    out_df = pd.DataFrame(outlier_json.get("items", []))
    st.caption(f"Flagged outliers: {outlier_json.get('count', len(out_df))}")
    if not out_df.empty:
        st.dataframe(out_df, use_container_width=True, hide_index=True)
    else:
        st.info("No outliers detected.")
else:
    st.error("Failed to retrieve outliers.")
