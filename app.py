import streamlit as st
import os
import json
import sys
from google import genai
from google.cloud import firestore
from google.oauth2 import service_account

# Firestore क्लाइंट इनिशियलाइज करें
db = firestore.Client()

st.title("EduCollab Hub - Community Chat")

# यूजर लॉगिन चेक करें
if "user_email" in st.session_state:
  user = st.session_state["user_email"]
  st.write(f"Logged in as: **{user}**")

  # मैसेज इनपुट बॉक्स
  message = st.text_input("संदेश लिखें...")
  if st.button("भेजें"):
    if message:
      # Firestore में मैसेज सेव करें
      db.collection("chats").add(
          {"user": user, "message": message, "timestamp": firestore.SERVER_TIMESTAMP}
      )
      st.success("मैसेज भेज दिया गया!")

  st.markdown("---")
  st.subheader("लाइव चैट फीड")

  # डेटाबेस से मैसेज फेच करें
  chats_ref = (
      db.collection("chats").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(20)
  )
  chats = chats_ref.stream()

  for chat in chats:
    chat_data = chat.to_dict()
    st.write(f"**{chat_data.get('user', 'Anonymous')}**: {chat_data.get('message', '')}")
else:
  st.warning("कृपया पहले चैट करने के लिए लॉगिन करें।")

st.set_page_config(page_title="EduCollab Hub", page_icon="🎓", layout="centered")

try:
    key_dict = dict(st.secrets["textkey"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    db = firestore.Client(credentials=creds, project=creds.project_id)
except Exception as e:
    st.error(f"Firestore Connection Error: {e}")

# Gemini AI Client Setup
try:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
    ai_client = genai.Client(api_key=gemini_api_key)
except Exception as e:
    st.error(f"Gemini API Key Error: {e}")
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_email" not in st.session_state:
    st.session_state.user_email = ""

if not st.session_state.logged_in:
    st.title("🎓 EduCollab Hub")
    st.write("शुरू करने के लिए कृपया लॉगिन करें या नया अकाउंट बनाएं।")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login to your account")
        login_email = st.text_input("Email", key="login_email")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Login"):
            if login_email and login_pass:
                st.session_state.logged_in = True
                st.session_state.user_email = login_email
                st.success("लॉगिन सफल रहा!")
                st.rerun()
            else:
                st.warning("कृपया सभी फील्ड भरें।")
                
    with tab2:
        st.subheader("Create a new account")
        signup_email = st.text_input("Email", key="signup_email")
        signup_pass = st.text_input("Password", type="password", key="signup_pass")
        
        if st.button("Create Account"):
            if signup_email and signup_pass:
                st.success("अकाउंट सफलतापूर्वक बन गया! अब आप Login टैब से लॉगिन कर सकते हैं।")
            else:
                st.warning("कृपया ईमेल और पासवर्ड दर्ज करें।")

else:
    st.sidebar.title("🛠️ Dashboard")
    st.sidebar.write(f"Logged in as: **{st.session_state.user_email}**")
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()

    st.title("EduCollab Hub - Workspace")
    
    uploaded_file = st.file_uploader("फाइल अपलोड करें", label_visibility="collapsed")
    
    if uploaded_file is not None:
        st.success(f"फाइल अपलोड सफल: {uploaded_file.name}")

    prompt = st.chat_input("यहाँ अपना मैसेज टाइप करें...")
    
    if prompt:
        st.chat_message("user").write(prompt)
        try:
            response = ai_client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
            )
            ai_reply = response.text
        except Exception as e:
            ai_reply = f"एआई रिस्पांस में त्रुटि: {e}"
            
        st.chat_message("assistant").write(ai_reply)
