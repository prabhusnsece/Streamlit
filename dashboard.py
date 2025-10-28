import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import time
import pytz

# --- Supabase connection ---
url = "https://dtzfdekgoskdyhdpqojw.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR0emZkZWtnb3NrZHloZHBxb2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE2Mzg2NDUsImV4cCI6MjA3NzIxNDY0NX0.KYdFwdezWFeR5KyX2v3KdrVJgAGl8nxqAmXRKOqa22c"
supabase = create_client(url, key)

st.set_page_config(page_title="RFID Student Tracker", layout="wide")
st.title("🎓 RFID Student Tracking Dashboard")

# --- Sidebar ---
refresh_rate = st.sidebar.slider("Refresh rate (seconds)", 5, 60, 10)
st.sidebar.info("Data auto-refreshes every few seconds.")

# --- Placeholder for live updates ---
placeholder = st.empty()
ist = pytz.timezone("Asia/Kolkata")

while True:
    with placeholder.container():
        response = supabase.table("student").select("*").execute()
        data = response.data

        if not data:
            st.warning("No student data available yet.")
        else:
            df = pd.DataFrame(data)
            if "last_seen" in df.columns:
                df["last_seen"] = pd.to_datetime(df["last_seen"], errors="coerce")
                df["last_seen"] = df["last_seen"].dt.tz_convert(ist)
                df["last_seen_str"] = df["last_seen"].dt.strftime("%Y-%m-%d %H:%M:%S %Z")

            st.subheader("📋 Student Log (Latest First)")
            st.dataframe(df.sort_values("last_seen", ascending=False)[["id", "name", "rfid", "location", "last_seen_str"]],
                         use_container_width=True)

            st.markdown("### 🔍 Summary")
            st.metric("Total Students", len(df))
            active = df[df["location"] != "Not detected yet"]
            st.metric("Active Students Detected", len(active))

    time.sleep(refresh_rate)
    st.rerun()