import streamlit as st
import sqlite3
import os
from pypdf import PdfReader
from scraper import scrape_websites
from chunker import chunk_text, preprocess_uploaded_doc
from embedder import embed_and_store, initialize_vectorstore
from llm_agent import rag_query
from config import SCRAPE_LINKS, FAISS_INDEX_PATH
from initializer import initial_vectorization

# Initialize SQLite database for users at script startup
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    conn.commit()
    conn.close()

init_db()  # Call here to ensure table exists before any operations

def signup():
    st.title("Sign Up")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["user", "admin"])
    if st.button("Sign Up"):
        if username and password:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                st.error("Username already exists!")
            else:
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
                conn.commit()
                st.success(f"User {username} signed up as {role}!")
                st.info("Please log in with your new credentials.")
            conn.close()
        else:
            st.warning("Please fill in all fields.")

def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE username = ? AND password = ?", (username, password))
        result = cursor.fetchone()
        conn.close()
        if result:
            st.session_state["logged_in"] = True
            st.session_state["role"] = result[0]
            st.session_state["username"] = username
            st.success("Logged in successfully!")
            st.rerun()
        else:
            st.error("Invalid username or password")

def chatbot_dashboard():
    st.title("Chatbot Dashboard")
    st.header(f"Welcome, {st.session_state['username']}!")
    
    # Initialize chat history in session state if not present
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Chat input at the bottom
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Generate and display bot response
        with st.chat_message("assistant"):
            with st.spinner("Generating response..."):
                response = rag_query(prompt)
            st.write(response)
            st.session_state.chat_history.append({"role": "assistant", "content": response})

def admin_dashboard():
    st.title("Admin Dashboard")
    st.header(f"Welcome, {st.session_state['username']}!")
    st.write("Coming Soon!")

def main():
    st.title("RAG Application")
    
    # Initialize vectorstore and data only if FAISS index doesn't exist
    if not os.path.exists(FAISS_INDEX_PATH):
        with st.spinner("Initializing vector database and data..."):
            initial_vectorization()  # Vectorize and store all data at startup
        st.success("Initial vectorization completed!")
    
    if st.session_state["role"] == "admin":
        admin_dashboard()
    else:
        chatbot_dashboard()
    
    if st.session_state["role"] == "admin":
        st.header("Admin Tools")
        new_urls = st.text_input("Add new web URLs (comma-separated)")
        if st.button("Scrape New Websites"):
            if new_urls:
                urls_list = [url.strip() for url in new_urls.split(",")]
                with st.spinner("Scraping new websites..."):
                    texts = scrape_websites(urls_list)
                    chunks = chunk_text(texts)
                    embed_and_store(chunks)
                st.success("New websites scraped and appended to vector DB!")
            else:
                st.warning("Please enter URLs")
        
        uploaded_file = st.file_uploader("Upload New Document (PDF or Text)", type=["pdf", "txt"])
        if uploaded_file:
            if uploaded_file.name.endswith(".pdf"):
                reader = PdfReader(uploaded_file)
                text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
            else:
                text = uploaded_file.read().decode("utf-8")
            with st.spinner("Processing new document..."):
                chunks = preprocess_uploaded_doc(text)
                embed_and_store(chunks)
            st.success("New document processed and appended to vector DB!")

if __name__ == "__main__":
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    
    if not st.session_state["logged_in"]:
        st.sidebar.title("Authentication")
        page = st.sidebar.radio("Go to", ["Login", "Sign Up"])
        if page == "Login":
            login()
        else:
            signup()
    else:
        main()
        
        if st.sidebar.button("Logout"):
            st.session_state["logged_in"] = False
            st.session_state.pop("role", None)
            st.session_state.pop("username", None)
            st.session_state.pop("initialized", None)
            st.session_state.pop("chat_history", None)  # Clear chat history on logout
            st.rerun()