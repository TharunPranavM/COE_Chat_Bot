import os
from pypdf import PdfReader
from scraper import KprietScraper
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
    pdf_chunks = []
    if SCRAPE_LINKS:
        # Use crawler for first URL, ignore others or crawl multiple
        scraper = KprietScraper(base_url=SCRAPE_LINKS[0], max_pages=50)
        web_text = scraper.scrape()
        web_chunks = chunk_text([web_text])  # chunk the full site
    else:
        web_chunks = []

    all_chunks = pdf_chunks + web_chunks
    return initialize_vectorstore(all_chunks)