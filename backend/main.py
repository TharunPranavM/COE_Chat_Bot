from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime
import os
from typing import Optional, List
from supabase import create_client, Client
from dotenv import load_dotenv
from pypdf import PdfReader

from models import UserCreate, UserLogin, Token, UserResponse, ChatMessage, ChatResponse, UploadResponse
from auth import create_access_token, decode_access_token
from supabase_client import supabase, supabase_admin
from llm_agent import rag_query
from chunker import preprocess_uploaded_doc
from embedder import embed_and_store
from config import PDF_DIR

load_dotenv()

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Ensure PDF directory exists
os.makedirs(PDF_DIR, exist_ok=True)

# Helper functions
def get_user_by_email(email: str):
    try:
        response = supabase.table('users').select('*').eq('email', email).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None

def create_user(user_data: UserCreate):
    try:
        response = supabase_admin.table('users').insert({
            'name': user_data.username,
            'email': user_data.email,
            'password': user_data.password,
            'role': user_data.role
        }).execute()
        
        if response.data:
            return user_data.email
        return None
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

def get_or_create_session(email: str):
    """Get the latest session or create a new one"""
    try:
        # Get latest session
        resp = supabase.table("chat_sessions").select("id")\
               .eq("email", email).order("updated_at", desc=True).limit(1).execute()
        
        if resp.data:
            return resp.data[0]["id"]
        
        # Create new session if none exists
        title = f"Chat {datetime.now().strftime('%b %d, %H:%M')}"
        resp = supabase_admin.table("chat_sessions").insert({
            "email": email,
            "title": title
        }).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception as e:
        print(f"Error getting/creating session: {e}")
        return None

def save_message(session_id: int, email: str, role: str, content: str):
    """Save a message to the database"""
    try:
        supabase_admin.table("chat_messages").insert({
            "session_id": session_id,
            "email": email,
            "role": role,
            "content": content
        }).execute()
        supabase_admin.table("chat_sessions").update({"updated_at": "now()"}).eq("id", session_id).execute()
    except Exception as e:
        print(f"Error saving message: {e}")

def get_session_messages(session_id: int):
    """Get all messages for a session"""
    try:
        resp = supabase.table("chat_messages") \
            .select("role, content, created_at") \
            .eq("session_id", session_id) \
            .order("created_at") \
            .execute()
        return resp.data or []
    except Exception as e:
        print(f"Error loading messages: {e}")
        return []

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user_email = payload.get("sub")
    role = payload.get("role")
    
    if user_email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    return {"email": user_email, "role": role}

# Authentication endpoints
@app.post("/api/auth/signup", status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate):
    existing_user = get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
    
    user_id = create_user(user_data)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create user"
        )
    
    return {"message": "User created successfully"}

@app.post("/api/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    user = get_user_by_email(user_data.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    stored_password = user.get('password')
    
    # Support both plain text and hashed passwords
    is_valid = (user_data.password == stored_password)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    access_token = create_access_token(
        data={"sub": user.get('email'), "role": user.get('role')}
    )
    
    user_response = UserResponse(
        id=user.get('email'),
        username=user.get('name'),
        email=user.get('email'),
        role=user.get('role')
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

# Chat endpoints
@app.post("/api/chat/{session_id}", response_model=ChatResponse)
async def chat(session_id: int, message: ChatMessage, current_user: dict = Depends(get_current_user)):
    email = current_user['email']
    
    # Save user message
    save_message(session_id, email, "user", message.message)
    
    # Get RAG response
    try:
        response_text = rag_query(message.message)
    except Exception as e:
        print(f"Error in RAG query: {e}")
        response_text = "I apologize, but I encountered an error processing your request. Please try again."
    
    # Save assistant response
    save_message(session_id, email, "assistant", response_text)
    
    return ChatResponse(
        response=response_text,
        timestamp=datetime.utcnow().isoformat()
    )

@app.get("/api/chat/sessions")
async def get_chat_sessions(current_user: dict = Depends(get_current_user)):
    """Get all chat sessions for the current user"""
    email = current_user['email']
    try:
        resp = supabase.table("chat_sessions").select("id,title,updated_at")\
               .eq("email", email).order("updated_at", desc=True).execute()
        return {"sessions": resp.data or []}
    except Exception as e:
        print(f"Error fetching sessions: {e}")
        return {"sessions": []}

@app.post("/api/chat/sessions/new")
async def create_new_session(current_user: dict = Depends(get_current_user)):
    """Create a new chat session"""
    email = current_user['email']
    title = f"Chat {datetime.now().strftime('%b %d, %H:%M')}"
    try:
        resp = supabase_admin.table("chat_sessions").insert({
            "email": email,
            "title": title
        }).execute()
        return {"session_id": resp.data[0]["id"], "title": title}
    except Exception as e:
        print(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")

@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: int, current_user: dict = Depends(get_current_user)):
    """Get chat history for a specific session"""
    messages = get_session_messages(session_id)
    return {"messages": messages}

# Admin file upload endpoints
@app.post("/api/admin/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can upload files"
        )
    
    # Save file with original name
    file_path = os.path.join(PDF_DIR, file.filename)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    file_size = len(content)
    upload_date = datetime.utcnow().isoformat()
    
    # Process PDF and embed
    try:
        pdf_reader = PdfReader(file_path)
        text = " ".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
        chunks = preprocess_uploaded_doc(text)
        embed_and_store(chunks)
    except Exception as e:
        print(f"Error processing PDF: {e}")
    
    return UploadResponse(
        filename=file.filename,
        file_id=file.filename,
        size=file_size,
        upload_date=upload_date
    )

@app.get("/api/admin/files")
async def get_files(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view files"
        )
    
    try:
        files_list = []
        total_size = 0
        
        # List all PDF files in the directory
        if os.path.exists(PDF_DIR):
            for filename in os.listdir(PDF_DIR):
                if filename.endswith('.pdf'):
                    file_path = os.path.join(PDF_DIR, filename)
                    file_stat = os.stat(file_path)
                    file_size = file_stat.st_size
                    upload_date = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                    
                    files_list.append({
                        "file_id": filename,
                        "filename": filename,
                        "size": file_size,
                        "upload_date": upload_date
                    })
                    total_size += file_size
        
        # Sort by upload date (newest first)
        files_list.sort(key=lambda x: x['upload_date'], reverse=True)
        
        return {
            "files": files_list,
            "total_files": len(files_list),
            "total_size": total_size
        }
    except Exception as e:
        print(f"Error fetching files: {e}")
        return {"files": [], "total_files": 0, "total_size": 0}

@app.get("/")
async def root():
    return {"message": "Role-based Auth API with RAG"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
