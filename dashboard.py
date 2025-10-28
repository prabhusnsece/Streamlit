import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import time

# --- Supabase connection ---
url = "https://dtzfdekgoskdyhdpqojw.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR0emZkZWtnb3NrZHloZHBxb2p3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE2Mzg2NDUsImV4cCI6MjA3NzIxNDY0NX0.KYdFwdezWFeR5KyX2v3KdrVJgAGl8nxqAmXRKOqa22c"
supabase = create_client(url, key)

st.set_page_config(page_title="RFID Student Tracker", layout="wide")
st.title("🎓 RFID Student Tracking Dashboard")

# --- Auto refresh every few seconds ---
refresh_rate = st.sidebar.slider("Refresh rate (seconds)", 5, 60, 10)

placeholder = st.empty()

while True:
    with placeholder.container():
        data = supabase.table("student").select("*").execute().data
        if not data:
            st.warning("No student data available yet.")
        else:
            df = pd.DataFrame(data)
            df["last_seen"] = pd.to_datetime(df["last_seen"])
            st.dataframe(df.sort_values("last_seen", ascending=False), use_container_width=True)

            # Analytics summary
            st.metric("Total Students", len(df))
            active = df[df["location"] != "Not detected yet"]
            st.metric("Active Students Detected", len(active))

    time.sleep(refresh_rate)
    st.rerun()