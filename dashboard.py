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
    st.image("https://www.snsgroups.com/assets/sns%20section-DmAMs1xk.png", width=200)  # replace with your logo path or URL
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
# 4️⃣ Header & Logout
# ------------------------------------------------
col1, col2 = st.columns([7, 1])
with col1:
    st.image("https://www.snsgroups.com/assets/sns%20section-DmAMs1xk.png", width=150)  # lab logo
    st.title("🎓 RFID Student Tracking Dashboard")
    st.caption("IoT & Edge AI Innovation Lab — Real-time RFID Tracking (India Standard Time)")
with col2:
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

# Add a hero/banner image
st.image("https://sppedtrackgps.in/wp-content/uploads/2022/03/RFID-Student-Attendance-System-Banner.png.webp", use_container_width=True)

st.markdown("---")

# ------------------------------------------------
# 5️⃣ Fetch Data from Supabase
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
# 6️⃣ Convert to DataFrame
# ------------------------------------------------
df = pd.DataFrame(data)

# ------------------------------------------------
# 7️⃣ Convert UTC → IST
# ------------------------------------------------
if "last_seen" in df.columns:
    ist = pytz.timezone("Asia/Kolkata")
    df["last_seen"] = pd.to_datetime(df["last_seen"], errors="coerce", utc=True)
    df["last_seen"] = df["last_seen"].dt.tz_convert(ist)
    df["last_seen"] = df["last_seen"].dt.strftime("%Y-%m-%d %H:%M:%S")

# ------------------------------------------------
# 8️⃣ Show Dashboard Table
# ------------------------------------------------
st.subheader("📋 Registered Student Activity")
st.dataframe(
    df[["id", "name", "rfid", "location", "last_seen"]],
    use_container_width=True,
    hide_index=True
)

# ------------------------------------------------
# 9️⃣ Statistics Section
# ------------------------------------------------
st.markdown("### 📊 Summary Insights")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("👩‍🎓 Total Students", len(df))
with col2:
    st.metric("🏫 Active Locations", df["location"].nunique())
with col3:
    st.metric("⏰ Last Update", datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%H:%M:%S"))

st.markdown("---")

# ------------------------------------------------
# 🔁 Auto Refresh every 10 seconds
# ------------------------------------------------
st.caption("🔄 Auto-refresh every 10 seconds to reflect real-time tag reads.")
time.sleep(10)
st.rerun()

