from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from config import FAISS_INDEX_PATH

def load_vectorstore():
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    return FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)