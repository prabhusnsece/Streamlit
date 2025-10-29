import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import pytz

# ---------------------------------
# Load secrets for authentication
# ---------------------------------
AUTH_USER = st.secrets["auth"]["username"]
AUTH_PASS = st.secrets["auth"]["password"]

# ---------------------------------
# Login Page
# ---------------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def login_screen():
    st.title("🔐 RFID Dashboard Login")
    st.write("IoT & Edge AI Innovation Lab")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == AUTH_USER and password == AUTH_PASS:
            st.session_state["authenticated"] = True
            st.success("✅ Login successful!")
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

if not st.session_state["authenticated"]:
    login_screen()
    st.stop()  # Stop execution until login succeeds

# ---------------------------------
# Continue to main dashboard after login
# ---------------------------------
st.set_page_config(page_title="RFID Student Tracking Dashboard", layout="wide")

# Supabase connection
supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["anon_key"])

st.title("🎓 RFID Student Tracking Dashboard")
st.caption("IoT & Edge AI Innovation Lab — Real-time RFID Tracking (India Standard Time)")

# Fetch data
response = supabase.table("students").select("*").execute()
df = pd.DataFrame(response.data)

if not df.empty:
    df["last_seen"] = pd.to_datetime(df["last_seen"])
    # Convert UTC → IST
    ist = pytz.timezone("Asia/Kolkata")
    df["last_seen"] = df["last_seen"].dt.tz_localize("UTC").dt.tz_convert(ist)
    df["last_seen"] = df["last_seen"].dt.strftime("%Y-%m-%d %H:%M:%S")

    st.dataframe(
        df[["id", "name", "rfid", "location", "last_seen"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No student data found in Supabase yet.")

# Logout button
if st.button("Logout"):
    st.session_state["authenticated"] = False
    st.rerun()