from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain.embeddings import HuggingFaceEmbeddings

def chunk_text(texts):
    initial_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    initial_chunks = initial_splitter.split_text('\n\n'.join(texts))
    
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    semantic_chunker = SemanticChunker(embeddings)
    semantic_chunks = []
    for chunk in initial_chunks:
        semantic_chunks.extend(semantic_chunker.split_text(chunk))
    
    return semantic_chunks

def preprocess_uploaded_doc(doc_content):
    return chunk_text([doc_content])