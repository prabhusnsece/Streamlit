import streamlit as st
import google.generativeai as genai
from fpdf import FPDF
import tempfile
import os

# ========== Gemini API Key ==========
API_KEY = "AIzaSyBZloFKbyaMn0EcrK8FdWZybl0OMGITfm0"
genai.configure(api_key=API_KEY)

# Initialize model
model = genai.GenerativeModel(model_name="gemini-2.0-flash")

# ========== Streamlit UI Setup ==========
st.set_page_config(page_title="SNS AI Email Generator", layout="centered", page_icon="📧")

# Custom CSS styling for color and aesthetics
st.markdown("""
    <style>
    .main {
        background-color: #f1f3f6;
    }
    .stApp {
        background-image: linear-gradient(to right top, #f7fbfc, #e0f2f1, #b2dfdb, #80cbc4, #4db6ac);
        padding: 2rem;
        border-radius: 10px;
    }
    h1 {
        color: #003366;
        text-align: center;
    }
    .stButton>button {
        background-color: #003366;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 10px 16px;
    }
    .stDownloadButton>button {
        background-color: #009688;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 10px 16px;
    }
    </style>
""", unsafe_allow_html=True)

# ========== Header with Logo ==========
st.image("https://www.bing.com/th?id=OIP.N0Boxtyrfky73SS1LbG4sQHaDD", width=150)  # Replace this link with your actual SNS logo if stored locally or hosted
st.title("📧 SNS AI Email Generator")

with st.expander("ℹ️ How it works"):
    st.markdown("""
    - Enter the email idea or purpose.
    - Choose format and tone.
    - Click **Generate Email**.
    - Download it as PDF or regenerate.
    """)

# ========== User Inputs ==========
user_input = st.text_area("✍️ Enter the purpose or content for the email:", height=150)

col1, col2 = st.columns(2)
with col1:
    email_format = st.selectbox("📑 Select the email format:", ["Formal", "Informal", "Business", "Apology", "Thank You"])
with col2:
    email_tone = st.selectbox("🎯 Select the tone:", ["Polite", "Assertive", "Friendly", "Professional", "Encouraging"])

# Store result
if "generated_email" not in st.session_state:
    st.session_state.generated_email = ""

# Email generation function
def generate_email(text, fmt, tone):
    prompt = f"""
    Write an email based on the following input:

    Input: {text}
    Format: {fmt}
    Tone: {tone}

    Ensure the email has a subject, greeting, body, and closing.
    """
    response = model.generate_content(prompt)
    return response.text.strip()

# Buttons
col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 Generate Email"):
        if user_input.strip():
            st.session_state.generated_email = generate_email(user_input, email_format, email_tone)
        else:
            st.warning("Please enter some content to generate the email.")

with col2:
    if st.button("🔁 Regenerate"):
        if user_input.strip():
            st.session_state.generated_email = generate_email(user_input, email_format, email_tone)
        else:
            st.warning("Enter email content first.")

# Output
if st.session_state.generated_email:
    st.subheader("📬 Generated Email")
    st.text_area("Your Email", value=st.session_state.generated_email, height=300)

    # PDF generation
    def create_pdf(content):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.set_auto_page_break(auto=True, margin=15)

        # Add logo to PDF (optional - for local logo usage)
        # pdf.image("sns_logo.png", x=10, y=8, w=33)

        for line in content.split('\n'):
            pdf.multi_cell(0, 10, line)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            pdf.output(tmp.name)
            return tmp.name

    pdf_path = create_pdf(st.session_state.generated_email)
    with open(pdf_path, "rb") as file:
        st.download_button("📥 Download as PDF", file, file_name="sns_generated_email.pdf", mime="application/pdf")
    os.remove(pdf_path)
