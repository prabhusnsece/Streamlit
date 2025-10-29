import streamlit as st
from supabase import create_client, Client
import pandas as pd
import pytz

# ------------------------------------
# 🔒 PAGE SETUP
# ------------------------------------
st.set_page_config(page_title="RFID Dashboard", page_icon="🎓", layout="wide")

# ------------------------------------
# 🔒 LOGIN AUTHENTICATION
# ------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔒 Login Required")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if (
            user == st.secrets["auth"]["username"]
            and pwd == st.secrets["auth"]["password"]
        ):
            st.session_state.logged_in = True
            st.success("✅ Login successful! Please wait...")
            st.experimental_set_query_params(refresh="1")  # safe page refresh
        else:
            st.error("Invalid username or password")
    st.stop()

# ------------------------------------
# ✅ CONNECT TO SUPABASE
# ------------------------------------
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["anon_key"]
supabase: Client = create_client(url, key)

st.title("🎓 RFID Student Tracking Dashboard")
st.caption("IoT & Edge AI Innovation Lab — Real-time RFID Tracking (India Standard Time)")

# ------------------------------------
# 🕒 INDIA TIMEZONE
# ------------------------------------
ist = pytz.timezone("Asia/Kolkata")

# ------------------------------------
# 🔄 AUTO REFRESH
# ------------------------------------
st_autorefresh = st.empty()
st_autorefresh.info("🔁 Auto-refreshes every 10 seconds")
st_autorefresh = st.experimental_data_editor

# ------------------------------------
# 📥 FETCH STUDENT DATA
# ------------------------------------
try:
    data = supabase.table("student").select("*").execute()
    students = data.data

    if not students:
        st.warning("No student data found in Supabase yet.")
    else:
        df = pd.DataFrame(students)

        if "last_seen" in df.columns:
            df["last_seen"] = pd.to_datetime(df["last_seen"], errors="coerce", utc=True)
            df["last_seen"] = df["last_seen"].dt.tz_convert(ist)
            df["last_seen"] = df["last_seen"].dt.strftime("%Y-%m-%d %H:%M:%S")

        # Sort by recent time
        df = df.sort_values(by="last_seen", ascending=False)

        # Display
        st.dataframe(
            df[["id", "name", "rfid", "location", "last_seen"]],
            use_container_width=True,
            hide_index=True,
        )

        st.success(f"✅ Total Students Tracked: {len(df)}")

except Exception as e:
    st.error(f"Error fetching data: {e}")

# ------------------------------------
# 📅 FOOTER
# ------------------------------------
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>IoT & Edge AI Innovation Lab — © 2025 SNS Institutions</div>",
    unsafe_allow_html=True,
)
