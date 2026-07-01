import math
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="GiddyUp Weather", page_icon="🏇", layout="wide")

TRACKS = {
    "Saratoga": {"lat": 43.0731, "lon": -73.7846},
    "Belmont Park": {"lat": 40.7146, "lon": -73.7226},
    "Aqueduct": {"lat": 40.6729, "lon": -73.8358},
    "Churchill Downs": {"lat": 38.2029, "lon": -85.7711},
    "Del Mar": {"lat": 32.9764, "lon": -117.2612},
}

def wind_cardinal(deg):
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[int((deg + 11.25) / 22.5) % 16]

def get_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,pressure_msl,cloud_cover",
        "hourly": "precipitation,rain,temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,pressure_msl,cloud_cover",
        "past_days": 3,
        "forecast_days": 2,
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "auto",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def rainfall_total(df, hours):
    cutoff = datetime.now() - timedelta(hours=hours)
    recent = df[df["time"] >= cutoff]
    return recent["precipitation"].sum()

def wind_compass(direction):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[0, 1],
        theta=[direction, direction],
        mode="lines+markers",
        line=dict(width=6),
        marker=dict(size=14),
        name="Wind Direction"
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=False, range=[0, 1]),
            angularaxis=dict(direction="clockwise", rotation=90)
        ),
        showlegend=False,
        height=350,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    return fig

st.title("🏇 GiddyUp Weather Dashboard")
st.caption("Live weather, rainfall totals, and wind for racetracks.")

track = st.selectbox("Select Track", list(TRACKS.keys()))
lat = TRACKS[track]["lat"]
lon = TRACKS[track]["lon"]

if st.button("Refresh Weather"):
    st.cache_data.clear()

@st.cache_data(ttl=600)
def load_data(lat, lon):
    return get_weather(lat, lon)

try:
    data = load_data(lat, lon)
    current = data["current"]
    hourly = pd.DataFrame(data["hourly"])
    hourly["time"] = pd.to_datetime(hourly["time"])

    st.subheader(track)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Temperature", f'{current["temperature_2m"]:.1f}°F')
        st.metric("Humidity", f'{current["relative_humidity_2m"]}%')

    with col2:
        st.metric("Current Rain", f'{current["precipitation"]:.2f}"')
        st.metric("Cloud Cover", f'{current["cloud_cover"]}%')

    with col3:
        st.metric("Wind Speed", f'{current["wind_speed_10m"]:.1f} mph')
        st.metric("Wind Gusts", f'{current["wind_gusts_10m"]:.1f} mph')

    with col4:
        direction = current["wind_direction_10m"]
        st.metric("Wind Direction", f"{wind_cardinal(direction)} / {direction:.0f}°")
        st.metric("Pressure", f'{current["pressure_msl"]:.1f} hPa')

    st.divider()

    st.subheader("Rainfall Totals")

    rain_cols = st.columns(6)
    windows = [1, 6, 12, 24, 48, 72]

    for c, h in zip(rain_cols, windows):
        with c:
            st.metric(f"Last {h}h", f'{rainfall_total(hourly, h):.2f}"')

    st.divider()

    left, right = st.columns([1, 1])

    with left:
        st.subheader("Wind Compass")
        st.plotly_chart(wind_compass(direction), use_container_width=True)

    with right:
        st.subheader("Next 24 Hours")
        future = hourly[hourly["time"] >= pd.Timestamp.now()].head(24)
        chart_df = future[["time", "precipitation", "wind_speed_10m", "wind_gusts_10m"]].copy()
        chart_df = chart_df.set_index("time")
        st.line_chart(chart_df)

    st.divider()

    export = hourly.copy()
    csv = export.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Weather CSV",
        data=csv,
        file_name=f"{track.lower().replace(' ', '_')}_weather.csv",
        mime="text/csv"
    )

except Exception as e:
    st.error("Weather data could not be loaded.")
    st.write(e)