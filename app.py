import streamlit as st
from google import genai
from PIL import Image
from datetime import datetime
from google.cloud import firestore

# --- Firebase Firestore Setup ---
db = firestore.Client.from_service_account_json("firebase_key.json")

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="EduCollab Hub",
    page_icon="logo.png",
    layout="centered"
)

# --- Main UI Header with Logo ---
col1, col2 = st.columns([1, 6])
with col1:
    try:
        st.image("logo.png", width=85)
    except Exception:
        st.write("🍎")
with col2:
    st.title("EduCollab Hub")

# --- Sidebar Configuration ---
st.sidebar.header("💬 Chat Settings & Friends")
# User Name & Room Selection for Friends Chat
user_name = st.sidebar.text_input("Aapka Naam (Your Name):", value="Friend 1")
chat_room = st.sidebar.selectbox("Chat Room / Topic:", ["General Educator Chat", "Friends Group Discussion", "Lesson Planning"])

# API Key from Secrets (Agar secrets mein hai toh wahan se lega, nahi toh sidebar mein puchega)
try:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
except Exception:
    api_key = ""

if not api_key:
    api_key = st.sidebar.text_input("Gemini API Key:", type="password")

if not api_key:
    st.warning("Kripya apni Gemini API key secrets.toml mein ya sidebar mein darj karein.")
    st.stop()
# Initialize Gemini Client
client = genai.Client(api_key=api_key)

# --- System Persona Instruction ---
system_prompt = (
    "You are a warm, encouraging, and friendly early childhood education teacher and companion. "
    "You speak with kindness, patience, and enthusiasm, helping friends collaborate, "
    "share ideas, and discuss education topics with cheerful emojis."
)

# --- Session State Setup for Messages based on Room ---
room_key = f"messages_{chat_room}"
if room_key not in st.session_state:
    st.session_state[room_key] = []
    
    # Firestore se selected room ki purani chat history load karein
    try:
        docs = db.collection("rooms").document(chat_room).collection("chats").order_by("timestamp").stream()
        for doc in docs:
            data = doc.to_dict()
            if "display_name" in data and "message" in data:
                st.session_state[room_key].append({
                    "role": data.get("role", "user"), 
                    "content": f"**{data['display_name']}**: {data['message']}"
                })
    except Exception as e:
        print(f"Firestore load error: {e}")

# --- Clear Screen Button ---
if st.sidebar.button("Clear Room Chat"):
    st.session_state[room_key] = []
    st.rerun()

# --- Main UI Header ---
st.title("🍎 Friends & Educator Collaborative Chat")
st.write(f"Namaste **{user_name}**! Aap abhi **'{chat_room}'** room mein hain. Apne doston ke sath yahan vichar saza karein ya AI se madad lein!")

# --- Display Messages on Screen ---
for message in st.session_state[room_key]:
    with st.chat_message("user" if "assistant" not in message["role"] else "assistant"):
        st.markdown(message["content"])

# --- Image Upload Feature in Main Chat Area ---
uploaded_image = st.file_uploader("🖼️ Koi tasveer ya activity share karein (Optional):", type=["jpg", "jpeg", "png"])

# --- Chat Input & AI / Friend Response ---
prompt = st.chat_input("Apna sandesh yahan likhein ya Gemini se puchiye...")

if prompt or uploaded_image:
    user_input_display = prompt if prompt else "[Shared an Image]"
    formatted_user_msg = f"**{user_name}**: {user_input_display}"
    
    # Show user message immediately on screen
    with st.chat_message("user"):
        if prompt:
            st.markdown(formatted_user_msg)
        if uploaded_image:
            st.image(uploaded_image, width=250)
            
    st.session_state[room_key].append({"role": "user", "content": formatted_user_msg})

    # Save user message to Firebase under specific Room
    try:
        db.collection("rooms").document(chat_room).collection("chats").document().set({
            "display_name": user_name,
            "message": user_input_display,
            "role": "user",
            "timestamp": datetime.now()
        })
    except Exception as e:
        print(f"Firestore save error: {e}")

    # Check if user wants AI response or just chatting with friends
    # Agar message mein '@ai' likha hai ya seedha AI se baat karni hai toh Gemini response dega
    contents = [prompt, Image.open(uploaded_image)] if uploaded_image and prompt else (Image.open(uploaded_image) if uploaded_image else prompt)
    
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config={"system_instruction": system_prompt}
        )
        bot_response = f"🤖 **Gemini AI**: {response.text}"
        
        with st.chat_message("assistant"):
            st.markdown(bot_response)
            
        st.session_state[room_key].append({"role": "assistant", "content": bot_response})

        # Save AI response to Firebase
        db.collection("rooms").document(chat_room).collection("chats").document().set({
            "display_name": "Gemini AI",
            "message": response.text,
            "role": "assistant",
            "timestamp": datetime.now()
        })
    except Exception as e:
        print(f"AI Error: {e}")