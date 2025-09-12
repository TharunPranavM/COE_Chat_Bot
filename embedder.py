from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
import os
from config import FAISS_INDEX_PATH

def embed_and_store(chunks, index_path=FAISS_INDEX_PATH):
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    
    if os.path.exists(index_path):
        vectorstore = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    else:
        vectorstore = FAISS.from_texts(texts=[""], embedding=embeddings)
    
    if chunks:
        vectorstore.add_texts(chunks)
        vectorstore.save_local(index_path)
    return vectorstore

def initialize_vectorstore(chunks):
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    if not os.path.exists(FAISS_INDEX_PATH):
        FAISS.from_texts(texts=[""], embedding=embeddings).save_local(FAISS_INDEX_PATH)
    vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    if chunks:
        vectorstore.add_texts(chunks)
        vectorstore.save_local(FAISS_INDEX_PATH)
    return vectorstore