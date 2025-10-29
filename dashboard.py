import streamlit as st
from supabase import create_client, Client
import pandas as pd
import pytz
import time

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
            time.sleep(1)
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
    st.experimental_rerun()

# Auto-refresh every 10 seconds
st_autorefresh = st.experimental_data_editor  # alias
st_autorefresh_interval = 10
st_autorefresh_label = f"Auto-refreshing every {st_autorefresh_interval} seconds..."
st.info(st_autorefresh_label)
st_autorefresh = st.experimental_rerun  # ensure live refresh below

time.sleep(st_autorefresh_interval)

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
