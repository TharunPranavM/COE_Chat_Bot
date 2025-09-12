import os
from pypdf import PdfReader
from scraper import scrape_websites
from chunker import chunk_text, preprocess_uploaded_doc
from embedder import initialize_vectorstore
from config import SCRAPE_LINKS, PDF_DIR

def process_pre_existing_pdfs():
    chunks = []
    if os.path.exists(PDF_DIR):
        for filename in os.listdir(PDF_DIR):
            if filename.endswith(".pdf"):
                filepath = os.path.join(PDF_DIR, filename)
                reader = PdfReader(filepath)
                text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
                chunks.extend(preprocess_uploaded_doc(text))
    return chunks

def initial_vectorization():
    pdf_chunks = process_pre_existing_pdfs()
    web_texts = scrape_websites(SCRAPE_LINKS) if SCRAPE_LINKS else []
    web_chunks = chunk_text(web_texts)
    all_chunks = pdf_chunks + web_chunks
    return initialize_vectorstore(all_chunks)