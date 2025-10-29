# streamlit_dashboard.py
import streamlit as st
from supabase import create_client, Client
import pandas as pd
import pytz
from datetime import datetime

# Try to import the lightweight autorefresh helper.
# If not available, we'll provide a manual Refresh button instead.
try:
    from streamlit_autorefresh import st_autorefresh
    HAVE_AUTORELOAD = True
except Exception:
    HAVE_AUTORELOAD = False

# ------------------------------------
# Page config
# ------------------------------------
st.set_page_config(page_title="RFID Dashboard", page_icon="🎓", layout="wide")

# ------------------------------------
# LOGIN
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
            # simple rerun to show dashboard
            st.experimental_rerun()
        else:
            st.error("❌ Invalid username or password")
    st.stop()

# ------------------------------------
# Connect to Supabase
# ------------------------------------
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["anon_key"]
supabase: Client = create_client(url, key)

# Header and logout
st.title("🎓 RFID Student Tracking Dashboard")
st.caption("IoT & Edge AI Innovation Lab — Real-time RFID Tracking (India Standard Time)")

if st.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.experimental_rerun()

# ------------------------------------
# Auto-refresh setup
# ------------------------------------
# Preferred: use streamlit-autorefresh (install with pip and add to requirements)
AUTO_REFRESH_MS = 10_000  # 10 seconds

if HAVE_AUTORELOAD:
    # returns a counter that increments on every refresh
    _ = st_autorefresh(interval=AUTO_REFRESH_MS, key="auto_refresh")
else:
    # fallback: show a Refresh button and a note
    st.info("Auto-refresh disabled (install `streamlit-autorefresh` for automatic updates).")
    if st.button("🔄 Refresh now"):
        st.experimental_rerun()

# ------------------------------------
# Timezone helper
# ------------------------------------
ist = pytz.timezone("Asia/Kolkata")

# ------------------------------------
# Fetch & render data
# ------------------------------------
try:
    response = supabase.table("student").select("*").execute()
    students = response.data

    if not students:
        st.warning("⚠️ No student data found in Supabase yet.")
    else:
        df = pd.DataFrame(students)

        # Normalize/convert last_seen to IST for display
        if "last_seen" in df.columns:
            # parse datetimes (coerce errors)
            df["last_seen"] = pd.to_datetime(df["last_seen"], errors="coerce")
            # If timestamps are tz-naive, localize to UTC then convert to IST
            if df["last_seen"].dt.tz is None:
                df["last_seen"] = df["last_seen"].dt.tz_localize("UTC", ambiguous="NaT", nonexistent="NaT")
            df["last_seen"] = df["last_seen"].dt.tz_convert(ist)
            df["last_seen"] = df["last_seen"].dt.strftime("%d-%b-%Y, %I:%M:%S %p")

        # Sort by last_seen (most recent first); handle None gracefully
        if "last_seen" in df.columns:
            df["sort_ts"] = pd.to_datetime(df["last_seen"], format="%d-%b-%Y, %I:%M:%S %p", errors="coerce")
            df = df.sort_values(by="sort_ts", ascending=False).drop(columns=["sort_ts"])
        else:
            df = df.sort_values(by="id")

        st.dataframe(df[["id", "name", "rfid", "location", "last_seen"]], use_container_width=True, hide_index=True)
        st.success(f"✅ Total Students Tracked: {len(df)}")

except Exception as e:
    st.error(f"Error fetching data: {e}")

# Footer
st.markdown("---")
st.markdown("<div style='text-align:center;color:gray;'>IoT & Edge AI Innovation Lab — © 2025 SNS Institutions</div>", unsafe_allow_html=True)
