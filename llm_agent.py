from groq import Groq
from config import GROQ_API_KEY
from vectorstore import load_vectorstore
from guardrails import apply_guardrails

def rag_query(query, use_complex_model=False):
    vectorstore = load_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    
    docs = retriever.get_relevant_documents(query)
    context = "\n\n".join([doc.page_content for doc in docs])
    
    # Choose model based on complexity
    model_name = "llama-3.3-70b-versatile" if not use_complex_model else "openai/gpt-oss-120b"
    client = Groq(api_key=GROQ_API_KEY)
    
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Answer based on the context provided."},
            {"role": "user", "content": f"Context: {context}\nQuery: {query}"}
        ],
        temperature=0.3,
        max_tokens=500
    )
    
    return apply_guardrails(query, response.choices[0].message.content)