# app.py
import streamlit as st
import os
import re
from datetime import datetime
from pypdf import PdfReader
from chunker import chunk_text, preprocess_uploaded_doc
from embedder import embed_and_store, initialize_vectorstore
from llm_agent import rag_query
from config import SCRAPE_LINKS, FAISS_INDEX_PATH, PDF_DIR
from initializer import initial_vectorization
from supabase_client import supabase, supabase_admin

# Email regex
EMAIL_REGEX = re.compile(r"^[0-9]{2}[A-Za-z]{2}[0-9]{3}@kpriet\.ac\.in$", re.IGNORECASE)

def validate_email(email):
    return bool(EMAIL_REGEX.fullmatch(email))

# === Helper Functions ===
def create_new_session(email):
    title = f"Chat {datetime.now().strftime('%b %d, %H:%M')}"
    resp = supabase_admin.table("chat_sessions").insert({
        "email": email,
        "title": title
    }).execute()
    return resp.data[0]["id"] if resp.data else None

def get_user_sessions(email):
    resp = supabase.table("chat_sessions").select("id,title")\
           .eq("email", email).order("updated_at", desc=True).execute()
    return resp.data or []

def load_session_messages(session_id):
    try:
        # Use relationship embedding: chat_messages -> users via email
        resp = supabase.table("chat_messages") \
            .select("role, content, users:email(name)") \
            .eq("session_id", session_id) \
            .order("created_at") \
            .execute()

        messages = []
        for row in resp.data:
            # row["users"] is a dict with "name"
            user_name = row.get("users", {}).get("name", "Unknown")
            messages.append({
                "role": row["role"],
                "content": row["content"],
                "name": user_name
            })
        return messages

    except Exception as e:
        st.error(f"Error loading messages: {e}")
        return []

def save_message(session_id, email, role, content):
    supabase_admin.table("chat_messages").insert({
        "session_id": session_id,
        "email": email,
        "role": role,
        "content": content
    }).execute()
    supabase_admin.table("chat_sessions").update({"updated_at": "now()"}).eq("id", session_id).execute()

# === Auth ===
def signup():
    st.title("Sign Up")
    name = st.text_input("Full Name")
    email = st.text_input("Email", placeholder="22AD060@kpriet.ac.in")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["user", "admin"])
    
    if st.button("Sign Up"):
        if not all([name, email, password]):
            st.warning("All fields required.")
            return
        if not validate_email(email):
            st.error("Email must be: 22AD060@kpriet.ac.in")
            return
        
        data = {"email": email, "name": name, "password": password, "role": role}
        try:
            supabase_admin.table("users").insert(data).execute()
            st.success(f"Account created for {name}!")
        except:
            st.error("Email already registered.")

def login():
    st.title("Login")
    email = st.text_input("Email", placeholder="22AD060@kpriet.ac.in")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if not validate_email(email):
            st.error("Invalid email format.")
            return
        resp = supabase.table("users").select("password,role,name").eq("email", email).execute()
        if resp.data and resp.data[0]["password"] == password:
            st.session_state.update({
                "logged_in": True,
                "email": email,
                "role": resp.data[0]["role"],
                "name": resp.data[0]["name"]
            })
            st.rerun()
        else:
            st.error("Invalid email or password")

# === Dashboards ===
def chatbot_dashboard():
    st.title("RAG Chatbot")
    st.header(f"Hi, {st.session_state['name']}!")

    # Sidebar: Session Selector + Sign Out
    st.sidebar.title("Chat History")
    sessions = get_user_sessions(st.session_state["email"])
    options = {s["title"]: s["id"] for s in sessions}
    options["New Chat"] = "new"
    selected = st.sidebar.selectbox("Select chat", list(options.keys()), key="session_select")

    if st.sidebar.button("Sign Out"):
        for key in ["logged_in", "role", "email", "name", "current_session_id", "chat_history"]:
            st.session_state.pop(key, None)
        st.rerun()

    # Handle session selection
    if selected == "New Chat":
        session_id = create_new_session(st.session_state["email"])
        st.session_state.current_session_id = session_id
        st.session_state.chat_history = []
        st.rerun()
    else:
        session_id = options[selected]
        if st.session_state.get("current_session_id") != session_id:
            st.session_state.current_session_id = session_id
            st.session_state.chat_history = load_session_messages(session_id)

    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = create_new_session(st.session_state["email"])
        st.session_state.chat_history = []

    # === New Chat Button in Chat Area ===
    col1, col2 = st.columns([6, 1])
    with col1:
        st.write("")  # spacer
    with col2:
        if st.button("New Chat", key="new_chat_btn"):
            session_id = create_new_session(st.session_state["email"])
            st.session_state.current_session_id = session_id
            st.session_state.chat_history = []
            st.rerun()

    # Display messages
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.write(f"**{msg['name']}**: {msg['content']}")
            else:
                st.write(msg["content"])

    # User input
    if prompt := st.chat_input("Ask anything..."):
        st.session_state.chat_history.append({
            "role": "user",
            "content": prompt,
            "name": st.session_state["name"]
        })
        with st.chat_message("user"):
            st.write(f"**{st.session_state['name']}**: {prompt}")
        save_message(st.session_state.current_session_id, st.session_state["email"], "user", prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = rag_query(prompt)
            st.write(response)
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response,
                "name": "Assistant"
            })
            save_message(st.session_state.current_session_id, st.session_state["email"], "assistant", response)

def admin_dashboard():
    st.title("Admin Panel")
    st.sidebar.button("Sign Out", on_click=lambda: [
        st.session_state.pop(k, None) for k in 
        ["logged_in", "role", "email", "name", "current_session_id", "chat_history"]
    ] + [st.rerun()])

    uploaded = st.file_uploader("Upload PDF", type="pdf")
    if uploaded:
        path = os.path.join(PDF_DIR, uploaded.name)
        with open(path, "wb") as f:
            f.write(uploaded.getbuffer())
        text = " ".join([p.extract_text() for p in PdfReader(uploaded).pages if p.extract_text()])
        chunks = preprocess_uploaded_doc(text)
        embed_and_store(chunks)
        st.success(f"Embedded: {uploaded.name}")

def main():
    if not os.path.exists(FAISS_INDEX_PATH):
        with st.spinner("Initializing knowledge base..."):
            initial_vectorization()
        st.success("Knowledge base ready!")

    if st.session_state.get("role") == "admin":
        admin_dashboard()
    else:
        chatbot_dashboard()

# === App Flow ===
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.sidebar.title("Authentication")
    page = st.sidebar.radio("Go to", ["Login", "Sign Up"])
    if page == "Login":
        login()
    else:
        signup()
else:
    main()