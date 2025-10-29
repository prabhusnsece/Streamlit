import streamlit as st
from supabase import create_client, Client
import pandas as pd
import pytz
from datetime import datetime

# ------------------------------------
# 🧭 PAGE CONFIG
# ------------------------------------
st.set_page_config(page_title="RFID Dashboard", page_icon="🎓", layout="wide")

# ------------------------------------
# 🔐 LOGIN SYSTEM
# ------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔒 Login Required")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if (
            username == st.secrets["auth"]["username"]
            and password == st.secrets["auth"]["password"]
        ):
            st.session_state.logged_in = True
            st.success("✅ Login successful! Redirecting...")
            st.query_params["refresh"] = "1"
            st.rerun()
        else:
            st.error("❌ Invalid username or password")
    st.stop()

# ------------------------------------
# 🔌 CONNECT TO SUPABASE
# ------------------------------------
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["anon_key"]
supabase: Client = create_client(url, key)

# ------------------------------------
# 🎓 DASHBOARD HEADER
# ------------------------------------
st.title("🎓 RFID Student Tracking Dashboard")
st.caption("IoT & Edge AI Innovation Lab — Real-time RFID Tracking (India Standard Time)")

# Logout button
if st.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.rerun()

# ------------------------------------
# 🔁 AUTO REFRESH
# ------------------------------------
st_autorefresh = st.experimental_rerun  # deprecated; fixed below
st_autorefresh_count = st.experimental_rerun  # ignore—remove confusion

# ✅ Use official auto-refresh (every 10s)
st_autorefresh = st.autorefresh(interval=10 * 1000, key="refresh")

# ------------------------------------
# 🕒 TIMEZONE SETUP
# ------------------------------------
ist = pytz.timezone("Asia/Kolkata")

# ------------------------------------
# 📥 FETCH DATA FROM SUPABASE
# ------------------------------------
try:
    data = supabase.table("student").select("*").execute()
    students = data.data

    if not students:
        st.warning("⚠️ No student data found in Supabase yet.")
    else:
        df = pd.DataFrame(students)

        if "last_seen" in df.columns:
            df["last_seen"] = pd.to_datetime(df["last_seen"], errors="coerce", utc=True)
            df["last_seen"] = df["last_seen"].dt.tz_convert(ist)
            df["last_seen"] = df["last_seen"].dt.strftime("%Y-%m-%d %H:%M:%S")

        # Sort by most recent scans
        df = df.sort_values(by="last_seen", ascending=False)

        st.dataframe(
            df[["id", "name", "rfid", "location", "last_seen"]],
            use_container_width=True,
            hide_index=True,
        )

        st.success(f"✅ Total Students Tracked: {len(df)}")

except Exception as e:
    st.error(f"Error fetching data: {e}")

# ------------------------------------
# ⚙️ FOOTER
# ------------------------------------
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>IoT & Edge AI Innovation Lab — © 2025 SNS Institutions</div>",
    unsafe_allow_html=True,
)
