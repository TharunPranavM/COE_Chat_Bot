import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SCRAPE_LINKS = os.getenv("SCRAPE_LINKS", "").split(",")
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./faiss_index")
PDF_DIR = os.getenv("PDF_DIR", "./pdfs")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is required in .env")