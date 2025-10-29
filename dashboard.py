import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import pytz
import time

# ------------------------------------------------
# 1️⃣ Load secrets (Supabase + Login)
# ------------------------------------------------
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["anon_key"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ------------------------------------------------
# 2️⃣ Streamlit App Config
# ------------------------------------------------
st.set_page_config(
    page_title="RFID Student Tracking Dashboard",
    page_icon="🎓",
    layout="wide"
)

# ------------------------------------------------
# 3️⃣ Authentication (Persistent across refreshes)
# ------------------------------------------------
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
            st.success("✅ Login successful! Loading dashboard...")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Invalid username or password")
    st.stop()

# ------------------------------------------------
# 4️⃣ Title
# ------------------------------------------------
st.title("🎓 RFID Student Tracking Dashboard")
st.caption("IoT & Edge AI Innovation Lab — Real-time RFID Tracking (India Standard Time)")

# ------------------------------------------------
# 5️⃣ Auto Refresh without logout
# ------------------------------------------------
refresh_rate = 10  # seconds
st_autorefresh = st.empty()
st_autorefresh.info(f"🔄 Auto-refresh every {refresh_rate} seconds.")
time.sleep(refresh_rate)
st.rerun()

# ------------------------------------------------
# 6️⃣ Fetch data from Supabase
# ------------------------------------------------
try:
    response = supabase.table("student").select("*").execute()
    data = response.data
except Exception as e:
    st.error("⚠️ Error fetching data from Supabase. Please check connection or table name.")
    st.stop()

if not data:
    st.info("No student data found in Supabase yet.")
    st.stop()

# ------------------------------------------------
# 7️⃣ Convert to DataFrame
# ------------------------------------------------
df = pd.DataFrame(data)

# ------------------------------------------------
# 8️⃣ Convert UTC → IST
# ------------------------------------------------
if "last_seen" in df.columns:
    ist = pytz.timezone("Asia/Kolkata")
    df["last_seen"] = pd.to_datetime(df["last_seen"], errors="coerce", utc=True)
    df["last_seen"] = df["last_seen"].dt.tz_convert(ist)
    df["last_seen"] = df["last_seen"].dt.strftime("%Y-%m-%d %H:%M:%S")

# ------------------------------------------------
# 9️⃣ Display Data
# ------------------------------------------------
st.dataframe(
    df[["id", "name", "rfid", "location", "last_seen"]],
    use_container_width=True,
    hide_index=True
)
